"""Đo chất lượng + tốc độ của pipeline hỏi đáp trên nhiều cấu hình, xuất báo cáo Markdown.

Cách chạy (đứng ở thư mục backend/, đã activate .venv, Ollama đang chạy):

    # Lần đầu: upload + index file PDF rồi chạy luôn
    python -m eval.run_bench --pdf sample.pdf

    # Các lần sau: dùng lại tài liệu đã index (chạy lại --pdf cùng file cũng tự dùng lại, không index trùng)
    python -m eval.run_bench --doc-id <doc_id>

    # Chỉ định cấu hình (mặc định: mode_fast, mode_balanced, mode_accurate; cấu hình cũ: vector_only, rerank8...)
    python -m eval.run_bench --doc-id <doc_id> --profiles rerank8 rerank20

    # Thêm cấu hình reranker nhỏ (tải thêm model ~600MB lần đầu)
    python -m eval.run_bench --doc-id <doc_id> --with-small-reranker

Báo cáo được ghi vào eval/reports/bench_<thời gian>.md (+ .json dữ liệu thô).
"""
import argparse
import json
import re
import statistics
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path

from app import config, pipeline

HERE = Path(__file__).parent

# Mỗi cấu hình là các giá trị ghi đè lên app.config trong lúc chạy.
# pipeline.py đọc config.X ở mỗi lần hỏi, nên đổi giá trị ở đây có tác dụng ngay.
PROFILES: dict[str, dict] = {
    "vector_only": {"USE_RERANK": False, "USE_BM25": False, "TOP_K_RETRIEVE": 20},
    "rerank20": {"USE_RERANK": True, "USE_BM25": False, "TOP_K_RETRIEVE": 20},
    "rerank8": {"USE_RERANK": True, "USE_BM25": False, "TOP_K_RETRIEVE": 8},
    "rerank8_bm25": {"USE_RERANK": True, "USE_BM25": True, "TOP_K_RETRIEVE": 8},
    # 3 chế độ trả lời của giao diện (app/options.py), các ngưỡng lấy từ .env
    "mode_fast": {"MODE": "fast"},
    "mode_balanced": {"MODE": "balanced"},
    "mode_accurate": {"MODE": "accurate"},
}
SMALL_RERANKER_PROFILE = {
    "small_rerank12_bm25": {
        "USE_RERANK": True,
        "USE_BM25": True,
        "TOP_K_RETRIEVE": 12,
        "RERANK_MODEL": "Alibaba-NLP/gte-multilingual-reranker-base",
        "RERANK_TRUST_REMOTE_CODE": True,
    }
}
# Chạy mặc định: 3 chế độ của giao diện. Cấu hình cũ (vector_only, rerank8...) gọi bằng --profiles.
DEFAULT_PROFILES = ["mode_fast", "mode_balanced", "mode_accurate"]
COMMON = {"USE_REWRITE": True}  # luôn bật viết lại câu hỏi để test hội thoại

STAGES = ["rewrite", "retrieve", "rerank", "llm", "verify", "locate"]


# ---------------------------------------------------------------- tiện ích
def apply_overrides(overrides: dict) -> dict:
    """Ghi đè config, trả về giá trị cũ để khôi phục sau."""
    old = {k: getattr(config, k) for k in overrides}
    for k, v in overrides.items():
        setattr(config, k, v)
    return old


def ollama_snapshot() -> list[dict]:
    """Model nào đang nạp, bao nhiêu % nằm trên GPU, còn giữ đến khi nào."""
    try:
        from ollama import Client

        out = []
        for m in Client(host=config.OLLAMA_HOST).ps().models:
            size, vram = m.size or 0, m.size_vram or 0
            out.append(
                {
                    "model": m.model,
                    "size_gb": round(size / 1e9, 2),
                    "gpu_percent": round(100 * vram / size) if size else 0,
                    "expires_at": str(m.expires_at)[:19] if m.expires_at else "",
                }
            )
        return out
    except Exception as e:  # không có quyền / Ollama cũ -> bỏ qua
        return [{"error": str(e)}]


def pages_of(result: dict) -> tuple[list[int], list[int]]:
    cited = [c["page"] for c in result.get("citations", [])]
    retrieved = []
    for r in result["debug"].get("retrieved", []):
        retrieved.extend(range(r["page_start"], r["page_end"] + 1))
    return cited, retrieved


def contains_any(text: str, patterns: list[str]) -> bool:
    """Mỗi phần tử có thể là 'a|b|c' (chỉ cần khớp một trong số đó)."""
    t = text.lower()
    return all(any(alt in t for alt in p.lower().split("|")) for p in patterns)


def evaluate(item: dict, result: dict) -> tuple[bool, str]:
    """Trả về (đạt?, lý do) cho một câu hỏi."""
    found = result["found"]
    cited, retrieved = pages_of(result)
    kind = item.get("type") or ("in_doc" if item.get("expect") == "answer" else "trap")
    page = item.get("expected_page")

    if kind in ("in_doc", "overview"):
        if not found:
            return False, f"từ chối nhầm ({result['debug'].get('rejected_reason')})"
        if page is not None and page not in cited and page not in retrieved:
            return False, f"sai trang: trích {cited}, tìm được {sorted(set(retrieved))}, cần {page}"
        msg = "ok"
        if page is not None and page not in cited:
            msg = f"ok nhưng trích dẫn ở trang {cited} (trang {page} chỉ có trong ngữ cảnh)"
    else:  # out_of_scope / trap / refuse
        if found:
            return False, "BỊA: lẽ ra phải từ chối"
        msg = f"ok ({result['debug'].get('rejected_reason')})"

    q = result["debug"].get("search_query", "")
    if item.get("query_must_contain") and not contains_any(q, item["query_must_contain"]):
        return False, f"viết lại thiếu ngữ cảnh: “{q}”"
    if item.get("query_must_not_contain") and contains_any(q, item["query_must_not_contain"]):
        return False, f"viết lại dính chủ đề cũ: “{q}”"
    return True, msg


def ask(doc_id: str, session: str, question: str) -> tuple[dict | None, int, str | None]:
    t = time.perf_counter()
    try:
        res = pipeline.answer_question(doc_id, session, question)
        err = None
    except Exception:
        res, err = None, traceback.format_exc(limit=3)
    return res, round((time.perf_counter() - t) * 1000), err


# ---------------------------------------------------------------- chạy một cấu hình
def run_profile(doc_id: str, name: str, overrides: dict, data: dict) -> dict:
    old = apply_overrides({**COMMON, **overrides})
    print(f"\n=== Cấu hình: {name} {overrides}")
    try:
        # Làm nóng: nạp model (Ollama, reranker) — không tính vào kết quả
        _, warm_ms, warm_err = ask(doc_id, uuid.uuid4().hex, "Hàm sigmoid còn được gọi là gì?")
        print(f"  làm nóng: {warm_ms} ms" + (f" LỖI: {warm_err}" if warm_err else ""))
        snapshot = ollama_snapshot()

        rows = []
        for item in data["single"]:
            res, ms, err = ask(doc_id, uuid.uuid4().hex, item["question"])
            rows.append(make_row(name, item["id"], item, res, ms, err))
            print(f"  {item['id']} {rows[-1]['status']} {ms} ms  {rows[-1]['note']}")

        for chain in data["chains"]:
            session = uuid.uuid4().hex  # cả chuỗi dùng chung một phiên
            for n, turn in enumerate(chain["turns"], start=1):
                res, ms, err = ask(doc_id, session, turn["question"])
                rid = f"{chain['id']}.{n}"
                rows.append(make_row(name, rid, turn, res, ms, err))
                print(f"  {rid} {rows[-1]['status']} {ms} ms  {rows[-1]['note']}")
        return {"profile": name, "overrides": overrides, "warmup_ms": warm_ms, "ollama": snapshot, "rows": rows}
    finally:
        apply_overrides(old)


def make_row(profile: str, rid: str, item: dict, res: dict | None, ms: int, err: str | None) -> dict:
    kind = item.get("type") or ("chain_answer" if item.get("expect") == "answer" else "chain_refuse")
    if res is None:
        return {"profile": profile, "id": rid, "type": kind, "question": item["question"], "status": "ERR",
                "note": (err or "").strip().splitlines()[-1], "total_ms": ms, "timings": {}}
    ok, note = evaluate(item, res)
    d = res["debug"]
    cited, _ = pages_of(res)
    return {
        "profile": profile,
        "id": rid,
        "type": kind,
        "question": item["question"],
        "status": "PASS" if ok else "FAIL",
        "note": note,
        "found": res["found"],
        "route": d.get("route"),
        "rejected_reason": d.get("rejected_reason"),
        "best_score": d.get("best_score"),
        "gate": d.get("gate"),
        "search_query": d.get("search_query"),
        "cited_pages": cited,
        "n_citations": len(res.get("citations", [])),
        "n_highlighted": sum(1 for c in res.get("citations", []) if c.get("rects")),
        "answer": res["answer"][:200],
        "timings": d.get("timings_ms", {}),
        "total_ms": ms,
    }


# ---------------------------------------------------------------- báo cáo
def median(values: list[float]) -> str:
    return f"{statistics.median(values) / 1000:.1f}" if values else "–"


def write_report(runs: list[dict], doc_id: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (out_dir / f"bench_{stamp}.json").write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")

    L: list[str] = []
    L.append(f"# Báo cáo benchmark — {datetime.now():%Y-%m-%d %H:%M}\n")
    L.append(f"- doc_id: `{doc_id}`")
    L.append(f"- Chat: `{config.CHAT_MODEL}` · Embedding: `{config.EMBED_MODEL}` · NUM_CTX={config.NUM_CTX}"
             f" · EMBED_NUM_CTX={config.EMBED_NUM_CTX} · KEEP_ALIVE={config.KEEP_ALIVE}"
             f" · TOP_K_CONTEXT={config.TOP_K_CONTEXT} · MIN_RERANK_SCORE={config.MIN_RERANK_SCORE}\n")

    # Bảng tổng hợp
    L.append("## 1. Tổng hợp\n")
    L.append("| Cấu hình | Có trong file | Tổng quan | Không liên quan | Bẫy | Hội thoại | Tổng | Trung vị (s) | Trung vị rerank (s) | Trung vị LLM (s) | Chậm nhất (s) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for run in runs:
        rows = run["rows"]

        def score(types):
            sel = [r for r in rows if r["type"] in types]
            return f"{sum(r['status'] == 'PASS' for r in sel)}/{len(sel)}" if sel else "–"

        totals = [r["total_ms"] for r in rows]
        L.append(
            f"| {run['profile']} | {score({'in_doc'})} | {score({'overview'})} | {score({'out_of_scope'})} | {score({'trap'})} "
            f"| {score({'chain_answer', 'chain_refuse'})} | {score({r['type'] for r in rows})} | {median(totals)} "
            f"| {median([r['timings'].get('rerank', 0) for r in rows if 'rerank' in r['timings']])} "
            f"| {median([r['timings']['llm'] for r in rows if 'llm' in r['timings']])} "
            f"| {max(totals) / 1000:.1f} |"
        )

    # Thời gian theo bước
    L.append("\n## 2. Thời gian trung vị theo bước (giây)\n")
    L.append("| Cấu hình | Làm nóng | " + " | ".join(STAGES) + " |")
    L.append("|---|---|" + "---|" * len(STAGES))
    for run in runs:
        cells = [median([r["timings"][s] for r in run["rows"] if s in r["timings"]]) for s in STAGES]
        L.append(f"| {run['profile']} | {run['warmup_ms'] / 1000:.1f} | " + " | ".join(cells) + " |")

    # Trạng thái Ollama
    L.append("\n## 3. Ollama sau khi làm nóng\n")
    for run in runs:
        snap = ", ".join(
            f"{m.get('model')} {m.get('size_gb')}GB {m.get('gpu_percent')}% GPU (giữ đến {m.get('expires_at')})"
            if "model" in m else str(m)
            for m in run["ollama"]
        )
        L.append(f"- **{run['profile']}**: {snap or 'không có model nào đang nạp'}")

    # Câu không đạt
    L.append("\n## 4. Các câu không đạt\n")
    any_fail = False
    for run in runs:
        for r in run["rows"]:
            if r["status"] != "PASS":
                any_fail = True
                L.append(
                    f"- **{run['profile']} · {r['id']}** ({r['type']}) “{r['question']}” → {r['status']}: {r['note']}"
                    f" · điểm {r.get('best_score')} / ngưỡng {r.get('gate')} · route {r.get('route')}"
                    f" · search_query “{r.get('search_query')}”"
                )
    if not any_fail:
        L.append("Không có.")

    # Chi tiết
    L.append("\n## 5. Chi tiết từng câu\n")
    for run in runs:
        L.append(f"\n### {run['profile']}\n")
        L.append("| ID | Kết quả | Điểm | Lý do từ chối | Route | Trang trích | Tô màu | Tổng (s) | search_query |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for r in run["rows"]:
            sq = (r.get("search_query") or "").replace("|", "/")
            L.append(
                f"| {r['id']} | {r['status']} | {r.get('best_score')} | {r.get('rejected_reason') or ''} | {r.get('route') or ''} "
                f"| {r.get('cited_pages', '')} | {r.get('n_highlighted', 0)}/{r.get('n_citations', 0)} "
                f"| {r['total_ms'] / 1000:.1f} | {sq} |"
            )

    path = out_dir / f"bench_{stamp}.md"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pdf", help="đường dẫn PDF: upload + index rồi chạy")
    g.add_argument("--doc-id", help="doc_id của tài liệu đã index")
    ap.add_argument("--questions", default=str(HERE / "bench_questions.json"))
    ap.add_argument("--profiles", nargs="*", help=f"tên cấu hình muốn chạy (mặc định: {DEFAULT_PROFILES})")
    ap.add_argument("--with-small-reranker", action="store_true", help="thêm cấu hình reranker nhỏ")
    ap.add_argument("--out", default=str(HERE / "reports"))
    args = ap.parse_args()

    profiles = dict(PROFILES)
    if args.with_small_reranker:
        profiles.update(SMALL_RERANKER_PROFILE)
    if not args.profiles:
        args.profiles = DEFAULT_PROFILES + (list(SMALL_RERANKER_PROFILE) if args.with_small_reranker else [])
    if args.profiles:
        unknown = set(args.profiles) - set(profiles)
        if unknown:
            raise SystemExit(f"Không có cấu hình: {unknown}. Có: {list(profiles)}")
        profiles = {k: profiles[k] for k in args.profiles}

    if args.pdf:
        # File đã có trên kệ (cùng nội dung) thì dùng lại, không index trùng
        import hashlib

        from app import store
        from app.db import SessionLocal

        sha = hashlib.sha256(Path(args.pdf).read_bytes()).hexdigest()
        with SessionLocal() as db:
            existing = store.find_by_sha256(db, sha)
        if existing is not None:
            doc_id = existing.id
            print(f"Dùng lại tài liệu đã có: doc_id={doc_id} ({existing.title})")
        else:
            t = time.perf_counter()
            index = pipeline.ingest_pdf(
                args.pdf, title=Path(args.pdf).stem, filename=Path(args.pdf).name, file_sha256=sha
            )
            doc_id = index.doc_id
            print(f"Đã index: doc_id={doc_id}, {len(index.chunks)} đoạn, {time.perf_counter() - t:.1f}s")
    else:
        if not re.fullmatch(r"[0-9a-f]{32}", args.doc_id):
            raise SystemExit("doc_id phải là 32 ký tự hex")
        doc_id = args.doc_id

    data = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    runs = [run_profile(doc_id, name, ov, data) for name, ov in profiles.items()]
    path = write_report(runs, doc_id, Path(args.out))
    print(f"\nĐã ghi báo cáo: {path}")


if __name__ == "__main__":
    main()

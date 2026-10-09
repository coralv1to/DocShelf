"""Chạy bộ câu hỏi hội thoại trên giáo trình Triết học, ghi phiếu kết quả + chấm tự động.

Cách chạy (đứng ở backend/, Ollama + Postgres đang chạy):

    python -m eval.run_triet_hoc                  # bộ chính 144 lượt + bộ bổ sung 40 câu
    python -m eval.run_triet_hoc --quick          # bộ chạy nhanh (mục 10 của file md): 8 session, 48 lượt + bổ sung
    python -m eval.run_triet_hoc --suite extra    # chỉ bộ bổ sung (câu bẫy, sửa tiền đề, câu đơn có đáp án)
    python -m eval.run_triet_hoc --sessions S01 S04 --suite main
    python -m eval.run_triet_hoc --reparse        # đọc lại PDF bằng bộ cắt đoạn mới trước khi chạy
    python -m eval.run_triet_hoc --mode accurate

Bộ chính: mỗi session là MỘT cuộc trò chuyện mới, gửi lần lượt các câu hỏi, lịch sử lấy từ DB
(đi qua chat_service.ask giống /api/chat). Bộ bổ sung: mỗi câu một cuộc trò chuyện mới.
Các cuộc trò chuyện được lưu dưới tài khoản admin đầu tiên, tiêu đề "[Test ...]" -> mở giao diện xem lại được.

Kết quả ghi dần vào eval/reports/triet_<thời gian>.jsonl (mỗi lượt một dòng); cuối cùng xuất
eval/reports/triet_<thời gian>.md (chấm tự động, xem eval/cham_triet_hoc.py).
Chạy lỗi giữa chừng: thêm --resume <file.jsonl> để chạy tiếp phần còn thiếu.
"""
import argparse
import hashlib
import json
import re
import time
import traceback
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app import chat_service, pipeline, store
from app.db import SessionLocal
from app.models import ChatSession, Chunk, Document, User

from . import cham_triet_hoc

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
DEFAULT_MD = ROOT / "Bo_cau_hoi_danh_gia_RAG_Triet_hoc (1).md"
DEFAULT_PDF = ROOT / "Giáo trình Triết học Mác - Lê Nin.pdf"
EXTRA = HERE / "bo_sung_triet_hoc.json"
QUICK = ["S01", "S04", "S09", "S15", "S21", "S22", "S23", "S24"]

SESSION_RE = re.compile(r"^### Session (\d+) (.+)$")
ROW_RE = re.compile(r"^\| (S\d+) (T\d+) \| (.+?) \| ([DSAQO]) \| (.+?) \| (.+?) \|\s*$")


def parse_md(path: Path) -> list[dict]:
    sessions, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = SESSION_RE.match(line)
        if m:
            cur = {"id": f"S{int(m.group(1)):02d}", "title": m.group(2).strip(), "turns": []}
            sessions.append(cur)
            continue
        m = ROW_RE.match(line)
        if m and cur is not None and m.group(1) == cur["id"]:
            cur["turns"].append({"suite": "main", "session": m.group(1), "turn": m.group(2),
                                 "question": m.group(3).strip(), "type": m.group(4),
                                 "expected": m.group(5).strip(), "pages": m.group(6).strip()})
    return [s for s in sessions if s["turns"]]


def extra_sessions(path: Path) -> list[dict]:
    """Bộ bổ sung: mỗi câu là một 'session' 1 lượt."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for kind in ("trap", "premise", "single"):
        for item in data[kind]:
            pages = item.get("pages", [])
            out.append({"id": item["id"], "title": kind, "turns": [{
                "suite": "extra", "session": item["id"], "turn": "T01", "question": item["question"],
                "type": kind, "expected": " & ".join(item.get("must", [])) or "từ chối, không bịa",
                "pages": "; ".join(str(p) for p in pages) or "Không có", "must": item.get("must", []),
            }]})
    return out


def get_or_ingest(pdf: Path, admin: User | None, reparse: bool) -> str:
    data = pdf.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    with SessionLocal() as db:
        doc = store.find_by_sha256(db, sha)
        if doc is not None:
            print(f"Dùng lại tài liệu đã có: {doc.title} ({doc.id}, {doc.num_chunks} đoạn)", flush=True)
            if reparse:
                t = time.perf_counter()
                index = pipeline.reparse_document(doc.id, doc.title)
                print(f"Đã đọc lại PDF: {doc.num_chunks} -> {len(index.chunks)} đoạn, "
                      f"{time.perf_counter() - t:.0f} giây", flush=True)
            return doc.id
    print("Đang index PDF (đọc + cắt đoạn + embed), có thể mất vài phút...", flush=True)
    t = time.perf_counter()
    index = pipeline.ingest_pdf(str(pdf), title=pdf.stem, filename=pdf.name, file_sha256=sha,
                                uploaded_by=admin.id if admin else None)
    print(f"Index xong: {len(index.chunks)} đoạn, {time.perf_counter() - t:.0f} giây", flush=True)
    return index.doc_id


def dump_chunks(doc_id: str, out: Path) -> None:
    with SessionLocal() as db:
        rows = db.scalars(select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.position)).all()
        out.write_text(json.dumps([
            {"chunk_id": r.chunk_key, "page_start": r.page_start, "page_end": r.page_end,
             "header": r.header, "text": r.text} for r in rows
        ], ensure_ascii=False, indent=1), encoding="utf-8")


def run_session(doc_id: str, sess: dict, admin_id: int | None, mode: str | None, out) -> None:
    print(f"\n=== {sess['id']} {sess['title']}", flush=True)
    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        chat = ChatSession(user_id=admin_id, document_id=doc_id,
                           title=chat_service.make_title(f"[Test {sess['id']}] {sess['turns'][0]['question']}"))
        db.add(chat)
        db.commit()
        for turn in sess["turns"]:
            t = time.perf_counter()
            err, res = None, None
            try:
                res = chat_service.ask(db, doc, chat, turn["question"], mode=mode)
            except Exception as e:  # HTTPException, lỗi Ollama...
                db.rollback()
                err = getattr(e, "detail", None) or traceback.format_exc(limit=2)
            ms = round((time.perf_counter() - t) * 1000)
            row = {**turn, "chat_session_id": chat.id, "total_ms": ms, "error": err}
            if res is not None:
                d = res["debug"]
                row.update({
                    "answer": res["answer"], "found": res["found"], "example": res.get("example"),
                    "citations": [{"page": c.get("page"), "quote": c.get("quote"), "section": c.get("section")}
                                  for c in res["citations"]],
                    "route": d.get("route"), "refusal_kind": d.get("refusal_kind"),
                    "rejected_reason": d.get("rejected_reason"), "search_query": d.get("search_query"),
                    "steps": d.get("steps"), "best_score": d.get("best_score"), "gate": d.get("gate"),
                    "confidence": d.get("confidence"), "retrieved": d.get("retrieved"),
                    "context": d.get("context"), "raw_quotes": d.get("raw_quotes"),
                    "dropped_quotes": d.get("dropped_quotes"), "timings_ms": d.get("timings_ms"),
                    "mode": d.get("mode"),
                })
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            pages = sorted({c["page"] for c in row.get("citations", [])})
            status = "LỖI" if err else ("trả lời" if row.get("found") else f"từ chối/{row.get('refusal_kind')}")
            print(f"  {turn['session']} {turn['turn']} [{turn['type']}] {ms/1000:5.1f}s  {status:<22} "
                  f"trích trang {pages}  cần {turn['pages']}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=str(DEFAULT_MD))
    ap.add_argument("--pdf", default=str(DEFAULT_PDF))
    ap.add_argument("--suite", choices=["main", "extra", "all"], default="all")
    ap.add_argument("--sessions", nargs="*")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--mode", choices=["fast", "balanced", "accurate"])
    ap.add_argument("--reparse", action="store_true", help="đọc lại PDF bằng bộ cắt đoạn hiện tại trước khi chạy")
    ap.add_argument("--resume")
    args = ap.parse_args()

    sessions = []
    if args.suite in ("main", "all"):
        main_set = parse_md(Path(args.md))
        wanted = QUICK if args.quick else args.sessions
        sessions += [s for s in main_set if not wanted or s["id"] in wanted]
    if args.suite in ("extra", "all"):
        sessions += extra_sessions(EXTRA)
    print(f"{len(sessions)} cuộc trò chuyện, {sum(len(s['turns']) for s in sessions)} lượt", flush=True)

    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == "admin").order_by(User.id))
    doc_id = get_or_ingest(Path(args.pdf), admin, args.reparse)

    reports = HERE / "reports"
    reports.mkdir(exist_ok=True)
    if args.resume:
        path = Path(args.resume)
        lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        # Giữ session đã chạy ĐỦ và không lỗi; session dở dang chạy lại từ đầu (lịch sử phải liền mạch)
        full = {s["id"] for s in sessions
                if all(any(r["session"] == t["session"] and r["turn"] == t["turn"] and not r["error"]
                           for r in lines) for t in s["turns"])}
        keep = [r for r in lines if r["session"] in full]
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep), encoding="utf-8")
        sessions = [s for s in sessions if s["id"] not in full]
    else:
        path = reports / f"triet_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    print(f"Ghi kết quả vào {path}", flush=True)
    dump_chunks(doc_id, path.with_name(path.stem + "_chunks.json"))

    started = time.perf_counter()
    with path.open("a", encoding="utf-8") as out:
        for sess in sessions:
            run_session(doc_id, sess, admin.id if admin else None, args.mode, out)
    print(f"\n=== Chạy xong sau {(time.perf_counter() - started) / 60:.1f} phút.", flush=True)

    report = cham_triet_hoc.write_report(path)
    print(f"=== Báo cáo chấm tự động: {report}", flush=True)


if __name__ == "__main__":
    main()

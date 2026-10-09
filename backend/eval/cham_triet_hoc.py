"""Chấm tự động kết quả run_triet_hoc (file .jsonl) -> báo cáo Markdown.

    python -m eval.cham_triet_hoc eval/reports/triet_<thời gian>.jsonl

Chấm tự động chỉ đo được những gì kiểm tra bằng máy:
  - có trả lời hay từ chối, từ chối có đúng chỗ không (câu bẫy / ngoài nguồn);
  - đoạn đưa cho model có nằm đúng vùng trang cần không (tìm đúng chỗ);
  - trang trích dẫn có nằm trong vùng trang cần (±1) không;
  - câu trả lời có chứa các ý khóa không (bộ bổ sung).
Đúng/đủ nội dung, mạch hội thoại, độ dễ hiểu (thang 0-2 của file md) vẫn cần người đọc chấm:
báo cáo liệt kê sẵn câu hỏi, ý cần đạt và câu trả lời để chấm tay.
"""
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAGE_SLACK = 1  # chấp nhận lệch 1 trang (đoạn văn vắt qua trang)


def expected_pages(text: str) -> set[int]:
    """'80–81; 92' -> {80, 81, 92}. 'Không có ...' -> set()."""
    out: set[int] = set()
    for part in re.split(r"[;,]", text):
        nums = [int(x) for x in re.findall(r"\d+", part)]
        if len(nums) == 1:
            out.add(nums[0])
        elif len(nums) >= 2 and nums[1] >= nums[0] and nums[1] - nums[0] < 40:
            out |= set(range(nums[0], nums[1] + 1))
    return out


def near(pages: set[int], expected: set[int]) -> set[int]:
    return {p for p in pages if any(abs(p - e) <= PAGE_SLACK for e in expected)}


def context_pages(r: dict) -> set[int]:
    pages: set[int] = set()
    for c in r.get("context") or r.get("retrieved") or []:
        pages |= set(range(c["page_start"], c["page_end"] + 1))
    return pages


def has_terms(text: str, must: list[str]) -> bool:
    t = text.lower()
    return all(any(alt.strip() in t for alt in m.lower().split("|")) for m in must)


def grade(r: dict) -> dict:
    """Thêm các trường chấm tự động vào một dòng kết quả."""
    g = {"status": "", "retrieval_hit": None, "cite_ok": None}
    if r.get("error"):
        g["status"] = "LỖI"
        return g
    exp = expected_pages(r["pages"])
    cited = {c["page"] for c in r.get("citations", []) if c.get("page")}
    if exp:
        g["retrieval_hit"] = bool(near(context_pages(r), exp))
        if cited:
            g["cite_ok"] = cited <= near(cited, exp) | {p for p in cited if p == 214}  # 214 = mục lục
    typ = r["type"]
    found = r.get("found")
    if typ in ("O", "trap"):
        g["status"] = "ĐẠT" if not found else "XEM LẠI (trả lời câu ngoài nguồn)"
    elif typ == "Q":
        g["status"] = "XEM TAY (câu mơ hồ)"
    elif typ in ("premise", "single"):
        ok = bool(found) and has_terms(r.get("answer", ""), r.get("must", [])) and g["cite_ok"] is not False
        g["status"] = "ĐẠT" if ok else ("TỪ CHỐI NHẦM" if not found else "SAI/THIẾU Ý")
    else:  # D / S / A của bộ chính: đúng sai nội dung cần chấm tay
        if not found:
            g["status"] = "TỪ CHỐI" + (" (đã tìm đúng trang)" if g["retrieval_hit"] else "")
        elif g["cite_ok"] is False:
            g["status"] = "TRẢ LỜI, TRÍCH LỆCH TRANG"
        else:
            g["status"] = "TRẢ LỜI"
    return g


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "–"


def write_report(path: Path) -> Path:
    path = Path(path)
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    for r in rows:
        r["_g"] = grade(r)
    main = [r for r in rows if r.get("suite", "main") == "main"]
    extra = [r for r in rows if r.get("suite") == "extra"]
    ok_rows = [r for r in rows if not r.get("error")]
    L: list[str] = [f"# Kết quả chạy bộ câu hỏi Triết học — {path.stem}", ""]
    if ok_rows:
        modes = Counter(r.get("mode") for r in ok_rows)
        L.append(f"Chế độ: {', '.join(f'{m} ({n})' for m, n in modes.items())}. "
                 f"Số lượt: {len(rows)} (lỗi: {len(rows) - len(ok_rows)}).")
        L.append("")

    # ------------------------------------------------ bộ chính
    if main:
        dsa = [r for r in main if r["type"] in "DSA" and not r.get("error")]
        answered = [r for r in dsa if r.get("found")]
        hit = [r for r in dsa if r["_g"]["retrieval_hit"]]
        false_ref = [r for r in hit if not r.get("found")]
        cited = [r for r in answered if r["_g"]["cite_ok"] is not None]
        cite_ok = [r for r in cited if r["_g"]["cite_ok"]]
        o_rows = [r for r in main if r["type"] == "O" and not r.get("error")]
        L += ["## Bộ chính (file md)", "", "| Chỉ số | Kết quả |", "|---|---|",
              f"| Lượt D/S/A có trả lời | {pct(len(answered), len(dsa))} |",
              f"| Tìm đúng vùng trang (đoạn đưa cho model nằm trong vùng cần ±1) | {pct(len(hit), len(dsa))} |",
              f"| Từ chối dù đã tìm đúng vùng trang | {pct(len(false_ref), len(hit))} |",
              f"| Trang trích dẫn nằm trong vùng cần (±1), trên các lượt có trả lời | {pct(len(cite_ok), len(cited))} |",
              f"| Câu ngoài nguồn (O) được từ chối | {pct(sum(1 for r in o_rows if not r.get('found')), len(o_rows))} |",
              ""]
        by_type = defaultdict(list)
        for r in main:
            if not r.get("error"):
                by_type[r["type"]].append(r)
        L += ["| Loại | Số lượt | Có trả lời | Tìm đúng trang |", "|---|---|---|---|"]
        for t in "DSAQO":
            rs = by_type.get(t, [])
            if rs:
                L.append(f"| {t} | {len(rs)} | {pct(sum(1 for r in rs if r.get('found')), len(rs))} | "
                         f"{pct(sum(1 for r in rs if r['_g']['retrieval_hit']), sum(1 for r in rs if r['_g']['retrieval_hit'] is not None))} |")
        L.append("")
        sess = defaultdict(list)
        for r in main:
            sess[r["session"]].append(r)
        L += ["| Session | Có trả lời | Tìm đúng trang | Thời gian TB |", "|---|---|---|---|"]
        for s, rs in sess.items():
            good = [r for r in rs if not r.get("error")]
            L.append(f"| {s} | {sum(1 for r in good if r.get('found'))}/{len(rs)} | "
                     f"{sum(1 for r in good if r['_g']['retrieval_hit'])}/{sum(1 for r in good if r['_g']['retrieval_hit'] is not None)} | "
                     f"{statistics.mean(r['total_ms'] for r in rs) / 1000:.1f}s |")
        L.append("")

    # ------------------------------------------------ bộ bổ sung
    if extra:
        L += ["## Bộ bổ sung (chấm tự động hoàn toàn)", "", "| Nhóm | Đạt |", "|---|---|"]
        for kind, label in (("trap", "Câu bẫy: từ chối, không bịa"), ("premise", "Sửa tiền đề sai"),
                            ("single", "Câu đơn có đáp án")):
            rs = [r for r in extra if r["type"] == kind]
            if rs:
                L.append(f"| {label} | {pct(sum(1 for r in rs if r['_g']['status'] == 'ĐẠT'), len(rs))} |")
        L.append("")

    # ------------------------------------------------ tốc độ
    if ok_rows:
        ms = sorted(r["total_ms"] for r in ok_rows)
        p95 = ms[min(len(ms) - 1, int(round(0.95 * (len(ms) - 1))))]
        L += ["## Tốc độ", "",
              f"p50 = {statistics.median(ms) / 1000:.1f}s · p95 = {p95 / 1000:.1f}s · "
              f"lâu nhất = {ms[-1] / 1000:.1f}s ({len(ms)} lượt)", ""]

    # ------------------------------------------------ chi tiết để chấm tay
    L += ["## Chi tiết từng lượt", "",
          "| ID | Loại | Chấm tự động | Trích trang | Cần | Điểm | Thời gian | Câu hỏi | Câu trả lời (rút gọn) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ans = (r.get("answer") or r.get("error") or "").replace("\n", " ").replace("|", "/")
        if r.get("example"):
            ans += " [VÍ DỤ: " + r["example"].replace("\n", " ").replace("|", "/") + "]"
        pages = sorted({c["page"] for c in r.get("citations", []) if c.get("page")})
        L.append(f"| {r['session']} {r['turn']} | {r['type']} | {r['_g']['status']} | {pages or ''} | {r['pages']} | "
                 f"{r.get('best_score', '')} | {r['total_ms'] / 1000:.1f}s | {r['question'].replace('|', '/')} | "
                 f"{ans[:220]}{'…' if len(ans) > 220 else ''} |")
    out = path.with_suffix(".md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(write_report(Path(p)))

"""Tìm vị trí (tọa độ) của một câu trích dẫn trên trang PDF gốc để tô màu."""
import unicodedata
from pathlib import Path

import pymupdf
from rapidfuzz import fuzz

from .pdf_parser import GAP_RATIO, SUP_DIGITS, fix_degree, span_char

FUZZY_MIN = 85          # điểm khớp gần đúng tối thiểu (0-100)
EDGE_PUNCT = " .,;:\"'“”‘’()"

Box = tuple[float, float, float, float]


def _page_chars(page) -> list[tuple[str, Box | None, int]]:
    """Dựng lại text của trang, mỗi ký tự kèm (khung tọa độ, mã dòng).

    Dùng đúng quy tắc chèn dấu cách của pdf_parser để text khớp với text đã index.
    Ký tự được chèn thêm (dấu cách, xuống dòng) có khung = None.
    """
    out: list[tuple[str, Box | None, int]] = []
    line_id = 0
    data = page.get_text("rawdict")
    for block in data["blocks"]:
        for line in block.get("lines", []):
            line_id += 1
            prev_x1 = None
            for span in line["spans"]:
                gap = span["size"] * GAP_RATIO
                for ch in span["chars"]:
                    c = span_char(ch["c"], span)  # giống hệt pdf_parser
                    x0, y0, x1, y1 = ch["bbox"]
                    if prev_x1 is not None and c != " " and out and out[-1][0] != " " and x0 - prev_x1 > gap:
                        out.append((" ", None, line_id))
                    out.append((c, (x0, y0, x1, y1), line_id))
                    prev_x1 = x1
            # Ký hiệu độ: sửa trong phạm vi dòng vừa dựng (giống pdf_parser)
            first = next((k for k in range(len(out) - 1, -1, -1) if out[k][2] != line_id), -1) + 1
            seg = [c for c, _, _ in out[first:]]
            fix_degree(seg)
            out[first:] = [(c, box, lid) for c, (_, box, lid) in zip(seg, out[first:])]
            # Hết dòng: nối từ bị ngắt bằng gạch nối, còn lại thì thêm dấu cách
            if out and out[-1][0] == "­":
                out.pop()
            elif out and out[-1][0] != "-":
                out.append((" ", None, line_id))
    return out


def _normalize_with_map(chars):
    """Chuẩn hóa (NFD, chữ thường, gộp khoảng trắng) và giữ ánh xạ về ký tự gốc."""
    text: list[str] = []
    index: list[int] = []  # vị trí trong text chuẩn hóa -> vị trí trong chars
    for i, (c, _, _) in enumerate(chars):
        if c in SUP_DIGITS:
            continue  # số mũ / số chú thích: không tính khi so khớp
        for nc in unicodedata.normalize("NFD", c).lower():
            if nc.isspace():
                if text and text[-1] == " ":
                    continue
                nc = " "
            text.append(nc)
            index.append(i)
    return "".join(text), index


def _normalize_quote(quote: str) -> str:
    q = unicodedata.normalize("NFD", quote.replace("­", "").translate({ord(d): None for d in SUP_DIGITS})).lower()
    return " ".join(q.split()).strip(EDGE_PUNCT)


def _find_span(q: str, text: str) -> tuple[int, int, float] | None:
    """Trả về (đầu, cuối, điểm). Khớp chính xác = 100 điểm."""
    if len(q) < 8:
        return None
    start = text.find(q)
    if start >= 0:
        return start, start + len(q), 100.0
    m = fuzz.partial_ratio_alignment(q, text, score_cutoff=FUZZY_MIN)
    if m is None:
        return None
    return m.dest_start, m.dest_end, m.score


def _boxes_to_rects(chars, idx_range, page_w: float, page_h: float) -> list[list[float]]:
    """Gộp khung các ký tự theo từng dòng -> mỗi dòng 1 hình chữ nhật, tọa độ tương đối 0..1."""
    lines: dict[int, list[float]] = {}
    for i in idx_range:
        _, box, line_id = chars[i]
        if box is None:
            continue
        r = lines.setdefault(line_id, [box[0], box[1], box[2], box[3]])
        r[0], r[1] = min(r[0], box[0]), min(r[1], box[1])
        r[2], r[3] = max(r[2], box[2]), max(r[3], box[3])
    return [
        [round(x0 / page_w, 4), round(y0 / page_h, 4), round(x1 / page_w, 4), round(y1 / page_h, 4)]
        for x0, y0, x1, y1 in lines.values()
    ]


def locate_quote(pdf_path: str | Path, quote: str, page_start: int, page_end: int) -> dict | None:
    """Tìm câu trích trong các trang page_start..page_end (đánh số từ 1).

    Trả về {"page": số_trang, "rects": [[x0, y0, x1, y1], ...]} hoặc None nếu không tìm thấy.
    """
    q = _normalize_quote(quote)
    best = None  # (điểm, số_trang, rects): duyệt HẾT các trang rồi chọn trang khớp tốt nhất
    with pymupdf.open(pdf_path) as doc:
        last = min(page_end, doc.page_count)
        for page_no in range(max(1, page_start), last + 1):
            page = doc[page_no - 1]
            chars = _page_chars(page)
            text, index = _normalize_with_map(chars)
            span = _find_span(q, text)
            if span is None:
                continue
            s, e, score = span
            if best is not None and score <= best[0]:
                continue
            rects = _boxes_to_rects(chars, range(index[s], index[e - 1] + 1), page.rect.width, page.rect.height)
            if rects:
                best = (score, page_no, rects)
            if score == 100.0:
                break  # khớp chính xác thì không cần dò tiếp
    return {"page": best[1], "rects": best[2]} if best else None


def render_page_png(pdf_path: str | Path, page_no: int, dpi: int = 110) -> bytes:
    """Vẽ một trang PDF thành ảnh PNG."""
    with pymupdf.open(pdf_path) as doc:
        if not 1 <= page_no <= doc.page_count:
            raise IndexError("Số trang không hợp lệ.")
        return doc[page_no - 1].get_pixmap(dpi=dpi).tobytes("png")


def page_count(pdf_path: str | Path) -> int:
    with pymupdf.open(pdf_path) as doc:
        return doc.page_count

import re
import unicodedata

from rapidfuzz import fuzz

from .chunker import Chunk

MIN_QUOTE_CHARS = 8


_DROP_SUP = {ord(d): None for d in "⁰¹²³⁴⁵⁶⁷⁸⁹"}  # số mũ / số chú thích (xem pdf_parser.SUP_DIGITS)


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s).translate(_DROP_SUP).lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:\"'“”‘’()")


def _find_quote(quote: str, chunks: list[Chunk], fuzzy_threshold: int) -> Chunk | None:
    q = normalize(quote)
    if len(q) < MIN_QUOTE_CHARS:
        return None  # quá ngắn, không đủ làm bằng chứng

    # 1) Khớp chính xác (sau chuẩn hóa)
    for c in chunks:
        if q in normalize(c.text):
            return c

    # 2) Khớp gần đúng: chấp nhận sai lệch nhỏ (model chép sai 1-2 chữ)
    best, best_score = None, 0.0
    for c in chunks:
        score = fuzz.partial_ratio(q, normalize(c.text))
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= fuzzy_threshold else None


def verify_quotes(quotes: list[str], chunks: list[Chunk], fuzzy_threshold: int = 90) -> list[dict] | None:
    """Trả về danh sách trích dẫn kèm trang nếu TẤT CẢ đều có thật; ngược lại trả về None."""
    if not quotes:
        return None
    citations = []
    for q in quotes:
        c = _find_quote(q, chunks, fuzzy_threshold)
        if c is None:
            return None
        citations.append(
            {
                "quote": q,
                "chunk_id": c.id,
                "page": c.page_start,        # sẽ được locate.py chỉnh lại thành trang chính xác
                "page_start": c.page_start,
                "page_end": c.page_end,
                "section": c.header,
                "rects": [],                 # tọa độ tô màu, locate.py điền vào
            }
        )

    # Bỏ trích dẫn trùng: câu nào nằm trọn trong một câu trích khác (sau chuẩn hóa) thì bỏ
    unique: list[dict] = []
    for c in sorted(citations, key=lambda x: -len(normalize(x["quote"]))):
        q = normalize(c["quote"])
        if not any(q in normalize(u["quote"]) for u in unique):
            unique.append(c)
    return [c for c in citations if any(c is u for u in unique)]  # giữ thứ tự ban đầu



def verify_quotes_partial(
    quotes: list[str], chunks: list[Chunk], fuzzy_threshold: int = 90
) -> tuple[list[dict] | None, list[str]]:
    """Như verify_quotes nhưng chấp nhận MỘT PHẦN: bỏ câu trích chép lệch, giữ câu kiểm chứng được.

    Đạt khi còn ít nhất 1 câu VÀ không ít hơn một nửa số câu model đưa ra
    (model bịa phần lớn trích dẫn thì cả câu trả lời không đáng tin).
    Trả về (trích_dẫn_hợp_lệ | None, các_câu_bị_bỏ).
    """
    if not quotes:
        return None, []
    good, dropped = [], []
    for q in quotes:
        (good if _find_quote(q, chunks, fuzzy_threshold) is not None else dropped).append(q)
    if not good or len(good) * 2 < len(quotes):
        return None, dropped
    return verify_quotes(good, chunks, fuzzy_threshold), dropped

import re
import time
import uuid

from . import chunker, config, embedder, followup, intent, llm, locate, memory, pdf_parser, prompts, store, verify
from . import options as opts_mod
from .options import Options

REFUSAL = "Tài liệu không có thông tin để trả lời câu hỏi này."  # bản ngắn, lưu vào lịch sử hội thoại
UNVERIFIED = "Không kiểm chứng được câu trả lời từ tài liệu."   # bản ngắn khi trích dẫn không khớp

OUTLINE_MAX_ITEMS = 16  # số mục tối đa liệt kê trong câu trả lời tổng quan / gợi ý
TOP_LEVEL_RE = re.compile(r"^(chương|phần|chapter|part)\b", re.IGNORECASE)
# Câu hỏi vị trí: "hàm append ở trang nào", "lưu đồ nằm ở mục nào"
LOCATION_RE = re.compile(
    r"\s*(ở|nằm ở|nằm trong|thuộc|tại)?\s*(trang|mục|chương|phần)\s+(nào|mấy|bao nhiêu)\s*\??"
    r"|\s*(nằm )?ở đâu( trong tài liệu)?\s*\??",
    re.IGNORECASE,
)
# Hình / bảng
CAPTION_RE = re.compile(r"^(Hình|Bảng|Figure|Table)\s+(\d+(?:\.\d+)+)\.?\s+(\S.*)$")
FIGURE_WORD_RE = re.compile(r"\b(hình|sơ đồ|lưu đồ|biểu đồ|bảng|minh họa|minh hoạ|figure|table|diagram)\b", re.IGNORECASE)
FIGURE_LABEL_RE = re.compile(r"\b(hình|bảng|figure|table)\s+(\d+(?:\.\d+)+)", re.IGNORECASE)
SHOW_RE = re.compile(r"\b(cho (tôi|mình|em)|xem|hiển thị|đưa ra|vẽ|mở|ở đâu|trang nào|tìm)\b", re.IGNORECASE)
FIGURE_STOP = set(
    "cho tôi mình em xem hãy vẽ hiển thị đưa ra tìm mở ở đâu trang nào là gì như thế nào sơ đồ lưu đồ "
    "hình bảng biểu minh họa hoạ của về các những một và trong tài liệu được có".split()
)
FIGURE_MIN_F1 = 0.5
CHAPTER_NO_RE = re.compile(r"\b(?:chương|chapter)\s+(\d+|[ivxlc]+)\b", re.IGNORECASE)

OVERVIEW_ID = "overview"
# Ngữ cảnh đưa cho model: ngoài các đoạn tìm được, thêm đoạn liền trước/liền sau CÙNG MỤC của 2 đoạn tốt nhất
# (định nghĩa, lập luận hay bị cắt ngang giữa 2 đoạn). Tổng không quá CONTEXT_MAX_WORDS từ (~2.500 token).
CONTEXT_MAX_WORDS = 1800
EXPAND_TOP = 2
OVERVIEW_MAX_WORDS = 800  # giới hạn độ dài đoạn tổng quan (~1.100 token)
BARE_CHAPTER_RE = re.compile(r"^(chương|phần|mục)\s+\w+\.?$", re.IGNORECASE)  # 'CHƯƠNG 6.' không có tên

# Câu hỏi về toàn bộ tài liệu: "tài liệu nói về gì", "tóm tắt", "gồm những phần nào"...
OVERVIEW_QUESTION_RE = re.compile(
    r"(nói về|chủ đề|tóm tắt|nội dung chính|gồm (những|các|mấy)|có (những|mấy) (phần|mục|chương)|mục lục"
    r"|bắt đầu (học )?từ đâu|nên (học|đọc) (phần|chương|mục) nào trước"
    r"|what is (this|the) (document|paper|file) about|summari[sz]e|main topics?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------- INDEXING
PART_LINE_RE = re.compile(r"^(phần|part|phụ lục|appendix)\b", re.IGNORECASE)
CHAPTER_LINE_RE = re.compile(r"^(chương|chapter)\b", re.IGNORECASE)
ROMAN_LINE_RE = re.compile(r"^[IVX]{1,4}\s*[-.–]\s+\S")
REVIEW_TITLE_RE = re.compile(r"^(câu hỏi|bài tập)", re.IGNORECASE)
ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def _title_depth(title: str) -> int:
    """Cấp của tiêu đề: phần = 0, chương = 1, mục La Mã 'I-' = 2, '1.' = 3, '1.1' = 4, '1.1.1' = 5..."""
    if PART_LINE_RE.match(title):
        return 0
    if CHAPTER_LINE_RE.match(title):
        return 1
    if ROMAN_LINE_RE.match(title):
        return 2
    m = re.match(r"^(\d+(?:\.\d+)*)", title)
    return 3 + m.group(1).count(".") if m else 3


def _number_value(token: str) -> int | None:
    """'3' -> 3, 'III' -> 3, 'xiv' -> 14."""
    if token.isdigit():
        return int(token)
    vals = [ROMAN_VALUES.get(ch) for ch in token.lower()]
    if not vals or None in vals:
        return None
    total = 0
    for k, v in enumerate(vals):
        total += -v if k + 1 < len(vals) and vals[k + 1] > v else v
    return total


def _build_overview_chunk(title: str, chunks: list[chunker.Chunk]) -> chunker.Chunk | None:
    """Đoạn tổng quan: dàn ý tài liệu, gồm tiêu đề nguyên văn lấy từ tài liệu.

    Tài liệu dài có hàng trăm tiêu đề -> giữ các cấp lớn trước (chương, rồi mục 1.1...),
    chỉ thêm cấp nhỏ hơn khi còn chỗ trong giới hạn OVERVIEW_MAX_WORDS.
    """
    entries: list[tuple[str, int, int]] = []  # (tiêu đề, cấp, trang)
    seen: set[str] = set()
    for c in chunks:
        for t in c.header.split(" > ")[1:]:  # bỏ tên file ở đầu
            if t not in seen and not BARE_CHAPTER_RE.match(t) and not REVIEW_TITLE_RE.match(t):
                seen.add(t)
                entries.append((t, _title_depth(t), c.page_start))
    if not entries:
        return None

    chosen = entries
    for max_depth in range(max(d for _, d, _ in entries), -1, -1):
        chosen = [e for e in entries if e[1] <= max_depth]
        if sum(len(t.split()) for t, _, _ in chosen) <= OVERVIEW_MAX_WORDS:
            break
    pages = [p for _, _, p in chosen]
    return chunker.Chunk(
        id=OVERVIEW_ID,
        text="\n".join(t for t, _, _ in chosen),
        header=f"{title} > Tổng quan tài liệu – các mục chính",
        page_start=min(pages),
        page_end=max(pages),
    )


def _build_index(pdf_path: str, title: str, doc_id: str) -> store.DocumentIndex:
    """Đọc PDF -> cắt đoạn (+ đoạn tổng quan) -> embed."""
    lines = pdf_parser.parse_pdf(pdf_path)
    if not lines:
        raise ValueError("Không trích được chữ nào từ PDF. Có thể đây là bản scan, cần OCR.")

    chunks = chunker.chunk_document(lines, title, config.CHUNK_WORDS, config.CHUNK_OVERLAP_WORDS)
    overview = _build_overview_chunk(title, chunks)
    if overview is not None:
        chunks.append(overview)

    vectors = embedder.embed_documents([c.text_for_search() for c in chunks])
    return store.DocumentIndex(doc_id, title, chunks, vectors)


def reparse_document(doc_id: str, title: str) -> store.DocumentIndex:
    """Đọc lại PDF gốc của tài liệu đã có bằng bộ đọc/cắt đoạn hiện tại (sau khi nâng cấp code)."""
    pdf = store.source_pdf(doc_id)
    if not pdf.exists():
        raise ValueError("Không còn file PDF gốc của tài liệu này.")
    index = _build_index(str(pdf), title, doc_id)
    store.replace_chunks(index)
    forget_document(doc_id)
    return index


def ingest_pdf(pdf_path: str, title: str, **meta) -> store.DocumentIndex:
    """Đọc PDF -> cắt đoạn -> embed -> lưu DB.

    meta: thông tin thêm ghi vào bảng documents (filename, file_sha256, uploaded_by).
    """
    index = _build_index(pdf_path, title, uuid.uuid4().hex)
    meta.setdefault("filename", f"{title}.pdf")
    store.save_index(index, pdf_path, num_pages=locate.page_count(pdf_path), **meta)
    return index


def forget_document(doc_id: str) -> None:
    """Bỏ cache riêng của pipeline khi tài liệu bị xóa."""
    _caption_cache.pop(doc_id, None)
    _outline_cache.pop(doc_id, None)


# ---------------------------------------------------------------- QUERY
def _rewrite_question(history: list[dict], question: str) -> str:
    history_text = "\n".join(
        ("Hỏi: " if m["role"] == "user" else "Đáp: ") + m["content"] for m in history
    )
    prompt = prompts.REWRITE_PROMPT.format(history=history_text, question=question)
    out = llm.chat([{"role": "user", "content": prompt}]).strip()
    first_line = out.splitlines()[0].strip() if out else ""
    return first_line or question


def _retrieve(index: store.DocumentIndex, query: str, opts: Options):
    """Tìm theo nghĩa (vector) + theo từ khóa (BM25), gộp bằng RRF.

    Trả về (q_vec, ứng_viên, kết_quả_vector, kết_quả_bm25); mỗi kết quả là [(vị_trí_đoạn, điểm)].
    """
    q_vec = embedder.embed_query(query)
    vector_hits = index.vector_search(q_vec, opts.top_k_retrieve)
    if not opts.use_bm25:
        return q_vec, vector_hits, vector_hits, []

    from .bm25 import BM25Index, rrf_fuse  # chỉ import khi bật cờ

    if index.bm25 is None:
        index.bm25 = BM25Index(index.get_tokens())  # token đã tách sẵn lúc upload -> dựng rất nhanh
    keyword_hits = index.bm25.search(query, opts.top_k_retrieve)
    fused = rrf_fuse([vector_hits, keyword_hits])[: opts.top_k_retrieve]
    return q_vec, fused, vector_hits, keyword_hits


CLEAR_BM25_MARGIN = 1.25  # đoạn đứng đầu phải có điểm từ khóa >= 1.25 lần đoạn thứ hai


def _clear_winner(vector_hits: list, keyword_hits: list) -> tuple[int | None, str]:
    """(vị trí đoạn "thắng rõ ràng" hoặc None, lý do) — đoạn thắng rõ ràng thì không cần rerank xác nhận.

    Rõ ràng = tìm theo nghĩa và tìm theo từ khóa cùng chọn một đoạn đứng đầu, VÀ theo từ khóa đoạn đó
    vượt hẳn đoạn thứ hai. Chỉ dùng cho câu hỏi vị trí ("append ở trang nào"): câu trả lời chỉ là
    tên mục + số trang, không gọi LLM. Từ cần tìm không có trong tài liệu thì BM25 không ra kết quả
    -> không "rõ ràng" -> vẫn rerank và từ chối như bình thường.
    """
    if not keyword_hits:
        return None, "từ khóa không có trong tài liệu"
    if not vector_hits or vector_hits[0][0] != keyword_hits[0][0]:
        return None, "tìm theo nghĩa và theo từ khóa chọn 2 đoạn khác nhau"
    if len(keyword_hits) > 1 and keyword_hits[0][1] < CLEAR_BM25_MARGIN * keyword_hits[1][1]:
        return None, "từ khóa xuất hiện nhiều ở nhiều đoạn"
    return keyword_hits[0][0], ""


def _expand_context(index: store.DocumentIndex, top: list[tuple[int, float]]) -> list[int]:
    """Vị trí các đoạn đưa cho model: các đoạn tìm được + đoạn kề cùng mục của EXPAND_TOP đoạn tốt nhất."""
    chosen = [i for i, _ in top]
    words = sum(len(index.chunks[i].text.split()) for i in chosen)
    for i, _ in top[:EXPAND_TOP]:
        if index.chunks[i].id == OVERVIEW_ID:
            continue
        for j in (i + 1, i - 1):  # đoạn sau trước (thường là phần tiếp của lập luận), rồi đoạn trước
            if not 0 <= j < len(index.chunks) or j in chosen:
                continue
            c = index.chunks[j]
            if c.id == OVERVIEW_ID or c.header != index.chunks[i].header:
                continue
            n = len(c.text.split())
            if words + n > CONTEXT_MAX_WORDS:
                continue
            chosen.append(j)
            words += n
    return sorted(chosen)  # giữ thứ tự xuất hiện trong văn bản


def _overview_position(index: store.DocumentIndex) -> int | None:
    for i, c in enumerate(index.chunks):
        if c.id == OVERVIEW_ID:
            return i
    return None


def _page_range_for(index: store.DocumentIndex, citation: dict) -> tuple[int, int]:
    """Khoảng trang cần dò để tìm câu trích.

    Đoạn thường chỉ trải 1-2 trang. Riêng đoạn tổng quan trải cả tài liệu (có thể >100 trang),
    nên tra tiêu đề được trích trong header các đoạn để biết nó nằm ở trang nào.
    """
    if citation["chunk_id"] != OVERVIEW_ID:
        return citation["page_start"], citation["page_end"]
    quote = " ".join(citation["quote"].split()).lower()
    for c in index.chunks:
        if c.id != OVERVIEW_ID and quote in c.header.lower():
            return c.page_start, c.page_start + 1
    return citation["page_start"], citation["page_start"]


# ---------------------------------------------------------------- DÀN Ý (không cần LLM)
_outline_cache: dict[str, list[str]] = {}


def _outline_lines(index: store.DocumentIndex) -> list[str]:
    """Dàn ý ĐẦY ĐỦ (mọi tiêu đề, theo thứ tự), dựng từ header các đoạn.

    Đoạn tổng quan chỉ giữ các cấp lớn cho vừa giới hạn từ; trả lời "Chương 7 gồm những mục nào?"
    cần cả các cấp nhỏ nên dựng lại từ header.
    """
    if index.doc_id in _outline_cache:
        return _outline_cache[index.doc_id]
    lines, seen = [], set()
    for c in index.chunks:
        if c.id == OVERVIEW_ID:
            continue
        for t in c.header.split(" > ")[1:]:
            if t not in seen and not BARE_CHAPTER_RE.match(t) and not REVIEW_TITLE_RE.match(t):
                seen.add(t)
                lines.append(t)
    if not lines:  # tài liệu cũ không có header theo mục: dùng đoạn tổng quan
        pos = _overview_position(index)
        lines = index.chunks[pos].text.splitlines() if pos is not None else []
    _outline_cache[index.doc_id] = lines
    return lines


def _top_level(lines: list[str]) -> list[str]:
    """Các mục cấp cao nhất: ưu tiên dòng 'Chương ...', rồi 'Phần ...'; nếu không có thì lấy cấp nhỏ nhất."""
    for pattern in (CHAPTER_LINE_RE, PART_LINE_RE):
        found = [t for t in lines if pattern.match(t)]
        if len(found) >= 2:
            return found
    if not lines:
        return []
    min_depth = min(_title_depth(t) for t in lines)
    return [t for t in lines if _title_depth(t) == min_depth]


def _pretty(title: str) -> str:
    """'CHƯƠNG 1. TỔNG QUAN NGÀNH...' -> 'Chương 1. Tổng quan ngành...' (chỉ đổi khi cả dòng viết hoa)."""
    if not title.isupper():
        return title
    low = title.lower()
    # Viết hoa chữ đầu, và chữ đầu sau số chương: 'chương 1. tổng quan' -> 'Chương 1. Tổng quan'
    low = re.sub(r"^((?:chương|phần|chapter|part)\s+\w+[.:]?\s*)(\w)", lambda m: m.group(1) + m.group(2).upper(), low)
    return low[0].upper() + low[1:]


def _overview_answer(index: store.DocumentIndex, question: str) -> tuple[str, list[str]] | None:
    """Trả lời câu hỏi tổng quan bằng dàn ý lấy nguyên văn từ tài liệu.

    Trả về (câu_trả_lời, danh_sách_tiêu_đề_làm_trích_dẫn) hoặc None nếu tài liệu không có dàn ý.
    """
    lines = _outline_lines(index)
    if not lines:
        return None

    # Hỏi về một chương cụ thể: "Chương 3 gồm những mục nào?" (sách đánh số 3 hay III đều được)
    m = CHAPTER_NO_RE.search(question)
    if m:
        n = _number_value(m.group(1))
        start = None
        for k, t in enumerate(lines):
            mm = re.match(r"^(?:chương|chapter)\s+(\d+|[ivxlc]+)\b", t, re.IGNORECASE)
            if mm and n is not None and _number_value(mm.group(1)) == n:
                start = k
                break
        subs = []
        if start is not None:
            head = lines[start]
            end = next((k for k in range(start + 1, len(lines)) if TOP_LEVEL_RE.match(lines[k])), len(lines))
            body = lines[start + 1 : end]
            # Sách đánh số mục theo chương ('3.1', '3.2'): chỉ lấy mục đúng chương (bỏ dòng lạc như '2.7 ...')
            subs = [t for t in body if re.match(rf"^{n}\.\d+(\s|$)", t)]
            if not subs and body:  # sách đánh số kiểu 'I-', '1.': lấy các mục cấp cao nhất trong chương
                top_depth = min(_title_depth(t) for t in body)
                subs = [t for t in body if _title_depth(t) == top_depth]
        if start is not None and subs:
            body = "\n".join(f"• {_pretty(t)}" for t in subs[:OUTLINE_MAX_ITEMS])
            return f"{_pretty(head)} gồm {len(subs)} mục:\n{body}", [head] + subs[:OUTLINE_MAX_ITEMS]

    top = _top_level(lines)
    if len(top) < 2:
        return None
    shown = top[:OUTLINE_MAX_ITEMS]
    body = "\n".join(f"• {_pretty(t)}" for t in shown)
    more = f"\n… và {len(top) - len(shown)} mục khác." if len(top) > len(shown) else ""
    chapters = sum(1 for t in top if CHAPTER_LINE_RE.match(t))
    unit = f"{chapters} chương" if chapters >= 2 else f"{len(top)} phần chính"
    hint = (
        "Bạn có thể hỏi chi tiết từng chương, ví dụ: “Chương 2 gồm những mục nào?”"
        if chapters >= 2
        else "Bạn có thể hỏi chi tiết về một mục bất kỳ ở trên."
    )
    answer = f"Tài liệu “{index.title}” gồm {unit}:\n{body}{more}\n\n{hint}"
    return answer, shown


def _location_answer(index: store.DocumentIndex, top: list[tuple[int, float]], gate: float):
    """Trả lời 'ở trang nào' bằng vị trí các đoạn tìm được (không cần LLM).

    Lấy tối đa 3 mục khác nhau có điểm >= ngưỡng và >= một nửa điểm cao nhất.
    Trích dẫn là tiêu đề mục (nguyên văn) để bấm vào mở đúng trang.
    """
    if not top:
        return None
    best = top[0][1]
    items, seen = [], set()
    for i, score in top:
        c = index.chunks[i]
        if c.id == OVERVIEW_ID or score < gate or score < best / 2:
            continue
        section = c.header.split(" > ")[-1]
        if section in seen:
            continue
        seen.add(section)
        items.append((c, section))
        if len(items) == 3:
            break
    if not items:
        return None

    def pages(c):
        return f"trang {c.page_start}" if c.page_start == c.page_end else f"trang {c.page_start}–{c.page_end}"

    lines = [f"• Mục {_pretty(sec)} — {pages(c)}" for c, sec in items]
    answer = "Nội dung này nằm ở:" + "\n" + "\n".join(lines) + "\n\nBấm vào nguồn bên dưới để mở đúng trang."
    citations = [
        {"quote": sec, "chunk_id": c.id, "page": c.page_start, "page_start": c.page_start,
         "page_end": c.page_end, "section": c.header, "rects": []}
        for c, sec in items
    ]
    return answer, citations


# ---------------------------------------------------------------- HÌNH / BẢNG (theo chú thích)
_caption_cache: dict[str, list[dict]] = {}


def _captions(index: store.DocumentIndex) -> list[dict]:
    """Chú thích hình/bảng nguyên văn: 'Hình 2.5 Sơ đồ thuật toán...' (bỏ câu nhắc lại như 'Hình 2.5 là ...')."""
    if index.doc_id in _caption_cache:
        return _caption_cache[index.doc_id]
    caps, seen = [], set()
    for i, c in enumerate(index.chunks):
        if c.id == OVERVIEW_ID:
            continue
        for line in c.text.split("\n"):
            m = CAPTION_RE.match(line.strip())
            if not m or not m.group(3)[0].isupper():  # 'Hình 2.5 là ...' là câu văn, không phải chú thích
                continue
            label = f"{m.group(1)} {m.group(2)}"
            if label.lower() not in seen:
                seen.add(label.lower())
                caps.append({"label": label, "title": m.group(3), "line": line.strip(), "pos": i})
    _caption_cache[index.doc_id] = caps
    return caps


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"\w+", s.lower()) if w not in FIGURE_STOP}


def _match_figure(index: store.DocumentIndex, question: str, top: list[tuple[int, float]]) -> dict | None:
    """Tìm hình/bảng mà câu hỏi nhắc tới.

    - Câu hỏi ghi rõ 'Hình 2.5' -> tra thẳng.
    - Ngược lại: chỉ xét hình/bảng nằm trong các đoạn tìm được (reranker đã lọc rất chính xác),
      chọn chú thích trùng từ nhiều nhất (F1 hai chiều), tối thiểu FIGURE_MIN_F1.
    """
    caps = _captions(index)
    m = FIGURE_LABEL_RE.search(question)
    if m:
        want = f"{m.group(1)} {m.group(2)}".lower()
        return next((c for c in caps if c["label"].lower() == want), None)
    if not FIGURE_WORD_RE.search(question):
        return None
    positions = {i for i, _ in top}
    q = _words(question)
    best, best_f1 = None, 0.0
    for cap in caps:
        if cap["pos"] not in positions:
            continue
        t = _words(cap["title"])
        common = len(q & t)
        if not common:
            continue
        p, r = common / len(t), common / len(q)
        f1 = 2 * p * r / (p + r)
        if f1 > best_f1:
            best, best_f1 = cap, f1
    return best if best_f1 >= FIGURE_MIN_F1 else None


def _figure_description(index: store.DocumentIndex, cap: dict) -> tuple[str, int] | None:
    """Câu văn mô tả hình trong bài, ví dụ 'Hình 2.5 là sơ đồ ... rồi xuất kết quả, ...'. Lấy nguyên văn."""
    label = cap["label"]
    for i, c in enumerate(index.chunks):
        if c.id == OVERVIEW_ID:
            continue
        lines = c.text.split("\n")
        for k, line in enumerate(lines):
            st = line.strip()
            if st.startswith(label + " ") and st != cap["line"] and not st[len(label) + 1 :][:1].isupper():
                text = " ".join(x.strip() for x in lines[k : k + 4])
                end = text.find(". ", len(label))
                sentence = text[: end + 1] if end > 0 else text
                return sentence, i
    return None


def _figure_citation(index: store.DocumentIndex, quote: str, pos: int) -> dict:
    c = index.chunks[pos]
    return {"quote": quote, "chunk_id": c.id, "page": c.page_start, "page_start": c.page_start,
            "page_end": c.page_end, "section": c.header, "rects": []}


def _refusal_text(index: store.DocumentIndex, reason: str, top_headers: list[tuple[str, int]]) -> str:
    """Câu từ chối dễ hiểu, kèm gợi ý hỏi gì / xem ở đâu."""
    if reason == "model_not_found" and top_headers:
        lines = [
            "Mình tìm thấy mục có vẻ liên quan nhưng không rút ra được câu trả lời chắc chắn từ nội dung.",
            "\nBạn có thể xem trực tiếp các mục sau, hoặc hỏi lại cụ thể hơn:",
        ]
        lines += [f"• {_pretty(h)} (trang {p})" for h, p in top_headers]
        return "\n".join(lines)
    if reason in ("quote_not_verified", "invalid_json"):
        lines = [
            "Mình tìm thấy vài đoạn có vẻ liên quan nhưng không kiểm chứng được câu trả lời "
            "bằng trích dẫn nguyên văn, nên không trả lời để tránh sai.",
        ]
        if top_headers:
            lines.append("\nBạn có thể xem trực tiếp các mục sau, hoặc hỏi lại cụ thể hơn:")
            lines += [f"• {_pretty(h)} (trang {p})" for h, p in top_headers]
        return "\n".join(lines)

    lines = [f"Tài liệu “{index.title}” không có thông tin để trả lời câu hỏi này."]
    top = _top_level(_outline_lines(index))
    if top:
        shown = top[:OUTLINE_MAX_ITEMS]
        lines.append("\nTài liệu này chủ yếu nói về:")
        lines += [f"• {_pretty(t)}" for t in shown]
        if len(top) > len(shown):
            lines.append(f"… và {len(top) - len(shown)} mục khác.")
    return "\n".join(lines)


def _attach_locations(index: store.DocumentIndex, citations: list[dict]) -> None:
    """Điền trang chính xác + tọa độ tô màu cho từng trích dẫn (nếu còn file PDF gốc)."""
    pdf = store.source_pdf(index.doc_id)
    if not pdf.exists():
        return
    for c in citations:
        start, end = _page_range_for(index, c)
        try:
            loc = locate.locate_quote(pdf, c["quote"], start, end)
        except Exception:
            loc = None  # tô màu là phần phụ: lỗi ở đây không được làm hỏng câu trả lời
        if loc is not None:
            c["page"] = loc["page"]
            c["rects"] = loc["rects"]


def answer_question(
    doc_id: str,
    session_id: str,
    question: str,
    history: list[dict] | None = None,
    opts: Options | None = None,
) -> dict:
    """Trả lời một câu hỏi về tài liệu doc_id.

    history: lịch sử hội thoại [{"role", "content"}] do API đọc từ DB và truyền vào.
             None -> dùng bộ nhớ tạm trong RAM theo session_id (benchmark dùng cách này).
    opts:    chế độ trả lời (xem options.py). None -> đọc từ config (benchmark).

    Kết quả có thêm "history_answer": bản ngắn của câu trả lời để lưu làm lịch sử
    (None nghĩa là không đưa lượt này vào lịch sử, vd câu chào hỏi).
    """
    opts = opts or opts_mod.from_config()
    index = store.load_index(doc_id)
    if index is None:
        raise ValueError("Không tìm thấy tài liệu. Hãy upload lại.")

    # B0. Không phải câu hỏi (chửi bới, chào hỏi, cảm ơn, gõ bậy...): trả lời ngắn ngay.
    # Chạy TRƯỚC bước viết lại: LLM có thể "sửa" một câu chửi thành câu hỏi về tài liệu.
    # Không lưu vào lịch sử để không làm nhiễu các câu hỏi sau.
    kind = intent.classify(question)
    if kind is not None:
        return {
            "answer": intent.reply(kind, index.title),
            "found": False,
            "citations": [],
            "history_answer": None,
            "debug": {
                "search_query": question, "route": "chitchat", "intent": kind, "refusal_kind": "chitchat",
                "mode": opts.mode,
                "best_score": 0.0, "gate": 0.0, "rejected_reason": None, "timings_ms": {}, "retrieved": [],
            },
        }

    timings: dict[str, int] = {}
    t = time.perf_counter()

    def lap(name: str) -> None:
        nonlocal t
        now = time.perf_counter()
        timings[name] = round((now - t) * 1000)  # mili giây
        t = now

    key = f"{doc_id}:{session_id}"
    use_memory = history is None
    if use_memory:
        history = memory.get_history(key, opts.history_turns)
    else:
        history = history[-opts.history_turns * 2 :] if opts.history_turns > 0 else []

    steps: dict[str, str] = {}  # bước nào đã chạy / bỏ qua và vì sao (hiện trong "Chi tiết")

    # B1. Viết lại câu hỏi tiếp nối (gọi LLM, 3-7 giây) — chế độ "smart": chỉ khi câu hỏi phụ thuộc hội thoại
    search_query = question
    if not history:
        steps["rewrite"] = "không có lịch sử"
    elif opts.rewrite == "always" or (opts.rewrite == "smart" and followup.needs_rewrite(question)):
        search_query = _rewrite_question(history, question)
        steps["rewrite"] = "đã viết lại"
    else:
        steps["rewrite"] = "bỏ qua (câu hỏi đã đủ nghĩa)" if opts.rewrite == "smart" else "tắt"
    lap("rewrite")

    # Câu hỏi vị trí: bỏ cụm "ở trang nào" khi tìm kiếm để không làm nhiễu điểm
    # (câu hỏi cấu trúc như "Tài liệu có những mục nào?" thuộc luồng tổng quan, không phải hỏi vị trí)
    is_location_q = bool(LOCATION_RE.search(search_query)) and not OVERVIEW_QUESTION_RE.search(search_query)
    retrieval_query = (LOCATION_RE.sub(" ", search_query).strip() or search_query) if is_location_q else search_query

    # B2. Tìm kiếm
    q_vec, candidates, vector_hits, keyword_hits = _retrieve(index, retrieval_query, opts)
    lap("retrieve")

    # B3. Chấm lại (rerank, CPU ~1s mỗi đoạn) + chọn ngưỡng từ chối. Ba trường hợp:
    #   a) câu hỏi vị trí mà kết quả đã rõ ràng -> lấy luôn đoạn đó, bỏ qua rerank
    #      (câu hỏi vị trí không gọi LLM sinh câu trả lời, chỉ chỉ ra mục + trang)
    #   b) chế độ có rerank -> rerank, so với ngưỡng rerank
    #   c) chế độ không rerank -> dùng điểm cosine, so với ngưỡng vector
    winner, why_not = None, ""
    if is_location_q and opts.skip_rerank_when_clear and opts.use_bm25:
        winner, why_not = _clear_winner(vector_hits, keyword_hits)
    if winner is not None:
        top = [(winner, float(index.embeddings[winner] @ q_vec))]
        gate = hard_gate = 0.0  # sự đồng thuận của 2 cách tìm đã là bằng chứng, không cần ngưỡng điểm
        best_score = top[0][1]
        steps["rerank"] = "bỏ qua (câu hỏi vị trí, vector và từ khóa cùng chọn 1 đoạn)"
    elif opts.use_rerank:
        from .reranker import rerank

        top = rerank(retrieval_query, [(i, index.chunks[i].text_for_search()) for i, _ in candidates])
        top = top[: opts.top_k_context]
        gate, hard_gate = opts.min_rerank_score, opts.hard_rerank_score
        best_score = top[0][1] if top else 0.0
        steps["rerank"] = f"đã chấm {len(candidates)} đoạn" + (f" (không bỏ qua được: {why_not})" if why_not else "")
    else:
        # Dùng điểm cosine (tính cho cả đoạn chỉ BM25 tìm được) để so với ngưỡng vector
        top = [(i, float(index.embeddings[i] @ q_vec)) for i, _ in candidates[: opts.top_k_context]]
        gate, hard_gate = opts.min_vector_score, opts.hard_vector_score
        best_score = vector_hits[0][1] if vector_hits else 0.0
        steps["rerank"] = "tắt"
    lap("rerank")

    # Định tuyến câu hỏi tổng quan: không đoạn nào đủ điểm nhưng câu hỏi hỏi về cả tài liệu
    route = "retrieval"
    overview_pos = _overview_position(index)
    is_overview_q = overview_pos is not None and OVERVIEW_QUESTION_RE.search(search_query)
    # Hỏi cả tài liệu khi không đoạn nào đủ điểm, HOẶC hỏi cấu trúc một chương ("Chương 3 gồm những mục nào?")
    if is_overview_q and (best_score < gate or CHAPTER_NO_RE.search(search_query)):
        route = "overview"
        top = [(overview_pos, best_score)]

    # B4. Ghép ngữ cảnh (giữ thứ tự xuất hiện trong văn bản), thêm đoạn kề cùng mục cho đủ ý
    context_pos = _expand_context(index, top) if route == "retrieval" else sorted(i for i, _ in top)
    context_chunks = [index.chunks[i] for i in context_pos]
    # Độ tin cậy của bước tìm kiếm: "high" = vượt ngưỡng tin cậy; "medium" = chỉ vượt ngưỡng cứng
    # (vẫn cho model đọc, nhưng nhắc model chặt hơn và giao diện khuyên người dùng mở nguồn kiểm tra)
    confidence = "high" if best_score >= gate else "medium"

    debug = {
        "search_query": search_query,
        "mode": opts.mode,
        "steps": steps,
        "route": route,
        "best_score": round(best_score, 4),
        "gate": gate,
        "hard_gate": hard_gate,
        "confidence": confidence,
        "rejected_reason": None,
        "timings_ms": timings,
        "retrieved": [
            {
                "chunk_id": index.chunks[i].id,
                "page_start": index.chunks[i].page_start,
                "page_end": index.chunks[i].page_end,
                "header": index.chunks[i].header,
                "score": round(s, 4),
            }
            for i, s in top
        ],
        # Những đoạn THỰC SỰ đưa cho model (gồm cả đoạn kề được thêm vào)
        "context": [
            {"chunk_id": c.id, "page_start": c.page_start, "page_end": c.page_end} for c in context_chunks
        ],
    }

    def finish(answer: str, found: bool, citations: list[dict], history_answer: str | None = None) -> dict:
        # Lịch sử chỉ lưu bản ngắn: câu từ chối/dàn ý dài làm rối bước viết lại câu hỏi tiếp theo
        short = history_answer or answer
        if use_memory:
            memory.add_turn(key, question, short)
        return {"answer": answer, "found": found, "citations": citations, "debug": debug, "history_answer": short}

    figure = None  # hình/bảng câu hỏi nhắc tới (gán bên dưới)

    def refuse(reason: str) -> dict:
        debug["rejected_reason"] = reason
        headers = []
        for i, _ in top[:3]:
            c = index.chunks[i]
            h = c.header.split(" > ")[-1]
            if c.id != OVERVIEW_ID and h != index.title and (h, c.page_start) not in headers:
                headers.append((h, c.page_start))
        if reason == "low_retrieval_score" or (reason == "model_not_found" and not headers):
            debug["refusal_kind"] = "not_in_doc"      # thật sự không có trong tài liệu
            short = REFUSAL
        elif reason == "model_not_found":
            debug["refusal_kind"] = "unsure"          # tìm được mục liên quan nhưng model không trả lời
            short = "Không rút ra được câu trả lời chắc chắn."
        else:
            debug["refusal_kind"] = "unverified"      # trả lời được nhưng trích dẫn không khớp
            short = UNVERIFIED
        if figure is not None and reason != "low_retrieval_score":
            # Câu hỏi về nội dung bên trong hình: không đoán, chỉ đường tới hình gốc
            debug["refusal_kind"] = "figure"
            cit = _figure_citation(index, figure["line"], figure["pos"])
            _attach_locations(index, [cit])
            text = (
                f"Nội dung bạn hỏi có vẻ nằm trong {figure['label']} – {figure['title']} (trang {cit['page']}). "
                "Hệ thống chỉ đọc được phần chữ của tài liệu, không đọc được nội dung bên trong hình, "
                "nên không trả lời để tránh sai.\n\nBấm vào nguồn bên dưới để xem hình gốc."
            )
            return finish(text, False, [cit], history_answer=short)
        return finish(_refusal_text(index, reason, headers), False, [], history_answer=short)

    # Hình / bảng: hỏi "cho tôi sơ đồ ...", "Hình 2.5 ở đâu" -> mở đúng hình, không cần LLM
    figure = _match_figure(index, retrieval_query, top) if route == "retrieval" else None
    if figure is not None:
        debug["figure"] = figure["label"]
    if figure is not None and (SHOW_RE.search(search_query) or FIGURE_LABEL_RE.search(search_query)):
        debug["route"] = "figure"
        cits = [_figure_citation(index, figure["line"], figure["pos"])]
        page_hint = index.chunks[figure["pos"]].page_start
        answer = f"Đây là {figure['label']} – {figure['title']}."
        desc = _figure_description(index, figure)
        if desc is not None:
            answer += f"\n\nTài liệu mô tả: “{desc[0]}”"
            cits.append(_figure_citation(index, desc[0], desc[1]))
        answer += "\n\nBấm vào nguồn bên dưới để xem hình gốc trong tài liệu."
        _attach_locations(index, cits)
        page_hint = cits[0]["page"]
        lap("locate")
        return finish(answer, True, cits, history_answer=f"{figure['label']} {figure['title']} (trang {page_hint})")

    # Câu hỏi vị trí ("ở trang nào"): trả lời bằng vị trí đoạn tìm được, không cần LLM
    if route == "retrieval" and is_location_q and best_score >= gate:
        built = _location_answer(index, top, gate)
        if built is not None:
            debug["route"] = "location"
            answer, citations = built
            _attach_locations(index, citations)
            lap("locate")
            return finish(answer, True, citations, history_answer=answer.split("\n\n")[0])

    # Câu hỏi tổng quan: trả lời bằng dàn ý nguyên văn, không cần LLM (nhanh, đầy đủ, kiểm chứng được)
    if route == "overview":
        built = _overview_answer(index, search_query)
        if built is not None:
            answer, titles = built
            ov = index.chunks[overview_pos]
            citations = [
                {"quote": t, "chunk_id": OVERVIEW_ID, "page": ov.page_start, "page_start": ov.page_start,
                 "page_end": ov.page_end, "section": ov.header, "rects": []}
                for t in titles
            ]
            _attach_locations(index, citations)
            lap("locate")
            short = "Tài liệu gồm: " + "; ".join(_pretty(t) for t in titles[:OUTLINE_MAX_ITEMS])
            return finish(answer, True, citations, history_answer=short)

    # Lớp 1: chặn trước khi gọi LLM — chỉ chặn khi đoạn tốt nhất gần như không liên quan (ngưỡng cứng).
    # Câu hỏi bằng lời lẽ đời thường thường có điểm rerank thấp dù đã tìm đúng đoạn, nên vùng giữa
    # ngưỡng cứng và ngưỡng tin cậy vẫn cho model đọc; lớp 2 (model) và lớp 3 (kiểm chứng trích dẫn) chặn tiếp.
    if route == "retrieval" and best_score < hard_gate:
        return refuse("low_retrieval_score")

    # B5. Sinh câu trả lời
    messages = (
        [{"role": "system", "content": prompts.SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": prompts.build_user_message(
            context_chunks, question, search_query, weak=confidence != "high")}]
    )
    result = llm.chat_json(messages, prompts.ANSWER_SCHEMA)
    lap("llm")

    if result is None:
        return refuse("invalid_json")
    if not result.get("found"):
        return refuse("model_not_found")

    # B6. Kiểm chứng trích dẫn
    debug["raw_quotes"] = result.get("quotes", [])  # giữ lại để chẩn đoán khi kiểm chứng thất bại
    citations, dropped = verify.verify_quotes_partial(result.get("quotes", []), context_chunks)
    lap("verify")
    if citations is None:
        return refuse("quote_not_verified")
    if dropped:
        debug["dropped_quotes"] = dropped  # câu trích chép lệch đã bị bỏ, câu trả lời vẫn giữ

    # Câu hỏi có nhắc hình/bảng: thêm chú thích hình làm nguồn để mở xem hình gốc
    if figure is not None and not any(c["quote"] == figure["line"] for c in citations):
        citations.append(_figure_citation(index, figure["line"], figure["pos"]))

    # B7. Tìm vị trí trích dẫn trên trang PDF gốc để tô màu
    _attach_locations(index, citations)
    lap("locate")

    answer = (result.get("answer") or "").strip()
    if not answer:
        return refuse("model_not_found")
    example = (result.get("example") or "").strip()
    if example:
        debug["example"] = example  # lưu trong debug để mở lại lịch sử vẫn thấy
    out = finish(answer, True, citations)
    out["example"] = example or None
    return out

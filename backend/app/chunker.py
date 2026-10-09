import re
from dataclasses import dataclass

# Khớp: "CHƯƠNG 1. TỔNG QUAN", "Chương II: Quy định", "Mục 1. Phạm vi", "CHƯƠNG 3" (đứng một mình)
# Không khớp câu văn: "Chương 1 sẽ trình bày...", "xem mục 3.2 để..." (sau số không phải chữ in hoa)
CHAPTER_RE = re.compile(r"^(chương|phần|mục)\s+([ivxlcdm]+|\d+)\s*([.:–-]\s*)?", re.IGNORECASE)
# Cấp "phần" bọc ngoài chương: "Phần I", "PHẦN 2" (chỉ khi ĐỨNG MỘT MÌNH hoặc theo sau là tên viết hoa),
# và phần cuối sách chứa các mục con theo chương: phụ lục, đáp án...
PART_RE = re.compile(r"^(PHỤ LỤC|ĐÁP ÁN|APPENDIX)\b")
PART_NO_RE = re.compile(r"^(phần|part)\s+([ivxlcdm]+|\d+)\s*([.:–-]\s*)?", re.IGNORECASE)
# Mục số La Mã trong chương: "I- Triết học là gì ?", "III. Ý nghĩa phương pháp luận..."
# (khoảng trắng sau dấu là bắt buộc, để không nhầm với tên viết tắt như "V.I.Lênin")
ROMAN_RE = re.compile(r"^([IVX]{1,4})\s*[-.–]\s+\S")
# Phần câu hỏi / bài tập cuối chương: các dòng "1. Phân tích...?" trong đó KHÔNG phải tiêu đề mục
REVIEW_RE = re.compile(r"^(câu hỏi ôn tập|câu hỏi và bài tập|câu hỏi thảo luận|bài tập|câu hỏi)\s*:?$", re.IGNORECASE)
# Phần đầu sách: coi như một chương riêng
FRONT_RE = re.compile(r"^(LỜI NÓI ĐẦU|LỜI MỞ ĐẦU|LỜI GIỚI THIỆU|PREFACE)\s*$")
ARTICLE_RE = re.compile(r"^điều\s+\d+", re.IGNORECASE)
NUMBERED_RE = re.compile(r"^\d{1,2}(\.\d{1,2})*\.?\s+[A-ZÀ-Ỹ](?:[^.]|\.\.\.){2,70}$")


@dataclass
class Chunk:
    id: str
    text: str        # nội dung gốc: dùng để hiển thị và kiểm chứng trích dẫn
    header: str      # tiêu đề ngữ cảnh: "Tên file > Chương II > Điều 5. ..."
    page_start: int
    page_end: int

    def text_for_search(self) -> str:
        """Văn bản đưa vào embedding/BM25/reranker: có thêm tiêu đề ngữ cảnh.

        Bỏ tên tài liệu ở đầu header: mọi đoạn đều giống nhau nên không giúp phân biệt,
        lại chiếm chỗ trong giới hạn token của reranker.
        """
        parts = self.header.split(" > ")
        head = " > ".join(parts[1:]) if len(parts) > 1 else self.header
        return f"[{head}]\n{self.text}"


def _is_chapter_heading(line: str) -> bool:
    """Phần còn lại sau "Chương 1." phải trống hoặc bắt đầu bằng chữ IN HOA.

    Dùng str.isupper() thay vì [A-ZÀ-Ỹ] trong regex, vì khoảng À-Ỹ của Unicode
    chứa cả chữ thường có dấu (đ, ư, ơ...).
    """
    m = CHAPTER_RE.match(line)
    if not m:
        return False
    rest = line[m.end():]
    return rest == "" or rest[0].isupper()


def _is_part_heading(line: str) -> bool:
    if PART_RE.match(line):
        return True
    m = PART_NO_RE.match(line)
    if not m:
        return False
    rest = line[m.end():]
    return rest == "" or rest[0].isupper()


def _is_roman_heading(line: str) -> bool:
    """'I- Triết học là gì ?', 'II- triết học trung hoa...' (sách hay viết thường sau số) -> True."""
    return bool(ROMAN_RE.match(line)) and len(line) <= 150 and not line.endswith((".", ";", ","))


def _is_bare(line: str, pattern: re.Pattern) -> bool:
    """'Chương I', 'Phần II' đứng một mình (tên chương nằm ở dòng sau)."""
    m = pattern.match(line)
    return bool(m) and line[m.end():].strip() == ""


def _is_numbered_heading(line: str) -> bool:
    """'1.1 Giới thiệu...', '3.2 Mạng neural (CNN)' -> True; dòng liệt kê kết thúc bằng '.' -> False."""
    if not (NUMBERED_RE.match(line) and (line[-1].isalnum() or line.endswith(")"))):
        return False
    if "?" in line:  # câu hỏi ôn tập "1. Phạm trù là gì? Phân tích..." không phải tiêu đề
        return False
    title = line.split(maxsplit=1)[1]
    if not title[0].isupper():  # [A-ZÀ-Ỹ] trong regex vẫn lọt chữ thường có dấu như "đ"
        return False
    return len(title.split()) >= 2 or len(title) >= 6  # loại "3.14 Doa" (kết quả in ra của code)


def _split_section(lines: list[tuple[int, str]], max_words: int, overlap_words: int):
    """Cắt một mục dài thành nhiều phần ~max_words từ, chồng lấn ~overlap_words từ."""
    parts, current, count = [], [], 0
    for page, line in lines:
        words = len(line.split())
        if current and count + words > max_words:
            parts.append(current)
            # Giữ lại vài dòng cuối của phần vừa cắt làm phần chồng lấn
            carry, carry_count = [], 0
            for item in reversed(current):
                w = len(item[1].split())
                if carry_count + w > overlap_words:
                    break
                carry.insert(0, item)
                carry_count += w
            current, count = carry, carry_count
        current.append((page, line))
        count += words
    if current:
        parts.append(current)
    return parts


def chunk_document(
    lines: list[tuple[int, str]], doc_title: str, max_words: int, overlap_words: int
) -> list[Chunk]:
    # Bước 1: gom các dòng thành "mục" theo tiêu đề. Các cấp (cấp nào sách không có thì để trống):
    #   phần ("Phần I") > chương ("Chương 1", "CHƯƠNG II") > mục La Mã ("I- ...") > mục đánh số / Điều
    sections: list[tuple[str, str, list[tuple[int, str]]]] = []
    part, chapter, roman, article = "", "", "", ""
    current: list[tuple[int, str]] = []
    pending = ""        # "chapter" | "part": tiêu đề vừa gặp mà tên còn nằm ở dòng sau
    in_review = False   # đang ở phần câu hỏi ôn tập cuối chương

    for page, line in lines:
        # Tên chương / phần nằm ở dòng sau: "Chương I" + "Khái lược về Triết học",
        # hoặc tiêu đề viết hoa bị xuống dòng: "CHƯƠNG 1. TỔNG QUAN NGÀNH" + "HỆ THỐNG THÔNG TIN QUẢN LÝ"
        if pending and len(line) < 100 and not (
            _is_chapter_heading(line) or _is_part_heading(line) or _is_roman_heading(line)
            or _is_numbered_heading(line) or ARTICLE_RE.match(line)
        ):
            title = part if pending == "part" else chapter
            bare = _is_bare(title, PART_NO_RE if pending == "part" else CHAPTER_RE)
            # tên bị ngắt dòng: "...của phép biện chứng duy" + "vật" (dòng ngắn, viết thường)
            wrapped = len(line.split()) <= 3 and line[:1].islower()
            if bare or wrapped or (line.isupper() and len(title) + len(line) < 100):
                merged = f"{title}. {line}" if bare else f"{title} {line}"
                if pending == "part":
                    part = merged
                else:
                    chapter = merged
                current.append((page, line))
                if not bare:  # sau khi ghép tên vào "Chương I" vẫn chờ thêm 1 dòng, phòng tên bị ngắt dòng
                    pending = ""
                continue
        pending = ""

        is_part = _is_part_heading(line)
        is_chapter = not is_part and (_is_chapter_heading(line) or bool(FRONT_RE.match(line)))
        is_roman = not (is_part or is_chapter) and _is_roman_heading(line)
        is_review = bool(REVIEW_RE.match(line))
        is_article = not (is_part or is_chapter or is_roman) and (
            is_review or (not in_review and (bool(ARTICLE_RE.match(line)) or _is_numbered_heading(line)))
        )
        if (is_part or is_chapter or is_roman or is_article) and current:
            sections.append((" > ".join(x for x in (part, chapter, roman) if x), article, current))
            current = []
        if is_part:
            part, chapter, roman, article = line[:100], "", "", ""
            pending = "part"
        elif is_chapter:
            chapter, roman, article = line[:100], "", ""
            pending = "chapter"
        elif is_roman:
            roman, article = line[:150], ""
        elif is_article:
            article = line[:120]
        if is_part or is_chapter or is_roman:
            in_review = False
        elif is_review:
            in_review = True
        current.append((page, line))
    if current:
        sections.append((" > ".join(x for x in (part, chapter, roman) if x), article, current))

    # Bước 2: mục nào dài thì cắt nhỏ tiếp, rồi tạo Chunk
    chunks: list[Chunk] = []
    for chap, art, sec_lines in sections:
        header = " > ".join(x for x in (doc_title, chap, art) if x)
        for part in _split_section(sec_lines, max_words, overlap_words):
            chunks.append(
                Chunk(
                    id=f"c{len(chunks)}",
                    text="\n".join(line for _, line in part),
                    header=header,
                    page_start=part[0][0],
                    page_end=part[-1][0],
                )
            )
    return chunks

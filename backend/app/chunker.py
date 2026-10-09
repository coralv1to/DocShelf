import re
from dataclasses import dataclass

# Khớp: "CHƯƠNG 1. TỔNG QUAN", "Chương II: Quy định", "Mục 1. Phạm vi", "CHƯƠNG 3" (đứng một mình)
# Không khớp câu văn: "Chương 1 sẽ trình bày...", "xem mục 3.2 để..." (sau số không phải chữ in hoa)
CHAPTER_RE = re.compile(r"^(chương|phần|mục)\s+([ivxlcdm]+|\d+)\s*([.:–-]\s*)?", re.IGNORECASE)
# Phần cuối sách chứa các mục con theo chương: phụ lục, đáp án... -> làm cấp "phần" bọc ngoài chương
PART_RE = re.compile(r"^(PHỤ LỤC|ĐÁP ÁN|APPENDIX)\b")
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
        """Văn bản đưa vào embedding/BM25/reranker: có thêm tiêu đề ngữ cảnh."""
        return f"[{self.header}]\n{self.text}"


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


def _is_numbered_heading(line: str) -> bool:
    """'1.1 Giới thiệu...', '3.2 Mạng neural (CNN)' -> True; dòng liệt kê kết thúc bằng '.' -> False."""
    if not (NUMBERED_RE.match(line) and (line[-1].isalnum() or line.endswith(")"))):
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
    # Bước 1: gom các dòng thành "mục" theo tiêu đề Chương / Điều / mục đánh số
    sections: list[tuple[str, str, list[tuple[int, str]]]] = []
    part, chapter, article = "", "", ""
    current: list[tuple[int, str]] = []
    prev_was_chapter = False

    for page, line in lines:
        # Tiêu đề chương bị xuống dòng: "CHƯƠNG 1. TỔNG QUAN NGÀNH" + "HỆ THỐNG THÔNG TIN QUẢN LÝ"
        if prev_was_chapter and line.isupper() and len(chapter) + len(line) < 100:
            chapter = f"{chapter} {line}"
            current.append((page, line))
            continue
        is_part = bool(PART_RE.match(line))
        is_chapter = _is_chapter_heading(line) or bool(FRONT_RE.match(line))
        is_article = bool(ARTICLE_RE.match(line)) or _is_numbered_heading(line)
        if (is_part or is_chapter or is_article) and current:
            sections.append((" > ".join(x for x in (part, chapter) if x), article, current))
            current = []
        if is_part:
            part, chapter, article = line[:100], "", ""
        elif is_chapter:
            chapter, article = line[:100], ""
        elif is_article:
            article = line[:120]
        prev_was_chapter = is_chapter
        current.append((page, line))
    if current:
        sections.append((" > ".join(x for x in (part, chapter) if x), article, current))

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

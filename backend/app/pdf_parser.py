import re
from collections import Counter

import pymupdf

GAP_RATIO = 0.15  # khoảng hở > 15% cỡ chữ thì coi là dấu cách

PAGE_NUMBER_RE = re.compile(r"^\s*(trang\s*)?\d+(\s*/\s*\d+)?\s*$", re.IGNORECASE)
STOP_RE = re.compile(r"^(references|tài liệu tham khảo|bibliography)$", re.IGNORECASE)
DOT_LEADER_RE = re.compile(r"(\.\s?){5,}")          # ". . . . ." trong mục lục
SECTION_NO_RE = re.compile(r"^\d{1,2}(\.\d{1,2})+\.?$")  # dòng chỉ có "1.1", "2.3.1"
BULLET_RE = re.compile(r"^[Ì•▪►■◦]\s*")            # ký hiệu đầu dòng


def _page_lines(page) -> list[str]:
    """Dựng lại từng dòng từ vị trí từng ký tự, tự chèn dấu cách khi có khoảng hở."""
    lines = []
    data = page.get_text("rawdict")
    for block in data["blocks"]:
        for line in block.get("lines", []):
            parts: list[str] = []
            prev_x1 = None
            for span in line["spans"]:
                gap = span["size"] * GAP_RATIO
                for ch in span["chars"]:
                    c = ch["c"]
                    x0, _, x1, _ = ch["bbox"]
                    if (
                        prev_x1 is not None
                        and c != " "
                        and parts
                        and parts[-1] != " "
                        and x0 - prev_x1 > gap
                    ):
                        parts.append(" ")
                    parts.append(c)
                    prev_x1 = x1
            text = "".join(parts).strip()
            if text:
                lines.append(text)
    return lines


def _extract_pages(pdf_path: str) -> list[list[str]]:
    with pymupdf.open(pdf_path) as doc:
        return [_page_lines(page) for page in doc]


def _is_toc_page(lines: list[str]) -> bool:
    """Trang có từ 5 dòng ". . . . ." trở lên -> trang mục lục."""
    return sum(1 for l in lines if DOT_LEADER_RE.search(l)) >= 5


def _remove_repeated_lines(pages_lines: list[list[str]]) -> list[list[str]]:
    """Bỏ các dòng xuất hiện ở >= 60% số trang (thường là header/footer)."""
    n = len(pages_lines)
    if n < 3:
        return pages_lines
    counter: Counter[str] = Counter()
    for lines in pages_lines:
        counter.update(set(lines))
    repeated = {line for line, count in counter.items() if count >= n * 0.6}
    return [[l for l in lines if l not in repeated] for lines in pages_lines]


def _join_hyphenated(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Nối dòng kết thúc bằng gạch nối với dòng sau: 'ac­' + 'curacy' -> 'accuracy'."""
    out: list[tuple[int, str]] = []
    for page, line in lines:
        if out and out[-1][1].endswith(("­", "-")):
            prev_page, prev = out[-1]
            out[-1] = (prev_page, prev.rstrip("­") + line)
        else:
            out.append((page, line))
    return out


def _join_section_numbers(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Gộp dòng chỉ có số mục với dòng tiêu đề ngay sau: '1.1' + 'Giới thiệu' -> '1.1 Giới thiệu'."""
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        page, line = lines[i]
        if SECTION_NO_RE.match(line) and i + 1 < len(lines):
            out.append((page, f"{line} {lines[i + 1][1]}"))
            i += 2
        else:
            out.append((page, line))
            i += 1
    return out


def _finalize(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    return _join_section_numbers(_join_hyphenated(lines))


def parse_pdf(pdf_path: str) -> list[tuple[int, str]]:
    """Trả về danh sách (số_trang, dòng_text) đã làm sạch, theo thứ tự trong file."""
    pages = _extract_pages(pdf_path)
    pages = [[] if _is_toc_page(lines) else lines for lines in pages]
    pages = _remove_repeated_lines(pages)

    result: list[tuple[int, str]] = []
    for page_no, lines in enumerate(pages, start=1):
        for line in lines:
            line = BULLET_RE.sub("", line.strip())
            if not line or PAGE_NUMBER_RE.match(line):
                continue
            if STOP_RE.match(line):  # gặp tiêu đề "References" -> dừng
                return _finalize(result)
            result.append((page_no, line))
    return _finalize(result)
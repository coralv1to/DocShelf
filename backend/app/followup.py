"""Câu hỏi này có cần đọc lịch sử hội thoại mới hiểu được không?

Viết lại câu hỏi bằng LLM tốn 3-7 giây. Phần lớn câu hỏi đã đủ nghĩa ("append ở trang nào",
"Dropout là gì?"), viết lại chỉ tốn thời gian và đôi khi còn làm sai ý (vd "trang nào" thành "chương nào").

Quy tắc (không gọi LLM, < 1ms): chỉ viết lại khi câu hỏi
  1. có đại từ / từ chỉ định trỏ về điều đã nói: "nó", "cái đó", "phương thức đó", "như vậy"...
  2. hoặc mở đầu kiểu nối tiếp: "Còn ...", "Vậy ...", "Thế còn ...", "Giải thích thêm"...
  3. hoặc không có từ nội dung nào: "Bằng cách nào?", "Tại sao?", "Ví dụ?"

Nguyên tắc: thà viết lại thừa (tốn vài giây) còn hơn bỏ sót một câu hỏi nối tiếp (tìm sai đoạn).
Câu nối tiếp ngầm không có dấu hiệu nào (vd "Xác suất giữ lại là bao nhiêu?" sau khi hỏi về dropout)
sẽ bị bỏ sót; khi đó bước sinh câu trả lời vẫn nhận lịch sử hội thoại nên thường vẫn hiểu đúng.
Cần chắc chắn hơn thì dùng chế độ "Kỹ" (luôn viết lại).
"""
import re
import unicodedata

# 1. Đại từ / từ chỉ định trỏ về điều đã nói
_REFERENCE_RE = re.compile(
    r"\b("
    r"nó|chúng nó|chúng|họ"
    r"|(cái|điều|việc|vấn đề|phương thức|phương pháp|cách|hàm|lệnh|thuật toán|khái niệm|mục|phần|bước|công thức"
    r"|tham số|giá trị|ví dụ|trường hợp|loại|kiểu|người|tác giả)\s+(đó|ấy|này|kia|trên)"
    r"|như (vậy|thế)(?! nào)|thế này|vậy thì|thì sao|ra sao vậy"
    r"|ở trên|nói trên|kể trên|vừa (rồi|nói|nêu)|trước đó"
    r"|đó|ấy"
    r"|it|its|this|that|they|them|those|these"
    r")\b",
    re.IGNORECASE,
)

# 2. Mở đầu kiểu nối tiếp, hoặc câu hỏi thiếu chủ ngữ: "Khi nào thì dừng?", "Tại sao lại thế?"
_CONTINUE_RE = re.compile(
    r"^\s*(còn|vậy|thế còn|thế|tiếp|tiếp theo|giải thích thêm|nói thêm|chi tiết hơn|cụ thể hơn|ví dụ"
    r"|(khi nào|lúc nào|bao giờ|tại sao|vì sao|làm sao|làm thế nào|bao nhiêu) (thì|lại)"
    r"|and|what about|how about|why)\b",
    re.IGNORECASE,
)

# 3. Từ không mang nội dung (hỏi, nối, trợ từ). Câu chỉ gồm những từ này thì chắc chắn là câu nối tiếp.
_FUNCTION_WORDS = set(
    """
    bằng cách nào sao vì tại thế như là gì của về có không được những các một và thì mà để cho với khi
    đâu ra bao nhiêu ai hả vậy chứ nhỉ nhé ạ à ơi hãy giúp tôi mình em bạn làm nữa thêm lại rồi đã sẽ đang
    trong ngoài trên dưới giữa từ đến theo do bởi nên phải cần muốn biết hỏi xin hơn nhất rất quá lắm
    tại_sao như_thế_nào bằng_cách_nào khi_nào ở đâu
    how why what when where which who is are do does can could the a an of to in on for
    """.split()
)

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def needs_rewrite(question: str) -> bool:
    q = unicodedata.normalize("NFC", question).strip()
    if _CONTINUE_RE.search(q) or _REFERENCE_RE.search(q):
        return True
    content = [w for w in _WORD_RE.findall(q.lower()) if w not in _FUNCTION_WORDS]
    return len(content) == 0

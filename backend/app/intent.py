"""Phân loại ý định câu nhắn TRƯỚC khi chạy RAG.

Không phải câu nào người dùng gõ cũng là câu hỏi về tài liệu: chào hỏi, cảm ơn, chửi bới, gõ bậy...
Những câu này phải được trả lời ngay bằng một câu ngắn, KHÔNG đi qua viết lại câu hỏi
(LLM có thể "sửa" câu chửi thành câu hỏi về tài liệu), không tìm kiếm, không lưu vào lịch sử.

Dùng quy tắc (regex) thay vì gọi LLM: nhanh (<1ms), tất định, dễ kiểm tra.
Nguyên tắc: thà bỏ lọt (câu đi tiếp vào RAG và bị từ chối như bình thường)
còn hơn chặn nhầm một câu hỏi thật.
"""
import re
import unicodedata

# Từ ngữ xúc phạm / tục tĩu (tiếng Việt có dấu, không dấu, viết tắt; tiếng Anh). So khớp nguyên từ.
_ABUSE_WORDS = [
    # tiếng Anh
    r"f+u+c*k+\w*", r"fk", r"fck", r"fuk", r"wtf", r"stfu", r"shut\s+up", r"bitch\w*", r"asshole",
    r"ass", r"dick", r"idiot", r"stupid", r"moron", r"bullshit", r"shit", r"dumb",
    # tiếng Việt
    r"đm", r"đmm", r"dmm", r"đcm", r"dcm", r"vcl", r"vkl", r"vl", r"vãi\s*l\w*", r"clm",
    r"đéo", r"đếch", r"địt\w*", r"dit\s*me", r"đĩ", r"cút", r"câm\s+(mồm|miệng|họng)", r"im\s+mồm",
    r"ngu", r"ngu\s+(như|vãi|thế|vậy)", r"óc\s+chó", r"oc\s+cho", r"chó\s+má", r"đồ\s+chó",
    r"mẹ\s+mày", r"me\s+may", r"bố\s+mày", r"thằng\s+ngu", r"con\s+điên", r"khốn\s+nạn",
]
ABUSE_RE = re.compile(r"(?<!\w)(" + "|".join(_ABUSE_WORDS) + r")(?!\w)", re.IGNORECASE)

# Cả câu chỉ là lời chào / cảm ơn / tạm biệt / xác nhận (không kèm câu hỏi nào khác)
GREETING_RE = re.compile(
    r"^(xin\s+chào|chào(\s+(bạn|bot|em|anh|chị|cậu))?|hi+|hello|hey|alo+|good\s+(morning|afternoon|evening))"
    r"(\s+(bạn|bot|em|anh|chị|cậu))?[\s!.,~]*$",
    re.IGNORECASE,
)
THANKS_RE = re.compile(
    r"^(cảm\s+ơn|cám\s+ơn|cảm\s+ơn\s+nhiều|thanks?|thank\s+you|thx|tks|ok(e|ay)?|oke|okela|được\s+rồi|"
    r"hiểu\s+rồi|tuyệt|hay\s+quá|good|great|nice)(\s+(bạn|bot|em|nhé|nha|nhiều|lắm|you))*[\s!.,~]*$",
    re.IGNORECASE,
)
BYE_RE = re.compile(r"^(tạm\s+biệt|bye+|goodbye|hẹn\s+gặp\s+lại|see\s+you)(\s+\w+)?[\s!.,~]*$", re.IGNORECASE)
HELP_RE = re.compile(
    r"^(bạn\s+là\s+(ai|gì)|bạn\s+(làm|giúp)\s+được\s+(gì|những\s+gì)|bạn\s+có\s+thể\s+làm\s+gì|"
    r"hướng\s+dẫn(\s+sử\s+dụng)?|help|trợ\s+giúp|cách\s+dùng)[\s?!.]*$",
    re.IGNORECASE,
)


def classify(text: str) -> str | None:
    """Trả về 'abuse' | 'greeting' | 'thanks' | 'bye' | 'help' | 'gibberish', hoặc None nếu là câu hỏi bình thường."""
    q = unicodedata.normalize("NFC", text).strip()
    if ABUSE_RE.search(q):
        return "abuse"
    if GREETING_RE.match(q):
        return "greeting"
    if THANKS_RE.match(q):
        return "thanks"
    if BYE_RE.match(q):
        return "bye"
    if HELP_RE.match(q):
        return "help"
    letters = re.findall(r"[^\W\d_]", q)
    if len(letters) < 2:  # "?", "...", "1", "a"
        return "gibberish"
    return None


def reply(kind: str, title: str) -> str:
    """Câu trả lời ngắn, lịch sự cho từng loại. Không giảng giải, luôn hướng về tài liệu."""
    example = "“Tài liệu này nói về chủ đề gì?”"
    if kind == "abuse":
        return f"Mình chỉ hỗ trợ hỏi đáp về nội dung tài liệu “{title}”. Bạn muốn tìm hiểu phần nào trong tài liệu?"
    if kind == "greeting":
        return f"Chào bạn! Mình trả lời câu hỏi dựa trên tài liệu “{title}”. Bạn có thể bắt đầu bằng câu {example}"
    if kind == "thanks":
        return "Không có gì! Bạn cần tìm thêm gì trong tài liệu thì cứ hỏi nhé."
    if kind == "bye":
        return "Tạm biệt bạn! Khi cần tra cứu tài liệu thì quay lại hỏi nhé."
    if kind == "help":
        return (
            f"Mình là trợ lý hỏi đáp tài liệu. Mình chỉ trả lời dựa trên nội dung “{title}”, "
            "kèm trích dẫn nguyên văn và số trang để bạn đối chiếu. Nếu tài liệu không có thông tin, mình sẽ nói rõ.\n\n"
            f"Bạn có thể hỏi: {example}, “Chương 2 gồm những mục nào?”, "
            "hoặc hỏi trực tiếp một khái niệm, ví dụ “Thuật toán là gì?”."
        )
    return "Mình chưa hiểu câu hỏi. Bạn thử hỏi cụ thể hơn về nội dung tài liệu nhé."

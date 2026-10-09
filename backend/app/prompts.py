from .chunker import Chunk

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "answer": {"type": "string"},
        "quotes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["found", "answer", "quotes"],
}

SYSTEM_PROMPT = """Bạn là trợ lý hỏi đáp CHỈ dựa trên TÀI LIỆU được cung cấp.

Quy tắc bắt buộc:
1. Chỉ dùng thông tin có trong TÀI LIỆU. Tuyệt đối không dùng kiến thức bên ngoài, không suy đoán, không bổ sung.
2. LỊCH SỬ HỘI THOẠI chỉ dùng để hiểu người dùng đang hỏi về điều gì. Không lấy thông tin từ các câu trả lời trước.
3. Nếu TÀI LIỆU không chứa câu trả lời: đặt "found": false, "answer": "", "quotes": [].
4. Nếu có câu trả lời: đặt "found": true, trả lời ngắn gọn bằng tiếng Việt trong "answer",
   và đưa vào "quotes" từ 1 đến 3 câu trích NGUYÊN VĂN (chép chính xác từng chữ) từ TÀI LIỆU làm căn cứ.
5. Chỉ trả về JSON đúng định dạng yêu cầu."""


def build_context(chunks: list[Chunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        pages = f"Trang {c.page_start}" if c.page_start == c.page_end else f"Trang {c.page_start}-{c.page_end}"
        blocks.append(f"[Đoạn {i} | {pages} | {c.header}]\n{c.text}")
    return "\n\n".join(blocks)


def build_user_message(chunks: list[Chunk], question: str, search_query: str) -> str:
    q = question
    if search_query.strip() != question.strip():
        q += f"\n(Hiểu đầy đủ là: {search_query})"
    return f"TÀI LIỆU:\n<<<\n{build_context(chunks)}\n>>>\n\nCÂU HỎI: {q}"


REWRITE_PROMPT = """Dựa vào lịch sử hội thoại, viết lại CÂU MỚI thành một câu hỏi ĐẦY ĐỦ,
tự hiểu được mà không cần đọc lịch sử.
- Nếu câu mới đã đầy đủ hoặc chuyển sang chủ đề khác: giữ nguyên.
- Giữ nguyên ý hỏi và loại câu hỏi: hỏi "trang nào" thì vẫn hỏi "trang nào" (không đổi thành "chương nào"),
  hỏi "là gì" thì vẫn hỏi "là gì".
- Luôn giữ TÊN khái niệm/đối tượng đang được nói tới trong lịch sử (tên thuật toán, hàm, lệnh, khái niệm...)
  vào câu viết lại, kể cả khi câu mới rất ngắn.
- Chỉ dùng thông tin trong CÂU HỎI của lịch sử để bổ sung ngữ cảnh, không chép nội dung câu trả lời.
- Chỉ xuất ra đúng một câu hỏi, không giải thích, không trả lời.

Ví dụ:
Lịch sử:
Hỏi: Học phí ngành A là bao nhiêu?
Đáp: Học phí ngành A là 15 triệu đồng/học kỳ.
Câu mới: Còn ngành B thì sao?
Viết lại: Học phí ngành B là bao nhiêu?

Lịch sử:
Hỏi: Vòng lặp while là gì?
Đáp: Vòng lặp while lặp lại khối lệnh khi điều kiện còn đúng.
Câu mới: Khi nào thì dừng?
Viết lại: Khi nào thì vòng lặp while dừng?

Lịch sử:
{history}
Câu mới: {question}
Viết lại:"""
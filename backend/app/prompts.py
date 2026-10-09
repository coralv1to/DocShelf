from .chunker import Chunk

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "answer": {"type": "string"},
        "quotes": {"type": "array", "items": {"type": "string"}},
        # Ví dụ minh họa do model TỰ NGHĨ (không có trong sách). Giao diện hiện riêng, gắn nhãn rõ ràng.
        "example": {"type": "string"},
    },
    "required": ["found", "answer", "quotes", "example"],
}

SYSTEM_PROMPT = """Bạn là trợ lý học tập giúp sinh viên hiểu giáo trình. Bạn CHỈ trả lời dựa trên TÀI LIỆU được cung cấp.

Quy tắc bắt buộc:
1. Nội dung trong "answer" phải lấy từ TÀI LIỆU. Không dùng kiến thức bên ngoài, không thêm tên người, năm,
   số liệu hay khẳng định nào mà TÀI LIỆU không có.
2. LỊCH SỬ HỘI THOẠI chỉ dùng để hiểu người dùng đang hỏi về điều gì. Không lấy thông tin từ các câu trả lời trước.
3. Đặt "found": true khi TÀI LIỆU có nội dung trả lời được câu hỏi, kể cả khi:
   - câu hỏi dùng từ ngữ đời thường, khác với thuật ngữ trong sách;
   - câu hỏi có tiền đề SAI (vd "vật chất do cảm giác tạo ra đúng không?"): nói rõ là chưa đúng
     và sửa lại theo TÀI LIỆU;
   - câu hỏi nhờ giải thích dễ hiểu, so sánh, tóm tắt, hoặc áp dụng vào ví dụ: trả lời phần lý thuyết từ TÀI LIỆU.
4. Đặt "found": false, "answer": "", "quotes": [], "example": "" khi TÀI LIỆU không có nội dung liên quan
   đến điều được hỏi (vd hỏi lịch thi, hỏi một chủ đề sách không nói tới, hỏi một chi tiết sách không ghi).
   Không trả lời bằng đoạn chỉ "na ná" chủ đề.
5. Khi "found": true:
   - "answer": trả lời bằng tiếng Việt, dễ hiểu với sinh viên, đúng trọng tâm, giữ nguyên thuật ngữ của sách.
     Nhiều ý thì dùng gạch đầu dòng. Người dùng xin "nguyên văn" thì chép đúng nguyên văn.
     Người dùng yêu cầu số ý hoặc độ dài (vd "3 ý", "ngắn gọn") thì làm đúng yêu cầu.
   - "quotes": 1 đến 4 câu chép NGUYÊN VĂN, chính xác từng chữ, từ TÀI LIỆU, làm căn cứ cho các ý chính.
     Không sửa chữ, không gộp hai câu ở hai chỗ khác nhau thành một.
   - "example": CHỈ điền khi người dùng xin ví dụ, liên hệ thực tế hoặc áp dụng: 1-3 câu ví dụ do bạn tự nghĩ,
     đúng với lý thuyết trong "answer". Không viết ví dụ này vào "answer". Không cần thì để "".
6. Chỉ trả về JSON đúng định dạng yêu cầu."""


def build_context(chunks: list[Chunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        pages = f"Trang {c.page_start}" if c.page_start == c.page_end else f"Trang {c.page_start}-{c.page_end}"
        blocks.append(f"[Đoạn {i} | {pages} | {c.header}]\n{c.text}")
    return "\n\n".join(blocks)


WEAK_NOTE = (
    "\n\nLƯU Ý: các đoạn trên được tìm tự động và có thể chỉ gần đúng chủ đề. Đọc kỹ: TÀI LIỆU có nội dung "
    "trả lời thì trả lời bình thường; chỉ na ná chủ đề mà không trả lời được điều được hỏi thì đặt \"found\": false."
)


def build_user_message(chunks: list[Chunk], question: str, search_query: str, weak: bool = False) -> str:
    """weak=True: điểm tìm kiếm thấp (đoạn tìm được có thể chỉ na ná chủ đề) -> nhắc model chặt hơn."""
    q = question
    if search_query.strip() != question.strip():
        q += f"\n(Hiểu đầy đủ là: {search_query})"
    note = WEAK_NOTE if weak else ""
    return f"TÀI LIỆU:\n<<<\n{build_context(chunks)}\n>>>{note}\n\nCÂU HỎI: {q}"


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
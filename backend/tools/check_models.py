from app import llm, embedder

print("CHAT:", llm.chat([{"role": "user", "content": "Chào bạn, trả lời một câu ngắn."}]))

v1 = embedder.embed_query("Học phí ngành công nghệ thông tin là bao nhiêu?")
docs = embedder.embed_documents([
    "Học phí ngành Công nghệ thông tin năm 2026 là 15 triệu đồng mỗi học kỳ.",
    "Ký túc xá có 500 phòng, ưu tiên sinh viên năm nhất.",
])
print("Số chiều vector:", v1.shape)
print("Độ giống với 2 đoạn:", docs @ v1)
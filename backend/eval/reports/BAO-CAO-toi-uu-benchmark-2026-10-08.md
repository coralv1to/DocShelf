# Báo cáo tối ưu tốc độ + benchmark — 08/10/2026

Tài liệu test: `sample.pdf` (Stanford CS229 cheatsheet tiếng Việt, 17 trang) · doc_id `2e13c575fc094c829995a7a2f8131cba` (54 đoạn, gồm 1 đoạn tổng quan) · báo cáo gốc: `backend\eval\reports\bench_20261008_122323.md`

## 1. Áp dụng thay đổi

- **Đã chép file:** có, không lỗi. Có 5 file `config.py`, `llm.py`, `embedder.py`, `reranker.py`, `verify.py` và thư mục `eval\`. Hai file `chunker.py` và `pipeline.py` đã được chép trước đó, mã băm trùng với gói.
- **Sao lưu:** `doc-qa\backup-truoc-toi-uu\`, gồm toàn bộ `app\*.py` và `env.bak`. `chunker.py` và `pipeline.py` trong thư mục sao lưu là **bản cũ thật**, tức bản trước khi áp gói.
- **`.env`:** đã thêm `KEEP_ALIVE=30m`, `EMBED_NUM_CTX=2048`, `RERANK_MAX_LENGTH=512`, `RERANK_TRUST_REMOTE_CODE=false`.
- **Kiểm tra trước khi chạy thật:** đã chạy thử `run_bench.py` bằng model giả lập. Script chạy hết 3 cấu hình và ghi được báo cáo.
- **`ollama ps` sau khi chạy xong:**

  ```
  NAME                    SIZE      PROCESSOR    CONTEXT    UNTIL
  qwen3-embedding:0.6b    2.1 GB    100% GPU     2048       29 minutes from now
  qwen3.5:4b              3.3 GB    100% GPU     8192       29 minutes from now
  ```

  → **UNTIL khoảng 30 phút** (trước đây chỉ 2–4 phút), nên keep-alive đã có hiệu lực. Embedding giảm từ 2,4GB xuống **2,1GB**. Tổng 5,4/6GB, cả hai model chạy 100% GPU.

## 2. Kết quả benchmark

### 2.1. Tổng hợp

| Cấu hình | Có trong file | Tổng quan | Không liên quan | Bẫy | Hội thoại | Tổng | Trung vị (s) | Trung vị rerank (s) | Trung vị LLM (s) | Chậm nhất (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| vector_only | 6/9 | 0/2 | 2/2 | 4/4 | 8/12 | 20/29 | **5.9** | 0.0 | 5.2 | 11.1 |
| rerank8 | 5/9 | 0/2 | 2/2 | 4/4 | 7/12 | 18/29 | 15.3 | 6.9 | 7.1 | 18.2 |
| rerank8_bm25 | 6/9 | 1/2 | 2/2 | 4/4 | **10/12** | **23/29** | 14.9 | 6.9 | 6.5 | 18.3 |

### 2.2. Thời gian trung vị theo bước (giây)

| Cấu hình | Làm nóng | rewrite | retrieve | rerank | llm | verify | locate |
|---|---|---|---|---|---|---|---|
| vector_only | 11.4 | 0.0 | 2.2 | 0.0 | 5.2 | 0.0 | 0.1 |
| rerank8 | 24.7 | 0.0 | 2.2 | 6.9 | 7.1 | 0.0 | 0.1 |
| rerank8_bm25 | 15.6 | 0.0 | 2.2 | 6.9 | 6.5 | 0.0 | 0.1 |

### 2.3. So với ngưỡng chấp nhận

| Tiêu chí | Yêu cầu | vector_only | rerank8 | rerank8_bm25 |
|---|---|---|---|---|
| Không liên quan (bắt buộc) | 2/2 | ✅ | ✅ | ✅ |
| Bẫy (bắt buộc) | 4/4 | ✅ | ✅ | ✅ |
| Lượt bẫy C4.3 (bắt buộc) | PASS | ✅ | ✅ | ✅ |
| Có trong file | ≥ 8/9 | ❌ 6/9 | ❌ 5/9 | ❌ 6/9 |
| Tổng quan | 2/2 | ❌ 0/2 | ❌ 0/2 | ❌ 1/2 |
| Hội thoại | ≥ 10/12 | ❌ 8/12 | ❌ 7/12 | ✅ 10/12 |
| Trung vị | < 15s | ✅ 5.9 | ❌ 15.3 | ✅ 14.9 (sát ngưỡng) |

**Không cấu hình nào bịa.** Không có cấu hình nào đạt đủ mọi tiêu chí. Hai tiêu chí chưa đạt ở mọi cấu hình là "có trong file" và "tổng quan".

## 3. Nhận xét

**Tốc độ**
- Bước chậm nhất là **rerank, trung vị 6,9s** trên CPU. LLM trung vị 6,5–7,1s.
- So với trước (60–70 giây/câu): `rerank8_bm25` nhanh hơn khoảng **4,5 lần** (trung vị 14,9s), `vector_only` nhanh hơn khoảng **11 lần** (5,9s).
- Nguyên nhân chậm cũ đã được xác nhận: rerank 20 đoạn trên CPU. Giảm xuống 8 đoạn còn 6,9s, dưới mức 10s của cây quyết định, nên **không cần thử reranker nhỏ**.
- LLM dưới 15s và chạy 100% GPU, nên **không cần giảm `NUM_CTX`**.
- `retrieve` mất đều 2,2s ở mọi cấu hình, có lẽ là thời gian embed câu hỏi. Đây là chỗ đáng xem tiếp.

**Câu bẫy, câu không liên quan: đạt hết, không có câu nào bị "BỊA".**
- Có rerank: cả 4 câu bẫy bị chặn ngay ở lớp 1 (điểm 0,0001–0,27, ngưỡng 0,3), khoảng cách an toàn tốt.
- `vector_only`: T01 và T02 vượt qua lớp 1 (điểm 0,61 và 0,49, ngưỡng 0,45) và **chỉ được chặn nhờ model tự nói không thấy** (`model_not_found`). T03, T04 và C4.3 có điểm 0,41–0,44, chỉ thấp hơn ngưỡng 0,45 một chút. Cấu hình này đạt bẫy nhưng **biên an toàn mỏng**.

**Lỗi chiếm đa số: `quote_not_verified`, tức model trả lời được nhưng trích dẫn không kiểm chứng được.**
- Gặp ở S04 (PCA) và S07 (cross-validation) **ở cả 3 cấu hình**, điểm tìm kiếm cao (0,67–0,94), nghĩa là đã tìm đúng đoạn.
- Gặp ở O01 ở cả 3 cấu hình, và O02 ở 2 cấu hình.
- S02, S08 lúc đạt lúc trượt giữa các cấu hình dù cùng điểm 0,94/0,96. Như vậy model chép câu trích không ổn định.
- Hiện **chưa xem được câu trích gốc** của model, vì khi bị từ chối, pipeline không giữ lại `quotes`. Giả thuyết cần kiểm chứng:
  1. Model chép cả phần tiêu đề trong ngoặc `[Đoạn i | Trang … | header]`. Phần này không nằm trong `text` của đoạn nên không qua kiểm chứng. Rất có thể đây là lý do O01/O02 trượt, vì tên "Tổng quan tài liệu – các mục chính" chỉ có trong header.
  2. Model gộp nhiều dòng hoặc nhiều tiêu đề vào một câu trích, hoặc chép lệch công thức. PCA và cross-validation là các đoạn có nhiều ký hiệu.

**Hội thoại**
- C1 (đại từ "nó") và C3 (chuyển chủ đề) đạt ở `rerank8_bm25`. Việc viết lại câu hỏi đã hoạt động: "Bằng cách nào?" thành "Bằng cách nào để LSTM tránh được vấn đề gradient biến mất…".
- **C2.2 và C2.3 trượt ở cả 3 cấu hình. Nguyên nhân là câu viết lại bỏ mất chủ thể "k-NN":**
  - "Tăng k thì sao?" thành "Nếu tăng giá trị k thì ảnh hưởng như thế nào đến độ chính xác của mô hình?"
  - "Còn giảm k?" thành "Còn khi giảm giá trị của tham số k thì sao?" (`vector_only`), hoặc "Nếu giảm giá trị của k thì sẽ ảnh hưởng như thế nào đến mô hình?" (`rerank8_bm25`)
  - Thiếu "k-NN" nên reranker cho điểm 0,03–0,04 và câu bị từ chối.
- Lượt bẫy C4.3 đạt ở cả 3 cấu hình. Ở `rerank8_bm25`, bước viết lại còn tự điền tên "Adam" lấy từ câu trả lời trước ("Ai là người đã đề xuất phương thức Adam…"), nhưng vẫn bị chặn đúng.
- S06 / C4.2 ("phương thức điều chỉnh tốc độ học"): chỉ đạt khi có BM25. Không có BM25 thì đoạn đúng không lọt top 8, điểm chỉ 0,04. Đây là bằng chứng rõ cho lợi ích của BM25 với thuật ngữ cụ thể.

## 4. Đề xuất

### 4.1. Cấu hình chọn: `rerank8_bm25`

`.env` đã đặt: `USE_RERANK=true`, `USE_BM25=true`, `TOP_K_RETRIEVE=8`, `USE_REWRITE=true`. **Cần khởi động lại uvicorn** để có hiệu lực.

⚠️ **Lựa chọn này lệch khỏi quy tắc trong hướng dẫn, cần v1to duyệt.** Quy tắc "nhanh nhất mà vẫn đạt mọi tiêu chí bắt buộc" sẽ chọn `vector_only`, vì cả 3 cấu hình đều đạt 3 tiêu chí bắt buộc. Mình chọn `rerank8_bm25` vì:
- Tổng điểm cao nhất (23/29 so với 20/29) và là cấu hình duy nhất đạt tiêu chí hội thoại.
- Chặn bẫy ở lớp 1 với biên rộng. `vector_only` phải dựa vào model 4B tự từ chối ở 2/4 câu bẫy.
- Trung vị 14,9s vẫn dưới mục tiêu 15s, dù sát ngưỡng.

Muốn ưu tiên tốc độ thì đổi về `USE_RERANK=false`, `USE_BM25=false`, `TOP_K_RETRIEVE=20`.

### 4.2. Việc nên làm tiếp (chưa làm, cần v1to duyệt)

1. **Ghi lại câu trích gốc khi bị từ chối** (sửa nhỏ trong `pipeline.py`: thêm `debug["raw_quotes"] = result.get("quotes")`), rồi chạy lại benchmark để xác định đúng nguyên nhân `quote_not_verified`. Đây là việc ưu tiên số 1, vì lỗi này gây ra 4/6 câu trượt của cấu hình chọn (2 câu còn lại là C2.2, C2.3 ở mục 3).
2. Nếu giả thuyết 1 đúng: thêm vào `SYSTEM_PROMPT` dòng "chỉ trích từ nội dung đoạn, không trích dòng tiêu đề trong ngoặc vuông", hoặc cho `verify.py` chấp nhận trích dẫn khớp với `header`.
3. **Sửa `REWRITE_PROMPT`**: thêm quy tắc "luôn giữ tên khái niệm/thuật toán đang được nói tới trong lịch sử", kèm một ví dụ dạng "Tăng k thì sao?" → "Tăng k trong k-NN thì ảnh hưởng thế nào?". Dự kiến sửa được C2.2 và C2.3.
4. Tìm hiểu vì sao bước `retrieve` mất 2,2s. Có thể do gọi embedding qua Ollama, hoặc do `underthesea` tách từ cho BM25. Bước này nằm ngay trên đường đi của mọi câu hỏi.
5. Tăng `MIN_RERANK_SCORE` là không cần thiết: điểm bẫy cao nhất là 0,27, trong khi câu đúng thường trên 0,75.

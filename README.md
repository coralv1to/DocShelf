# DocShelf

Kệ tài liệu hỏi đáp bằng LLM chạy local (Qwen qua Ollama). Upload nhiều file PDF lên kệ, chọn từng tài liệu để chat:

- Chỉ trả lời theo nội dung tài liệu đang chọn, kèm trích dẫn nguyên văn và vị trí trên trang
- Từ chối khi tài liệu không có thông tin thay vì bịa
- Hiểu câu hỏi tiếp nối trong hội thoại, lưu lịch sử trò chuyện
- Đăng nhập, phân quyền: admin upload/xóa tài liệu, người dùng xem và chat
- 3 chế độ trả lời Nhanh / Cân bằng / Kỹ, admin chỉnh trong trang Cài đặt
- API có API key để hệ thống khác tích hợp (gửi file → nhận `doc_id` → chat trên đúng file đó)

## Tài liệu

| File | Nội dung |
|---|---|
| [docs/01-huong-dan-chay-local.md](docs/01-huong-dan-chay-local.md) | Chạy trên máy cá nhân: Postgres bằng Docker, tạo bảng, tạo tài khoản admin, chạy app |
| [docs/02-production-va-tich-hop-api.md](docs/02-production-va-tich-hop-api.md) | Đưa lên server cho nhiều người dùng, nâng model, tích hợp API vào hệ thống khác |
| [docs/huong-dan-build-rag-qwen-nextjs.md](docs/huong-dan-build-rag-qwen-nextjs.md) | Hướng dẫn gốc xây dựng pipeline RAG từng bước |

## Cấu trúc

```
docshelf/
├── backend/                FastAPI + pipeline RAG
│   ├── app/
│   │   ├── main.py         API cho giao diện DocShelf (/api/...)
│   │   ├── api_v1.py       API tích hợp cho hệ thống ngoài (/api/v1/..., API key)
│   │   ├── auth.py         đăng nhập, JWT cookie, phân quyền
│   │   ├── chat_service.py hỏi đáp dùng chung: lịch sử, gọi pipeline, lưu tin nhắn
│   │   ├── options.py      3 chế độ trả lời (bước nào chạy / bỏ qua)
│   │   ├── app_settings.py cài đặt admin chỉnh trên giao diện
│   │   ├── followup.py     nhận biết câu hỏi nối tiếp (có cần viết lại không)
│   │   ├── warmup.py       nạp sẵn model + tài liệu khi khởi động
│   │   ├── models.py       các bảng database
│   │   ├── db.py           kết nối Postgres
│   │   ├── store.py        lưu / nạp tài liệu đã index
│   │   ├── cli.py          lệnh quản trị (tạo tài khoản, API key, reindex...)
│   │   └── pipeline.py ... pipeline RAG (cắt đoạn, tìm kiếm, rerank, LLM, kiểm chứng)
│   ├── alembic/            migration tạo / cập nhật bảng
│   ├── eval/               benchmark chất lượng
│   ├── tools/              script kiểm tra (python -m tools.<tên>)
│   └── data/               file PDF gốc (không commit)
├── frontend/               Next.js
├── db/init/                SQL chạy lần đầu khi tạo Postgres
├── docs/                   tài liệu
└── docker-compose.yml      Postgres + pgvector
```

## Chạy nhanh (đã cài đặt xong theo docs/01)

```powershell
docker compose up -d

cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# cửa sổ khác
cd frontend
npm run dev
```

Mở http://localhost:3000

## Lệnh quản trị (trong backend/, đã activate .venv)

| Lệnh | Việc |
|---|---|
| `alembic upgrade head` | Tạo / cập nhật bảng |
| `python -m app.cli create-user admin --role admin` | Tạo tài khoản quản trị |
| `python -m app.cli create-user <tên>` | Tạo tài khoản người dùng |
| `python -m app.cli list-users` / `set-password` / `set-active` | Quản lý tài khoản |
| `python -m app.cli import-legacy` | Nhập tài liệu cũ trong `data/` vào database |
| `python -m app.cli create-api-key <tên>` | Cấp API key cho hệ thống ngoài |
| `python -m app.cli reindex --all` | Embed lại sau khi đổi `EMBED_MODEL` |

## Script kiểm tra (trong backend/, đã activate .venv)

| Lệnh | Việc |
|---|---|
| `python -m tools.check_models` | Gọi thử chat model + embedding |
| `python -m tools.check_latency` | So sánh độ trễ localhost và 127.0.0.1 |
| `python -m tools.check_index` | Cắt đoạn `sample.pdf`, in 5 đoạn đầu |
| `python -m tools.check_locate sample.pdf 3 "câu trích"` | Tô vị trí câu trích, lưu `locate_test.png` |
| `python -m tools.load_test --key dsk_... --doc <doc_id>` | Kiểm thử nhiều người hỏi cùng lúc |
| `chay-benchmark.bat` | Benchmark chất lượng, log ở `eval\bench_log.txt` |

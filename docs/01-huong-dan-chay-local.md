# DocShelf — Hướng dẫn chạy local (máy cá nhân)

Tài liệu này dành cho việc chạy DocShelf trên máy của bạn như một ứng dụng cá nhân / để phát triển.
Đưa lên server cho nhiều người dùng và tích hợp vào hệ thống khác: xem
[02-production-va-tich-hop-api.md](02-production-va-tich-hop-api.md).

## Mục lục

1. [Bức tranh tổng thể](#1-bức-tranh-tổng-thể)
2. [Chuẩn bị](#2-chuẩn-bị)
3. [Bật Postgres bằng Docker](#3-bật-postgres-bằng-docker)
4. [Cài backend và kết nối database](#4-cài-backend-và-kết-nối-database)
5. [Tạo bảng bằng Alembic](#5-tạo-bảng-bằng-alembic)
6. [Tạo tài khoản quản trị và người dùng](#6-tạo-tài-khoản-quản-trị-và-người-dùng)
7. [Chuyển tài liệu cũ vào database](#7-chuyển-tài-liệu-cũ-vào-database-nếu-có)
8. [Chạy backend + frontend](#8-chạy-backend--frontend)
8b. [Chế độ trả lời và trang Cài đặt](#8b-chế-độ-trả-lời-và-trang-cài-đặt)
9. [Dùng hằng ngày](#9-dùng-hằng-ngày)
10. [Đổi model](#10-đổi-model)
11. [Benchmark](#11-benchmark)
12. [Lỗi thường gặp](#12-lỗi-thường-gặp)
13. [Bảng lệnh nhanh](#13-bảng-lệnh-nhanh)

---

## 1. Bức tranh tổng thể

```
Trình duyệt ──► Next.js (cổng 3000) ──/api/*──► FastAPI (cổng 8000) ──► Postgres + pgvector (Docker, cổng 5433)
                  giao diện                       pipeline RAG          tài khoản, tài liệu, đoạn văn,
                                                      │                 vector, lịch sử chat
                                                      ▼
                                                 Ollama (cổng 11434)
                                                 qwen3.5:4b (trả lời) + qwen3-embedding:0.6b (vector)
```

Dữ liệu nằm ở đâu:

| Dữ liệu | Nơi lưu |
|---|---|
| Tài khoản, tài liệu, đoạn văn + vector, cuộc trò chuyện, tin nhắn | Postgres (volume Docker `docshelf_pgdata`) |
| File PDF gốc (để hiện trang nguồn và tô trích dẫn) | `backend/data/<doc_id>/source.pdf` |
| Cấu hình, mật khẩu, khóa bí mật | `backend/.env` (không commit lên git) |

Phân quyền:

| Quyền | Admin | User |
|---|---|---|
| Xem kệ tài liệu, chat, xem trang nguồn | ✅ | ✅ |
| Xem lại / xóa cuộc trò chuyện của mình | ✅ | ✅ |
| Upload, xóa tài liệu | ✅ | ❌ |
| Xem cuộc trò chuyện của người khác | ❌ | ❌ |

Tài khoản được tạo bằng dòng lệnh (mục 6), chưa có trang đăng ký.

---

## 2. Chuẩn bị

Cần có trên máy:

- **Docker Desktop** (đang chạy)
- **Python 3.12+** (máy bạn đang dùng 3.14)
- **Node.js 20+**
- **Ollama** với 2 model:

```powershell
ollama pull qwen3.5:4b
ollama pull qwen3-embedding:0.6b
```

Mọi lệnh bên dưới chạy trong **PowerShell**, đứng ở thư mục gốc project (`D:\03_Projects\08_LLM\doc-qa`) trừ khi ghi khác.

---

## 3. Bật Postgres bằng Docker

File `docker-compose.yml` ở thư mục gốc đã cấu hình sẵn: Postgres 17 có extension **pgvector** (lưu vector), dữ liệu nằm trong volume nên tắt/xóa container không mất.

```powershell
docker compose up -d
docker compose ps
```

Chờ cột STATUS hiện `healthy` (khoảng 10 giây). Kiểm tra pgvector đã bật:

```powershell
docker exec -it docshelf-db psql -U docshelf -d docshelf -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
```

In ra một số phiên bản (vd `0.8.x`) là được. Nếu ra `(0 rows)` cũng không sao: bước 5 sẽ tự bật.

Thông số kết nối (dùng cho DBeaver / pgAdmin nếu muốn xem bảng):

| | |
|---|---|
| Host | `127.0.0.1` |
| Port | `5433` |
| Database | `docshelf` |
| User | `docshelf` |
| Password | `docshelf_dev_123` |

> Chỉ dùng mật khẩu này ở máy dev. Cổng được mở ở `127.0.0.1` nên máy khác trong mạng không vào được.

---

## 4. Cài backend và kết nối database

### 4.1. Cài thư viện

```powershell
cd backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Lần này `requirements.txt` có thêm:

| Thư viện | Dùng để |
|---|---|
| `sqlalchemy` | Làm việc với database bằng class Python thay vì viết SQL tay |
| `psycopg[binary]` | Driver kết nối Postgres |
| `pgvector` | Cho SQLAlchemy hiểu kiểu cột `vector` |
| `alembic` | Tạo / cập nhật cấu trúc bảng theo từng phiên bản (migration) |
| `bcrypt` | Băm mật khẩu (không bao giờ lưu mật khẩu gốc) |
| `pyjwt` | Tạo / kiểm tra token đăng nhập |

### 4.2. Cấu hình `.env`

Mở `backend\.env` (nếu chưa có thì sao chép từ `.env.example`). Cần có 2 dòng:

```dotenv
DATABASE_URL=postgresql+psycopg://docshelf:docshelf_dev_123@127.0.0.1:5433/docshelf
JWT_SECRET=<chuỗi ngẫu nhiên dài>
```

Tạo `JWT_SECRET`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Dán kết quả vào sau `JWT_SECRET=`.

Ý nghĩa `DATABASE_URL`:

```
postgresql+psycopg :// docshelf : docshelf_dev_123 @ 127.0.0.1 : 5433 / docshelf
   loại DB + driver     user        mật khẩu          máy      cổng   tên database
```

`JWT_SECRET` là khóa dùng để **ký** token đăng nhập. Ai có khóa này có thể tự tạo token giả danh bất kỳ ai, nên giữ bí mật và không commit lên git. Đổi khóa thì mọi người phải đăng nhập lại.

Nên đổi luôn dòng `OLLAMA_HOST` thành `http://127.0.0.1:11434`: trên Windows, `localhost` có thể chậm thêm khoảng 2 giây mỗi lần gọi (kiểm tra bằng `python -m tools.check_latency`).

---

## 5. Tạo bảng bằng Alembic

```powershell
alembic upgrade head
```

Lệnh này đọc các file trong `backend/alembic/versions/` và tạo bảng:

| Bảng | Nội dung |
|---|---|
| `users` | Tài khoản: tên đăng nhập, mật khẩu đã băm, quyền `admin` / `user` |
| `api_clients` | Hệ thống ngoài được cấp API key (xem tài liệu 02) |
| `documents` | Tài liệu: tên, số trang, mã băm file (chặn upload trùng), model embedding đã dùng |
| `chunks` | Các đoạn văn của tài liệu + vector (cột kiểu `vector` của pgvector) |
| `chat_sessions` | Cuộc trò chuyện: của ai, về tài liệu nào |
| `messages` | Từng câu hỏi / câu trả lời, kèm trích dẫn (JSONB) |

Mỗi khi nhận phiên bản code mới có thêm file trong `alembic/versions/`, chạy lại `alembic upgrade head` (chạy thừa không sao). Phiên bản hiện tại có 2 migration: `0001` (các bảng chính) và `0002` (bảng `app_settings` cho trang Cài đặt + cột `search_tokens` lưu sẵn kết quả tách từ cho BM25).

Sau này sửa `app/models.py` (thêm cột, thêm bảng) thì **không sửa database bằng tay**, mà:

```powershell
alembic revision --autogenerate -m "mo ta thay doi"   # sinh file migration mới
# mở file vừa sinh trong alembic/versions/ đọc lại cho chắc
alembic upgrade head                                  # áp dụng
```

---

## 6. Tạo tài khoản quản trị và người dùng

Mọi lệnh quản trị nằm trong `app/cli.py`:

```powershell
# Tài khoản quản trị (được upload / xóa tài liệu)
python -m app.cli create-user admin --role admin --name "Quản trị viên"

# Tài khoản người dùng thường (chỉ xem và chat)
python -m app.cli create-user sv01 --name "Nguyễn Văn A"
```

Lệnh sẽ hỏi mật khẩu 2 lần. Lúc gõ **không hiện chữ**, đó là bình thường: mật khẩu không bị lưu vào lịch sử lệnh của PowerShell.

Quy tắc: tên đăng nhập 3–50 ký tự, chỉ `a-z 0-9 . _ -` (tự chuyển về chữ thường); mật khẩu tối thiểu 8 ký tự.

Các lệnh khác:

```powershell
python -m app.cli list-users              # xem danh sách
python -m app.cli set-password sv01       # đổi mật khẩu (vd người dùng quên)
python -m app.cli set-active sv01 --off   # khóa tài khoản
python -m app.cli set-active sv01 --on    # mở lại
```

---

## 7. Chuyển tài liệu cũ vào database (nếu có)

Các tài liệu đã upload trước khi có Postgres nằm trong `backend/data/<doc_id>/` (gồm `meta.json` + `embeddings.npy`). Chuyển vào database, **không phải embed lại**:

```powershell
python -m app.cli import-legacy
```

Chạy lại nhiều lần không sao: tài liệu đã có sẽ được bỏ qua. Tài liệu được nhập sẽ hiện trên kệ, chưa gắn người upload. Sau khi kiểm tra ổn, có thể xóa `meta.json` và `embeddings.npy` trong các thư mục đó (giữ `source.pdf`).

---

## 8. Chạy backend + frontend

**Cửa sổ 1 — backend** (trong `backend`, đã activate `.venv`):

```powershell
uvicorn app.main:app --reload --port 8000
```

Lúc khởi động, backend kiểm tra `JWT_SECRET` và kết nối Postgres; thiếu gì sẽ báo lỗi rõ ràng (xem mục 12). Tài liệu API tự sinh: http://localhost:8000/docs

**Cửa sổ 2 — frontend:**

```powershell
cd frontend
npm run dev
```

Mở http://localhost:3000 → tự chuyển sang trang đăng nhập.

- Đăng nhập **admin**: thấy ô "Thêm tài liệu lên kệ" và nút xóa (hiện khi rê chuột vào thẻ tài liệu).
- Đăng nhập **user**: chỉ thấy kệ tài liệu và chat.
- Bấm một tài liệu → chat. Sidebar hiện lịch sử các cuộc trò chuyện về tài liệu đó; tải lại trang vẫn còn.

Khi backend khởi động, log hiện các dòng `warmup: ... xong`: backend đang nạp sẵn model embedding, model trả lời, reranker và các tài liệu. Câu hỏi đầu tiên sau khi các dòng này xong sẽ không phải chờ nạp model (trước đây chờ thêm 10–20 giây). Tắt bằng `WARMUP=false` trong `.env` nếu muốn khởi động nhẹ hơn.

---

## 8b. Chế độ trả lời và trang Cài đặt

Admin vào **Cài đặt** (sidebar) để chọn chế độ trả lời mặc định:

| Chế độ | Chạy những bước nào | Thời gian thường gặp* |
|---|---|---|
| **Nhanh** | Tìm kiếm (vector + từ khóa) → LLM trả lời. **Không rerank** | 3–8 giây |
| **Cân bằng** (khuyên dùng) | Như Kỹ, nhưng **bỏ qua bước không cần cho câu hỏi đó**: câu đã đủ nghĩa thì không viết lại; câu hỏi vị trí ("append ở trang nào") đã rõ kết quả thì không rerank | 5–15 giây, câu hỏi vị trí 1–3 giây |
| **Kỹ** | Luôn viết lại câu hỏi theo hội thoại (LLM) + luôn rerank | 15–25 giây |

\* Ước tính trên laptop GPU 6GB, `qwen3.5:4b`, reranker chạy CPU. Số thật: chạy benchmark (mục 11).

Các tùy chọn khác trong trang Cài đặt:

- **Cho người dùng tự chọn chế độ:** bật thì ô chat có nút Nhanh / Cân bằng / Kỹ (trình duyệt nhớ lựa chọn); tắt thì mọi người dùng chế độ mặc định.
- **Nâng cao:** số đoạn tìm, số đoạn đưa cho model, các ngưỡng từ chối, số lượt hội thoại nhớ. Ô nào khác mặc định thì viền vàng. **Khôi phục mặc định** đưa về giá trị trong `.env`.

Thay đổi có hiệu lực từ câu hỏi tiếp theo, không cần khởi động lại backend.

**Xem một câu hỏi đã chạy những bước nào:** bấm **Chi tiết** dưới câu trả lời. Mục `steps` cho biết bước nào đã chạy / bỏ qua và vì sao; `timings_ms` là số mili giây từng bước. Ví dụ:

```json
"mode": "balanced",
"steps": {
  "rewrite": "bỏ qua (câu hỏi đã đủ nghĩa)",
  "rerank": "bỏ qua (câu hỏi vị trí, vector và từ khóa cùng chọn 1 đoạn)"
}
```

Câu hỏi vị trí mà vẫn bị rerank thì `steps.rerank` ghi lý do, ví dụ "tìm theo nghĩa và theo từ khóa chọn 2 đoạn khác nhau" hoặc "từ khóa xuất hiện nhiều ở nhiều đoạn".

**Viết lại câu hỏi khi nào (chế độ Nhanh / Cân bằng):** chỉ khi câu hỏi có dấu hiệu phụ thuộc hội thoại: đại từ ("nó", "phương thức đó"), mở đầu nối tiếp ("Còn…", "Vậy…"), thiếu chủ ngữ ("Khi nào thì dừng?"), hoặc không có từ nội dung ("Bằng cách nào?"). Quy tắc nằm trong `backend/app/followup.py`. Câu nối tiếp ngầm không có dấu hiệu (vd hỏi "Xác suất giữ lại là bao nhiêu?" ngay sau câu về dropout) sẽ không được viết lại; bước trả lời vẫn đọc lịch sử nên thường vẫn đúng. Cần chắc chắn thì dùng chế độ Kỹ.

---

## 9. Dùng hằng ngày

```powershell
# Mở Docker Desktop (Postgres tự chạy vì restart: unless-stopped)
cd D:\03_Projects\08_LLM\doc-qa\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
# cửa sổ khác
cd D:\03_Projects\08_LLM\doc-qa\frontend
npm run dev
```

Sao lưu dữ liệu:

```powershell
docker exec docshelf-db pg_dump -U docshelf -Fc -f /tmp/backup.dump docshelf
docker cp docshelf-db:/tmp/backup.dump .\backup_docshelf.dump
# sao lưu kèm thư mục backend\data (file PDF gốc)
```

> Không dùng `pg_dump ... > file` trong PowerShell: PowerShell đổi mã hóa ký tự khi ghi qua `>`, làm hỏng file nhị phân.

Khôi phục:

```powershell
docker cp .\backup_docshelf.dump docshelf-db:/tmp/backup.dump
docker exec docshelf-db pg_restore -U docshelf -d docshelf --clean --if-exists /tmp/backup.dump
```

Xóa sạch làm lại từ đầu (**mất hết dữ liệu**):

```powershell
docker compose down -v      # -v: xóa luôn volume dữ liệu
docker compose up -d
cd backend; alembic upgrade head
```

---

## 10. Đổi model

**Model trả lời** (`CHAT_MODEL`): `ollama pull <model>` → sửa `.env` → khởi động lại backend. Không cần làm gì với dữ liệu.

**Model embedding** (`EMBED_MODEL`): vector cũ được tạo bằng model cũ, không so được với câu hỏi embed bằng model mới. Sau khi đổi:

```powershell
ollama pull qwen3-embedding:4b
# sửa EMBED_MODEL trong .env
python -m app.cli reindex --all     # embed lại mọi tài liệu (không cần đọc lại PDF)
# khởi động lại backend
```

Nếu quên `reindex`, khi chat sẽ nhận lỗi 409 nhắc chạy lệnh này, thay vì trả lời sai.

Với GPU 6GB, xem phần đánh giá VRAM trong tài liệu 02 trước khi nâng model.

---

## 11. Benchmark

Benchmark gọi thẳng pipeline nên cần Postgres đang chạy:

```powershell
cd backend
chay-benchmark.bat
# hoặc
python -m eval.run_bench --pdf sample.pdf
```

Chạy lại `--pdf` cùng một file sẽ tự dùng lại tài liệu đã index, không tạo bản trùng trên kệ.

Mặc định benchmark chạy 3 chế độ `mode_fast`, `mode_balanced`, `mode_accurate` để so tốc độ và độ chính xác. Các cấu hình cũ vẫn chạy được: `python -m eval.run_bench --pdf sample.pdf --profiles vector_only rerank8_bm25`. Bộ câu hỏi có thêm 5 câu hỏi vị trí (L01–L04, LT1).

Lưu ý khi đọc kết quả chế độ Cân bằng: câu C1.3 ("Xác suất giữ lại một neural là bao nhiêu?") có thể báo "viết lại thiếu ngữ cảnh" vì đây là câu nối tiếp ngầm mà quy tắc không nhận ra (xem mục 8b). Xem cột trang trích dẫn để biết câu trả lời có đúng không.

---

## 12. Lỗi thường gặp

| Thông báo | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Chưa đặt JWT_SECRET (>= 32 ký tự)` | Thiếu / quá ngắn trong `.env` | Làm mục 4.2 |
| `Không kết nối được Postgres` | Docker Desktop chưa chạy, chưa `docker compose up -d`, sai `DATABASE_URL` | `docker compose ps` phải `healthy` |
| `relation "users" does not exist` | Chưa tạo bảng | `alembic upgrade head` |
| `port is already allocated` khi `docker compose up` | Cổng 5433 bị chiếm | Đổi `127.0.0.1:5433` thành cổng khác trong compose **và** trong `DATABASE_URL` |
| Đăng nhập xong lại bị đẩy về trang đăng nhập | Cookie không lưu được | Mở bằng `http://localhost:3000`; local thì để `COOKIE_SECURE=false` |
| Chat báo 409 "index bằng ... đang dùng ..." | Đã đổi `EMBED_MODEL` | `python -m app.cli reindex --all` |
| Chat báo 503 "Không kết nối được Ollama" | Ollama chưa chạy | Mở Ollama, `ollama ps` |
| `column chunks.search_tokens does not exist` hoặc `relation "app_settings" does not exist` | Code mới, database chưa cập nhật | `alembic upgrade head` |
| Trả lời chậm | Xem **Chi tiết** → `timings_ms` để biết bước nào chậm | Mục 8b: chọn chế độ Nhanh / Cân bằng |
| Upload báo 409 "đã có trên kệ" | File trùng nội dung với tài liệu đã có | Bình thường: dùng tài liệu đã có |
| `password authentication failed for user "docshelf"` | Volume cũ tạo với mật khẩu khác | `docker compose down -v` rồi `up -d` (mất dữ liệu), hoặc sửa `DATABASE_URL` cho đúng mật khẩu cũ |

---

## 13. Bảng lệnh nhanh

| Việc | Lệnh (trong `backend`, đã activate `.venv`) |
|---|---|
| Tạo / cập nhật bảng | `alembic upgrade head` |
| Tạo admin | `python -m app.cli create-user admin --role admin` |
| Tạo user | `python -m app.cli create-user <tên> --name "Họ tên"` |
| Đổi mật khẩu | `python -m app.cli set-password <tên>` |
| Khóa / mở tài khoản | `python -m app.cli set-active <tên> --off` / `--on` |
| Danh sách tài khoản | `python -m app.cli list-users` |
| Nhập tài liệu cũ | `python -m app.cli import-legacy` |
| Index lại sau khi đổi model embedding | `python -m app.cli reindex --all` |
| Cấp API key cho hệ thống ngoài | `python -m app.cli create-api-key <tên>` |
| Chạy backend | `uvicorn app.main:app --reload --port 8000` |
| Kiểm tra độ trễ Ollama | `python -m tools.check_latency` |

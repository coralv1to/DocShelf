# DocShelf — Đưa lên server (production) và tích hợp API vào hệ thống khác

Tài liệu gồm 2 phần:

- **Phần A — Build production:** đưa DocShelf lên server cho nhiều người dùng cùng lúc, nâng cấp model.
- **Phần B — Tích hợp API:** một hệ thống khác (vd hệ thống quản lý đào tạo) gửi file sang DocShelf, nhận `doc_id`, rồi cho người dùng của họ chat trên đúng file đó.

Chạy trên máy cá nhân: xem [01-huong-dan-chay-local.md](01-huong-dan-chay-local.md).

## Mục lục

**Phần A — Build production**
- [A1. Kiến trúc trên server](#a1-kiến-trúc-trên-server)
- [A2. Yêu cầu server](#a2-yêu-cầu-server)
- [A3. Đưa những file nào lên server](#a3-đưa-những-file-nào-lên-server)
- [A4. Cấu hình khác gì so với local](#a4-cấu-hình-khác-gì-so-với-local)
- [A5. Các bước triển khai](#a5-các-bước-triển-khai)
- [A6. Nhiều người dùng cùng lúc](#a6-nhiều-người-dùng-cùng-lúc)
- [A7. Nâng cấp model](#a7-nâng-cấp-model)
- [A8. Vận hành: cập nhật, sao lưu, theo dõi](#a8-vận-hành-cập-nhật-sao-lưu-theo-dõi)
- [A9. Checklist bảo mật](#a9-checklist-bảo-mật)

**Phần B — Tích hợp API**
- [B1. Mô hình tích hợp](#b1-mô-hình-tích-hợp)
- [B2. Cấp API key](#b2-cấp-api-key)
- [B3. Hệ thống ngoài cần lưu gì](#b3-hệ-thống-ngoài-cần-lưu-gì)
- [B4. Danh sách API](#b4-danh-sách-api)
- [B5. Mã lỗi](#b5-mã-lỗi)
- [B6. Ví dụ code](#b6-ví-dụ-code)
- [B7. Hiển thị trích dẫn và trang nguồn](#b7-hiển-thị-trích-dẫn-và-trang-nguồn)
- [B8. Lưu ý khi tích hợp](#b8-lưu-ý-khi-tích-hợp)

---

# Phần A — Build production

## A1. Kiến trúc trên server

```
                         ┌──────────────────────── Server (Ubuntu + GPU NVIDIA) ────────────────────────┐
Người dùng DocShelf ─┐   │                                                                              │
                     ├─► │ Nginx :443 (HTTPS) ─┬─ /          ──► Next.js :3000 ──/api/*──┐               │
Hệ thống ngoài ──────┘   │                     └─ /api/v1/*  ───────────────────────────►├► FastAPI :8000 │
 (server-to-server)      │                                                              │   (N worker)    │
                         │                                                              ▼                 │
                         │                    Postgres + pgvector (Docker, 127.0.0.1:5433)                │
                         │                    Ollama :11434 (GPU) — model trả lời + embedding             │
                         │                    /var/lib/docshelf/data — file PDF gốc                       │
                         └──────────────────────────────────────────────────────────────────────────────┘
```

Chỉ **Nginx** mở ra Internet (cổng 80/443). Next.js, FastAPI, Postgres, Ollama đều chỉ nghe ở `127.0.0.1`.

## A2. Yêu cầu server

| Thành phần | Tối thiểu | Ghi chú |
|---|---|---|
| Hệ điều hành | Ubuntu 22.04 / 24.04 | Các lệnh bên dưới viết cho Ubuntu |
| GPU | NVIDIA, cài sẵn driver (`nvidia-smi` chạy được) | Quyết định tốc độ trả lời, xem A6–A7 |
| RAM | 16GB | Mỗi worker backend nạp reranker riêng (~2–3GB nếu chạy CPU) |
| Ổ đĩa | 50GB+ | Model Ollama 3–10GB mỗi cái + PDF + database |
| Phần mềm | Docker, Python 3.12+, Node.js 20+, Ollama, Nginx | |

## A3. Đưa những file nào lên server

Cách khuyến nghị: **push code lên GitHub (repo private), rồi `git clone` trên server**. `.gitignore` đã loại sẵn những thứ không được đưa lên.

| Đưa lên (có trong git) | Không đưa lên (tạo lại trên server) |
|---|---|
| `backend/app/` — mã nguồn | `backend/.venv/` — tạo lại bằng `python -m venv` |
| `backend/alembic/`, `backend/alembic.ini` — migration | `backend/.env` — tạo mới với cấu hình production |
| `backend/requirements.txt` | `backend/data/` — thư mục PDF (có thể chép riêng nếu muốn giữ dữ liệu cũ) |
| `backend/tools/`, `backend/eval/` | `frontend/node_modules/` — `npm ci` |
| `frontend/` (trừ node_modules, .next) | `frontend/.next/` — `npm run build` |
| `docker-compose.yml`, `db/init/` | `.env` ở thư mục gốc (mật khẩu Postgres) |
| `docs/` | |

Muốn chuyển cả dữ liệu từ máy local lên: sao lưu database (`pg_dump`, xem tài liệu 01 mục 9) + nén thư mục `backend/data`, chép lên server, khôi phục.

## A4. Cấu hình khác gì so với local

**`.env` ở thư mục gốc** (cạnh `docker-compose.yml`, chỉ dùng cho Docker):

```dotenv
POSTGRES_PASSWORD=<mật khẩu mạnh, tạo bằng: openssl rand -base64 32>
```

**`backend/.env`** — những dòng khác với local:

| Biến | Local | Production | Vì sao |
|---|---|---|---|
| `DATABASE_URL` | mật khẩu `docshelf_dev_123` | mật khẩu mạnh ở trên | |
| `JWT_SECRET` | chuỗi bất kỳ ≥ 32 ký tự | chuỗi ngẫu nhiên **mới**, khác local | Lộ khóa = ai cũng giả danh được admin |
| `COOKIE_SECURE` | `false` | `true` | Cookie đăng nhập chỉ gửi qua HTTPS |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | giữ nguyên (Ollama cùng máy) | |
| `CHAT_MODEL` | `qwen3.5:4b` | model lớn hơn nếu GPU đủ (A7) | |
| `RERANK_DEVICE` | `cpu` | `cuda` nếu GPU còn VRAM | Rerank trên CPU mất ~7s/câu |
| `DATA_DIR` | `data` | `/var/lib/docshelf/data` | Đường dẫn tuyệt đối, nằm ngoài thư mục code |
| `KEEP_ALIVE` | `30m` | `-1` (giữ model trong VRAM mãi) | Không mất thời gian nạp lại model |
| `DEFAULT_MODE` | `balanced` | `balanced` | Chế độ mặc định ban đầu; sau đó admin đổi trong trang Cài đặt |
| `WARMUP` | `true` | `true` | Nạp sẵn model + tài liệu khi khởi động, người hỏi đầu tiên không phải chờ |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | 5, 10 | xem A6 | Số kết nối DB mỗi worker |

**Frontend:** biến `BACKEND_URL` (mặc định `http://localhost:8000`) phải đặt **lúc build**, vì Next.js ghi địa chỉ chuyển tiếp `/api/*` vào bản build.

## A5. Các bước triển khai

Ví dụ: tên miền `docshelf.example.edu.vn`, user Linux `deploy`, code ở `/opt/docshelf`.

### A5.1. Cài phần mềm

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git
# Node.js 20+: https://nodejs.org (hoặc nvm)
# Docker: https://docs.docker.com/engine/install/ubuntu/
sudo usermod -aG docker deploy        # đăng xuất / đăng nhập lại để có quyền dùng docker
curl -fsSL https://ollama.com/install.sh | sh
```

### A5.2. Lấy code, bật Postgres

```bash
sudo mkdir -p /opt/docshelf /var/lib/docshelf/data
sudo chown -R deploy:deploy /opt/docshelf /var/lib/docshelf
git clone https://github.com/<tài-khoản>/docshelf.git /opt/docshelf
cd /opt/docshelf

echo "POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=')" > .env
chmod 600 .env
docker compose up -d
docker compose ps        # chờ healthy
```

### A5.3. Backend

```bash
cd /opt/docshelf/backend
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

cp .env.example .env
chmod 600 .env
nano .env    # sửa theo bảng A4: DATABASE_URL (mật khẩu trong /opt/docshelf/.env), JWT_SECRET, COOKIE_SECURE=true, DATA_DIR...

ollama pull qwen3.5:4b            # hoặc model lớn hơn (A7)
ollama pull qwen3-embedding:0.6b

.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli create-user admin --role admin --name "Quản trị viên"

# chạy thử, Ctrl+C khi thấy "Application startup complete"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Chạy nền bằng **systemd** (tự khởi động lại khi lỗi hoặc khi reboot) — tạo `/etc/systemd/system/docshelf-api.service`:

```ini
[Unit]
Description=DocShelf API (FastAPI)
After=network.target docker.service ollama.service

[Service]
User=deploy
WorkingDirectory=/opt/docshelf/backend
ExecStart=/opt/docshelf/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now docshelf-api
sudo systemctl status docshelf-api
journalctl -u docshelf-api -f          # xem log
```

### A5.4. Frontend

```bash
cd /opt/docshelf/frontend
npm ci
BACKEND_URL=http://127.0.0.1:8000 npm run build
```

Tạo `/etc/systemd/system/docshelf-web.service`:

```ini
[Unit]
Description=DocShelf Web (Next.js)
After=network.target docshelf-api.service

[Service]
User=deploy
WorkingDirectory=/opt/docshelf/frontend
Environment=NODE_ENV=production
Environment=BACKEND_URL=http://127.0.0.1:8000
ExecStart=/usr/bin/npm run start -- -p 3000 -H 127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now docshelf-web
```

(Quen PM2 thì dùng `pm2 start npm --name docshelf-web -- run start -- -p 3000 -H 127.0.0.1` cũng được.)

### A5.5. Nginx + HTTPS

`/etc/nginx/sites-available/docshelf`:

```nginx
# Giới hạn tốc độ gọi API chat: tối đa 30 câu/phút mỗi IP (chống spam làm nghẽn GPU)
limit_req_zone $binary_remote_addr zone=docshelf_chat:10m rate=30r/m;

server {
    listen 80;
    server_name docshelf.example.edu.vn;

    client_max_body_size 25m;          # upload PDF tối đa 20MB + phần đầu request

    # Câu trả lời có thể mất 10–60 giây (LLM), upload + index có thể vài phút
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # API cho hệ thống ngoài: đi thẳng vào FastAPI
    location /api/v1/chat {
        limit_req zone=docshelf_chat burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
    location /api/v1/ {
        proxy_pass http://127.0.0.1:8000;
    }

    # Giao diện DocShelf (Next.js tự chuyển /api/* sang FastAPI)
    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/docshelf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Chứng chỉ HTTPS miễn phí (Let's Encrypt), tự sửa file nginx để thêm cổng 443
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d docshelf.example.edu.vn
```

Nếu tên miền đi qua **Cloudflare**: bật chế độ SSL "Full (strict)", và nâng timeout nếu câu trả lời hay vượt 100 giây (giới hạn mặc định của Cloudflare).

## A6. Nhiều người dùng cùng lúc

### Nút thắt nằm ở đâu

Mỗi câu hỏi đi qua: embed câu hỏi (GPU, ~0,1s) → BM25 (CPU, rất nhanh) → rerank (CPU ~7s / GPU <1s) → **LLM sinh câu trả lời (GPU, 5–20s)** → kiểm chứng + tìm vị trí (CPU, ~0,1s).

**GPU chạy LLM là nút thắt chính.** Các phần khác (FastAPI, Postgres, Nginx) chịu được hàng trăm request cùng lúc; GPU thì mỗi lúc chỉ sinh được vài câu trả lời. Khi đông người, các câu hỏi xếp hàng trong Ollama và người sau phải chờ người trước.

Ước lượng thông lượng:

```
số câu trả lời / phút  ≈  OLLAMA_NUM_PARALLEL × 60 / (số giây mỗi câu)
```

Ví dụ 1 câu mất 10 giây, `OLLAMA_NUM_PARALLEL=4` → khoảng 24 câu/phút. 50 người cùng bấm gửi một lúc thì người cuối chờ khoảng 2 phút. Con số thật phải đo bằng `tools/load_test.py` (cuối mục này).

### Các thông số cần chỉnh

**1. Ollama** — đặt biến môi trường cho service: `sudo systemctl edit ollama`, thêm:

```ini
[Service]
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_KEEP_ALIVE=-1"
Environment="OLLAMA_FLASH_ATTENTION=1"
```

rồi `sudo systemctl restart ollama`.

| Biến | Ý nghĩa | Gợi ý |
|---|---|---|
| `OLLAMA_NUM_PARALLEL` | Số câu một model xử lý song song | 1 (GPU 6–8GB), 2–4 (16GB), 4–8 (24GB+). **Mỗi luồng song song tốn thêm VRAM** cho bộ nhớ ngữ cảnh (`NUM_CTX`), tăng quá mức thì model tràn ra CPU và chậm hẳn |
| `OLLAMA_MAX_LOADED_MODELS` | Số model nằm sẵn trong VRAM | ≥ 2: model trả lời + model embedding, không phải nạp đi nạp lại |
| `OLLAMA_KEEP_ALIVE` | Giữ model trong VRAM bao lâu | `-1` = mãi mãi |
| `OLLAMA_FLASH_ATTENTION` | Tối ưu bộ nhớ ngữ cảnh | `1` để giảm VRAM khi chạy song song |
| `OLLAMA_MAX_QUEUE` | Số request được xếp hàng tối đa (mặc định 512) | Vượt thì Ollama báo lỗi ngay thay vì chờ |

Sau khi đổi, chạy `ollama ps`: cột PROCESSOR phải là `100% GPU`. Nếu thấy `xx% CPU` nghĩa là thiếu VRAM: giảm `OLLAMA_NUM_PARALLEL` hoặc `NUM_CTX`, hoặc dùng model nhỏ hơn.

**2. Backend (uvicorn workers)**

- Mỗi worker là một tiến trình riêng. Mỗi tiến trình có cache tài liệu riêng và **nạp reranker riêng** (2–3GB RAM nếu chạy CPU).
- Trong một worker, các API dạng `def` chạy trên threadpool (40 luồng), nên một worker đã nhận được nhiều request cùng lúc.
- Gợi ý: `--workers 2` cho server 16GB RAM, `--workers 4` cho 32GB+. Tăng worker **không** làm GPU nhanh hơn; chỉ cần đủ để không phải chờ ở tầng backend.

**3. Database**

Tổng số kết nối = số worker × (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`), phải nhỏ hơn `max_connections` của Postgres (mặc định 100). Ví dụ 4 worker × (5 + 10) = 60 → ổn.

**4. Reranker lên GPU**

Rerank trên CPU mất khoảng 7 giây mỗi câu và chiếm CPU khi đông người. Nếu GPU còn chỗ (bge-reranker-v2-m3 cần ~1–2GB VRAM), đặt `RERANK_DEVICE=cuda`. Cần PyTorch bản có CUDA: `pip install torch --index-url https://download.pytorch.org/whl/cu124` (chọn bản cu khớp driver, xem pytorch.org).

**5. Chế độ trả lời khi quá tải**

Trong trang **Cài đặt**, admin đổi chế độ mặc định sang **Nhanh** (bỏ rerank, giảm khoảng 7 giây mỗi câu khi reranker chạy CPU). Có thể tắt "Cho người dùng tự chọn chế độ" để không ai dùng chế độ Kỹ (chậm nhất) trong giờ cao điểm. Không cần khởi động lại backend. Chi tiết các chế độ: tài liệu 01, mục 8b.

### Đo tải thật

```bash
cd /opt/docshelf/backend
.venv/bin/python -m app.cli create-api-key loadtest
# upload 1 tài liệu bằng key đó (xem B4) để lấy doc_id, rồi:
.venv/bin/python -m tools.load_test --key dsk_... --doc <doc_id> --levels 1 4 8 16 32
```

Kết quả mẫu:

```
   1 người | TB    8.2s | p95    8.2s | chậm nhất    8.2s | lỗi   0 |   7.3 câu/phút
   8 người | TB   21.0s | p95   33.5s | chậm nhất   34.1s | lỗi   0 |  14.1 câu/phút
```

Tăng dần đến khi **p95** vượt mức chấp nhận được (vd 30 giây). Mức đó chính là số người hỏi cùng lúc tối đa với cấu hình hiện tại. Đo xong thì thu hồi key: `python -m app.cli revoke-api-key loadtest`.

### Khi Ollama không còn đủ

Ollama tiện nhưng không tối ưu cho hàng chục câu hỏi song song. Bước tiếp theo là **vLLM**, có cơ chế continuous batching cho thông lượng cao hơn nhiều trên cùng GPU. DocShelf hiện gọi model qua thư viện `ollama` (`app/llm.py`, `app/embedder.py`). Chuyển sang vLLM cần viết lại 2 file này để gọi API dạng OpenAI; phần còn lại giữ nguyên.

## A7. Nâng cấp model

### VRAM ước lượng (bản lượng tử hóa mặc định của Ollama, `NUM_CTX=8192`, 1 luồng)

| Model | VRAM khoảng | Ghi chú |
|---|---|---|
| `qwen3-embedding:0.6b` | ~2GB | Đang dùng |
| `qwen3-embedding:4b` | ~3–4GB | Vector 2560 chiều |
| `qwen3-embedding:8b` | ~5–6GB | |
| `qwen3.5:4b` | ~3,3GB | Đang dùng |
| Model trả lời ~9B | ~6–7GB | |
| bge-reranker-v2-m3 (GPU) | ~1–2GB | Khi `RERANK_DEVICE=cuda` |

Đây là số **ước lượng**: số thật xem bằng `ollama ps` sau khi nạp. Mỗi luồng song song (`OLLAMA_NUM_PARALLEL`) cộng thêm bộ nhớ ngữ cảnh. Tên chính xác các bản model: https://ollama.com/library

Gợi ý theo GPU:

| GPU | Cấu hình hợp lý |
|---|---|
| 6–8GB (laptop hiện tại) | 4B + embedding 0.6b, reranker CPU, `NUM_PARALLEL=1` |
| 16GB | ~9B + embedding 0.6b + reranker GPU, `NUM_PARALLEL=2` |
| 24GB trở lên | ~9B + embedding 4b + reranker GPU, `NUM_PARALLEL=4` |

### Đổi model trả lời (vd 4B → 9B)

```bash
ollama pull <tên-model-9b>
nano /opt/docshelf/backend/.env           # CHAT_MODEL=<tên-model-9b>
sudo systemctl restart docshelf-api
```

Không cần làm gì với dữ liệu. Có thể cho người dùng chọn giữa 4B và 9B trong giao diện ở phiên bản sau.

### Đổi model embedding (vd 0.6b → 4b)

Vector cũ không so được với vector mới, nên **phải index lại**:

```bash
ollama pull qwen3-embedding:4b
nano /opt/docshelf/backend/.env           # EMBED_MODEL=qwen3-embedding:4b
cd /opt/docshelf/backend
.venv/bin/python -m app.cli reindex --all  # đọc đoạn văn từ DB, embed lại, không cần PDF
sudo systemctl restart docshelf-api
```

Trong lúc chưa reindex, chat trên tài liệu cũ trả lỗi 409 (không trả lời sai). Nên làm vào giờ vắng người.

### Luôn đo lại sau khi đổi

```bash
.venv/bin/python -m eval.run_bench --pdf sample.pdf
```

So với báo cáo cũ trong `eval/reports/`. Model lớn hơn **không chắc** tốt hơn cho từng loại câu hỏi. Benchmark trả lời được câu hỏi đó, tránh nâng cấp theo cảm tính.

## A8. Vận hành: cập nhật, sao lưu, theo dõi

**Cập nhật phiên bản mới:**

```bash
cd /opt/docshelf
git pull
cd backend
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head            # nếu có thay đổi bảng
sudo systemctl restart docshelf-api
cd ../frontend
npm ci && BACKEND_URL=http://127.0.0.1:8000 npm run build
sudo systemctl restart docshelf-web
```

**Sao lưu hằng ngày** — `crontab -e`:

```cron
# 2h sáng: dump database + nén thư mục PDF, giữ 14 ngày
0 2 * * * docker exec docshelf-db pg_dump -U docshelf -Fc docshelf > /backup/docshelf_$(date +\%F).dump && tar czf /backup/docshelf_data_$(date +\%F).tgz -C /var/lib/docshelf data && find /backup -name 'docshelf_*' -mtime +14 -delete
```

(Trên Linux dùng `>` được; vấn đề hỏng file nhị phân chỉ có ở PowerShell.)

**Theo dõi:**

| Việc | Lệnh |
|---|---|
| Backend còn sống | `curl -s http://127.0.0.1:8000/api/health` |
| Log backend | `journalctl -u docshelf-api -f` |
| Model đang nạp, % GPU | `ollama ps` |
| GPU | `nvidia-smi` |
| Hệ thống ngoài nào đang dùng | `.venv/bin/python -m app.cli list-api-keys` |

## A9. Checklist bảo mật

- [ ] `JWT_SECRET`, `POSTGRES_PASSWORD` mới, mạnh, khác local; file `.env` quyền `600`
- [ ] `COOKIE_SECURE=true` và chạy HTTPS
- [ ] Postgres chỉ nghe `127.0.0.1` (compose đã cấu hình), Ollama không mở ra ngoài (mặc định nghe `127.0.0.1:11434`)
- [ ] Firewall chỉ mở 22, 80, 443: `sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable`
- [ ] Đổi mật khẩu admin mặc định nếu đã dùng mật khẩu thử
- [ ] API key chỉ nằm ở **backend** của hệ thống ngoài, không bao giờ ở frontend / trình duyệt
- [ ] Có sao lưu tự động và đã thử khôi phục ít nhất 1 lần
- [ ] Trang tài liệu API tự sinh `/docs` của FastAPI: Nginx ở trên không chuyển `/docs` sang backend nên không lộ ra ngoài; giữ nguyên như vậy

---

# Phần B — Tích hợp API vào hệ thống khác

## B1. Mô hình tích hợp

Tình huống: hệ thống X (vd hệ thống quản lý đào tạo) có frontend riêng. Người dùng X upload file trên giao diện của X, sau đó bấm vào file để chat. DocShelf chỉ đóng vai trò "bộ não" phía sau.

```
Trình duyệt người dùng X          Backend hệ thống X                         DocShelf
        │                                │                                       │
 1. upload file ───────────────────────► │ ── POST /api/v1/documents ──────────► │ đọc, cắt đoạn, embed
        │                                │ ◄── { doc_id, title, num_pages } ──── │
        │                                │ lưu (file_id ↔ doc_id) vào DB của X   │
        │                                │                                       │
 2. bấm vào file, hỏi ─────────────────► │ ── POST /api/v1/chat ───────────────► │ chỉ tìm trong doc_id đó
        │                                │    { doc_id, question,                │
        │                                │      session_id?, user_ref }          │
        │ ◄── câu trả lời + trích dẫn ── │ ◄── { answer, citations, session_id } │
        │                                │ lưu session_id để hỏi tiếp            │
```

Hai nguyên tắc:

1. **Gọi server-to-server.** Frontend của X gọi backend của X; backend của X gắn API key và gọi DocShelf. API key không bao giờ xuất hiện trong trình duyệt (ai mở DevTools cũng đọc được). DocShelf cố ý không bật CORS cho `/api/v1`.
2. **Mỗi hệ thống một "kệ" riêng.** Tài liệu upload bằng key của X chỉ X thấy được; hệ thống Y, và cả giao diện DocShelf nội bộ, đều không thấy. Gửi `doc_id` của hệ thống khác sẽ nhận 404.

## B2. Cấp API key

Trên server DocShelf:

```bash
cd /opt/docshelf/backend
.venv/bin/python -m app.cli create-api-key he-thong-dao-tao
```

```
Đã tạo API key cho 'he-thong-dao-tao'. Key chỉ hiện MỘT LẦN, hãy lưu lại ngay:

    dsk_ZKpfHLFh...

Hệ thống ngoài gửi kèm header:  X-API-Key: <key>
```

DocShelf chỉ lưu mã băm (sha256) của key nên không xem lại được key gốc. Mất key thì thu hồi và cấp key mới:

```bash
.venv/bin/python -m app.cli list-api-keys                    # xem các hệ thống, số tài liệu, lần dùng cuối
.venv/bin/python -m app.cli revoke-api-key he-thong-dao-tao   # thu hồi (tài liệu vẫn giữ)
```

Hệ thống X lưu key trong biến môi trường / file cấu hình của **backend X**, ví dụ `DOCSHELF_API_KEY=dsk_...`.

## B3. Hệ thống ngoài cần lưu gì

Tối thiểu chỉ cần lưu `doc_id` gắn với file của họ. Gợi ý bảng bên hệ thống X:

```sql
-- File người dùng X đã upload, gắn với tài liệu bên DocShelf
CREATE TABLE docshelf_documents (
    file_id        BIGINT PRIMARY KEY REFERENCES files(id),  -- khóa của X
    doc_id         CHAR(32) NOT NULL UNIQUE,                 -- trả về từ POST /api/v1/documents
    num_pages      INT,
    created_at     TIMESTAMPTZ DEFAULT now()
);

-- (Tùy chọn) cuộc trò chuyện: để người dùng mở lại lịch sử hoặc hỏi tiếp
CREATE TABLE docshelf_sessions (
    session_id     CHAR(32) PRIMARY KEY,                     -- trả về từ POST /api/v1/chat
    user_id        BIGINT NOT NULL REFERENCES users(id),     -- người dùng của X
    file_id        BIGINT NOT NULL REFERENCES files(id),
    title          TEXT,                                     -- câu hỏi đầu tiên
    updated_at     TIMESTAMPTZ DEFAULT now()
);
```

Không cần lưu nội dung tin nhắn: DocShelf đã lưu, lấy lại bằng `GET /api/v1/sessions/{session_id}/messages`. Nếu X muốn tự lưu lịch sử thì cũng được.

## B4. Danh sách API

Mọi request gửi kèm header `X-API-Key: dsk_...`. Địa chỉ gốc: `https://docshelf.example.edu.vn`.

| Phương thức | Đường dẫn | Việc |
|---|---|---|
| POST | `/api/v1/documents` | Upload PDF → `doc_id` |
| GET | `/api/v1/documents` | Danh sách tài liệu của hệ thống mình |
| GET | `/api/v1/documents/{doc_id}` | Thông tin một tài liệu |
| DELETE | `/api/v1/documents/{doc_id}` | Xóa tài liệu + mọi cuộc trò chuyện về nó |
| GET | `/api/v1/documents/{doc_id}/pages/{page}/image` | Ảnh PNG một trang (hiện trang nguồn) |
| POST | `/api/v1/chat` | Hỏi đáp trên một tài liệu |
| GET | `/api/v1/sessions?doc_id=&user_ref=` | Danh sách cuộc trò chuyện |
| GET | `/api/v1/sessions/{session_id}/messages?user_ref=` | Toàn bộ tin nhắn của một cuộc |
| DELETE | `/api/v1/sessions/{session_id}?user_ref=` | Xóa một cuộc trò chuyện |

### POST /api/v1/documents — upload

`multipart/form-data`:

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `file` | ✅ | File PDF, tối đa 20MB, PDF có chữ (bản scan cần OCR trước) |
| `title` | | Tên hiển thị; bỏ trống thì lấy tên file |

```bash
curl -X POST https://docshelf.example.edu.vn/api/v1/documents \
  -H "X-API-Key: $DOCSHELF_API_KEY" \
  -F "file=@giao-trinh-hoc-may.pdf" \
  -F "title=Giáo trình Học máy"
```

Response `201 Created`:

```json
{
    "doc_id": "33b6b532e7424580968c3d95c8c7b310",
    "title": "Giáo trình Học máy",
    "filename": "giao-trinh-hoc-may.pdf",
    "num_pages": 3,
    "num_chunks": 1,
    "embed_model": "qwen3-embedding:0.6b",
    "created_at": "2026-10-08T23:46:15.891372+07:00",
    "duplicate": false
}
```

→ **Lưu `doc_id`.** Đây là thứ duy nhất bắt buộc phải nhớ.

Gửi lại **đúng file đã upload** (cùng nội dung) sẽ nhận `200 OK` với `"duplicate": true` và **`doc_id` cũ**, không index lại. Gửi lại sau lỗi mạng vì thế an toàn, không tạo bản trùng.

Upload là **đồng bộ**: request chỉ trả về khi đã index xong. File dài có thể mất 1–3 phút, nên đặt timeout phía X ≥ 300 giây.

### POST /api/v1/chat — hỏi đáp

```json
{
    "doc_id": "33b6b532e7424580968c3d95c8c7b310",
    "question": "Hàm sigmoid còn được gọi là gì?",
    "session_id": null,
    "user_ref": "sv-2051001",
    "mode": null,
    "include_debug": false
}
```

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `doc_id` | ✅ | Tài liệu cần hỏi. Câu trả lời **chỉ** dựa trên tài liệu này |
| `question` | ✅ | 1–2000 ký tự |
| `session_id` | | `null` = bắt đầu cuộc trò chuyện mới. Gửi lại `session_id` nhận được để hỏi tiếp (hệ thống hiểu "nó", "còn cái kia thì sao"...) |
| `user_ref` | | Mã người dùng bên X. Cuộc trò chuyện tạo với `user_ref` nào thì chỉ mở tiếp được với đúng `user_ref` đó, để người dùng X không đọc được lịch sử của nhau |
| `mode` | | `"fast"` / `"balanced"` / `"accurate"` (Nhanh / Cân bằng / Kỹ, xem tài liệu 01 mục 8b). `null` = chế độ mặc định do admin DocShelf đặt. Admin tắt "Cho người dùng tự chọn chế độ" thì giá trị này bị bỏ qua |
| `include_debug` | | `true`: thêm thông tin chẩn đoán (các bước đã chạy / bỏ qua, điểm tìm kiếm, thời gian từng bước) |

Response `200 OK`:

```json
{
    "session_id": "5599632af53342dca1fa1d6ad35fb52e",
    "doc_id": "33b6b532e7424580968c3d95c8c7b310",
    "answer": "Hàm sigmoid còn được gọi là hàm logistic, thường dùng trong hồi quy logistic để đưa đầu ra về khoảng (0, 1).",
    "found": true,
    "refusal_kind": null,
    "mode": "balanced",
    "citations": [
        {
            "quote": "Ham sigmoid con duoc goi la ham logistic loai 1",
            "page": 2,
            "section": "Giáo trình Học máy > CHUONG 2",
            "rects": [[0.195, 0.1166, 0.5844, 0.1345]]
        }
    ]
}
```

| Trường | Ý nghĩa |
|---|---|
| `session_id` | Lưu lại để hỏi tiếp trong cùng cuộc trò chuyện |
| `answer` | Câu trả lời (văn bản thường, có thể có xuống dòng và dấu •) |
| `found` | `true` = trả lời được và trích dẫn đã kiểm chứng. `false` = từ chối, `answer` giải thích lý do |
| `mode` | Chế độ thực tế đã dùng để trả lời |
| `refusal_kind` | Khi `found = false`: `not_in_doc` (tài liệu không có), `unsure` (có mục liên quan nhưng không chắc), `unverified` (không kiểm chứng được trích dẫn), `figure` (thông tin nằm trong hình), `chitchat` (câu chào hỏi, không phải câu hỏi) |
| `citations[].quote` | Câu trích **nguyên văn** từ tài liệu |
| `citations[].page` | Số trang (bắt đầu từ 1) |
| `citations[].section` | Mục / chương chứa câu trích |
| `citations[].rects` | Vùng cần tô trên ảnh trang `[x0, y0, x1, y1]`, tỉ lệ 0..1 so với chiều rộng/cao trang (xem B7) |

Thời gian trả lời: 5–30 giây tùy model và mức tải (xem A6). Đặt timeout phía X ≥ 120 giây.

### GET /api/v1/sessions/{session_id}/messages

```json
{
    "session_id": "5599632af53342dca1fa1d6ad35fb52e",
    "doc_id": "33b6b532e7424580968c3d95c8c7b310",
    "messages": [
        {"role": "user", "content": "Hàm sigmoid còn gọi là gì?", "created_at": "..."},
        {"role": "assistant", "content": "Hàm sigmoid còn được gọi là...", "created_at": "...",
         "found": true, "citations": [ ... ]}
    ]
}
```

Cuộc trò chuyện tạo với `user_ref` thì phải gửi kèm `?user_ref=...` giống hệt.

### Các API còn lại

- `GET /api/v1/documents?limit=100&offset=0` → mảng tài liệu (cùng dạng với response upload).
- `DELETE /api/v1/documents/{doc_id}` → `{"ok": true}`. Xóa cả file PDF, đoạn văn, vector, mọi cuộc trò chuyện. **Không khôi phục được.**
- `GET /api/v1/documents/{doc_id}/pages/{page}/image` → ảnh PNG của trang.
- `GET /api/v1/sessions?doc_id=...&user_ref=...` → `[{session_id, doc_id, user_ref, title, updated_at}]`, mới nhất trước, tối đa 100.

## B5. Mã lỗi

Lỗi trả về dạng `{"detail": "thông báo tiếng Việt"}`.

| Mã | Khi nào | Bên X nên làm |
|---|---|---|
| 400 | Dữ liệu sai: không phải PDF, câu hỏi trống, `session_id` thuộc tài liệu khác | Báo lại người dùng |
| 401 | Thiếu / sai API key, key đã bị thu hồi | Kiểm tra cấu hình key |
| 404 | `doc_id` / `session_id` không tồn tại, của hệ thống khác, hoặc sai `user_ref` | Xóa liên kết cũ bên X nếu tài liệu đã bị xóa |
| 409 | DocShelf vừa đổi model embedding, tài liệu chưa index lại | Báo quản trị DocShelf chạy `reindex` |
| 413 | File > 20MB | Báo người dùng |
| 422 | PDF không trích được chữ (bản scan) hoặc thiếu trường bắt buộc | Báo người dùng cần PDF có chữ / OCR |
| 429 | Gọi chat quá nhanh (giới hạn ở Nginx, A5.5) | Chờ rồi gửi lại |
| 503 | Model AI (Ollama) không chạy | Thử lại sau, báo quản trị DocShelf |
| 502 / 504 | Quá tải / quá thời gian chờ | Thử lại sau |

## B6. Ví dụ code

### Python (backend của X — FastAPI / Django / Flask đều tương tự)

```python
import os
import requests

DOCSHELF_URL = os.environ["DOCSHELF_URL"]          # https://docshelf.example.edu.vn
HEADERS = {"X-API-Key": os.environ["DOCSHELF_API_KEY"]}


def docshelf_upload(path: str, title: str | None = None) -> dict:
    with open(path, "rb") as f:
        r = requests.post(
            f"{DOCSHELF_URL}/api/v1/documents",
            headers=HEADERS,
            files={"file": (os.path.basename(path), f, "application/pdf")},
            data={"title": title} if title else None,
            timeout=300,                            # index có thể mất vài phút
        )
    r.raise_for_status()
    return r.json()                                 # -> lưu r.json()["doc_id"] vào DB của X


def docshelf_chat(doc_id: str, question: str, user_id: int, session_id: str | None = None) -> dict:
    r = requests.post(
        f"{DOCSHELF_URL}/api/v1/chat",
        headers=HEADERS,
        json={"doc_id": doc_id, "question": question, "session_id": session_id, "user_ref": str(user_id)},
        timeout=180,
    )
    r.raise_for_status()
    return r.json()                                 # -> lưu session_id để hỏi tiếp
```

### Node.js (backend của X dùng Express) — làm "cầu nối" cho frontend

```js
// Frontend X gọi /api/files/:fileId/chat của chính X; X tra doc_id rồi gọi DocShelf.
app.post("/api/files/:fileId/chat", requireLogin, async (req, res) => {
  const { docId } = await db.docshelfDocuments.findByFileId(req.params.fileId); // doc_id đã lưu lúc upload
  const r = await fetch(`${process.env.DOCSHELF_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "X-API-Key": process.env.DOCSHELF_API_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({
      doc_id: docId,
      question: req.body.question,
      session_id: req.body.sessionId ?? null,
      user_ref: String(req.user.id),
    }),
    signal: AbortSignal.timeout(180_000),
  });
  const data = await r.json();
  if (!r.ok) return res.status(r.status).json(data);
  res.json(data); // { session_id, answer, found, citations, ... }
});

// Ảnh trang nguồn: X chuyển tiếp, gắn API key ở phía server
app.get("/api/files/:fileId/pages/:page", requireLogin, async (req, res) => {
  const { docId } = await db.docshelfDocuments.findByFileId(req.params.fileId);
  const r = await fetch(`${process.env.DOCSHELF_URL}/api/v1/documents/${docId}/pages/${Number(req.params.page)}/image`, {
    headers: { "X-API-Key": process.env.DOCSHELF_API_KEY },
  });
  if (!r.ok) return res.sendStatus(r.status);
  res.set("Content-Type", "image/png").set("Cache-Control", "private, max-age=86400");
  res.send(Buffer.from(await r.arrayBuffer()));
});
```

### Frontend của X (React) — chỉ gọi backend của X

```tsx
const [sessionId, setSessionId] = useState<string | null>(null);

async function ask(question: string) {
  const r = await fetch(`/api/files/${fileId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, sessionId }),
  });
  const data = await r.json();
  setSessionId(data.session_id);   // câu sau gửi kèm để hỏi tiếp
  // hiển thị data.answer, data.citations
}
```

## B7. Hiển thị trích dẫn và trang nguồn

Mỗi trích dẫn có `page` và `rects`. Hiện ảnh trang rồi phủ các khung tô vàng lên đúng vị trí. `rects` tính theo tỉ lệ nên ảnh hiển thị to nhỏ cỡ nào cũng khớp:

```tsx
<div style={{ position: "relative" }}>
  <img src={`/api/files/${fileId}/pages/${c.page}`} style={{ width: "100%", display: "block" }} />
  {c.rects.map(([x0, y0, x1, y1], i) => (
    <div key={i} style={{
      position: "absolute",
      left: `${x0 * 100}%`, top: `${y0 * 100}%`,
      width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%`,
      background: "rgba(253, 224, 71, 0.4)",
    }} />
  ))}
</div>
```

`rects` rỗng nghĩa là không xác định được vị trí chính xác: vẫn hiện trang `page`, chỉ không tô. Có thể xem cách giao diện DocShelf làm trong `frontend/components/SourcePanel.tsx`.

## B8. Lưu ý khi tích hợp

- **Một `doc_id` = một tài liệu.** Muốn hỏi trên nhiều file cùng lúc thì hiện chưa hỗ trợ; mỗi cuộc trò chuyện gắn với đúng một tài liệu.
- **Không gọi từ trình duyệt.** Lặp lại vì quan trọng: lộ API key là lộ toàn bộ tài liệu của hệ thống X.
- **Luôn gửi `user_ref`** nếu X có nhiều người dùng, để tách lịch sử trò chuyện giữa họ.
- **Xử lý `found = false`** như một câu trả lời bình thường (hiện `answer`), không coi là lỗi. Đó là lúc hệ thống từ chối thay vì bịa.
- **Upload trùng an toàn:** gửi lại cùng file nhận về `doc_id` cũ.
- **Xóa file bên X** thì nên gọi `DELETE /api/v1/documents/{doc_id}` để dọn dữ liệu bên DocShelf.
- **Timeout:** upload ≥ 300s, chat ≥ 120s (có thể lâu hơn khi đông người, xem A6).
- **Môi trường thử:** xin một key riêng cho môi trường test của X (vd `he-thong-dao-tao-test`), không dùng chung key với production.

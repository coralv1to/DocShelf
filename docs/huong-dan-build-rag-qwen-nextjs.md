# Hướng dẫn build hệ thống hỏi đáp tài liệu (RAG) với Qwen + Next.js

> Mục tiêu: upload một file PDF, đặt câu hỏi, hệ thống **chỉ trả lời dựa trên nội dung file**, kèm trích dẫn và số trang. Câu hỏi không liên quan hoặc file không có thông tin thì **từ chối, không bịa**. Hiểu được câu hỏi tiếp nối trong hội thoại.
>
> Máy mục tiêu: ThinkPad P1 Gen 6, i7-13800H, 32GB RAM, RTX A1000 6GB, Windows.

---

## Mục lục

- [Phần 0. Bức tranh tổng thể](#phần-0-bức-tranh-tổng-thể)
- [Phần 1. Chuẩn bị môi trường](#phần-1-chuẩn-bị-môi-trường)
- [Phần 2. Khung backend và kết nối model](#phần-2-khung-backend-và-kết-nối-model)
- [Phần 3. Indexing: PDF → đoạn văn → vector](#phần-3-indexing-pdf--đoạn-văn--vector)
- [Phần 4. Hỏi đáp: tìm kiếm, sinh câu trả lời, kiểm chứng](#phần-4-hỏi-đáp-tìm-kiếm-sinh-câu-trả-lời-kiểm-chứng)
- [Phần 5. API với FastAPI](#phần-5-api-với-fastapi)
- [Phần 6. Frontend Next.js](#phần-6-frontend-nextjs)
- [Phần 7. Nâng cấp tìm kiếm: BM25 + RRF + Rerank](#phần-7-nâng-cấp-tìm-kiếm-bm25--rrf--rerank)
- [Phần 8. Hiểu hội thoại: viết lại câu hỏi](#phần-8-hiểu-hội-thoại-viết-lại-câu-hỏi)
- [Phần 9. Đánh giá chất lượng](#phần-9-đánh-giá-chất-lượng)
- [Phần 10. Demo qua ngrok](#phần-10-demo-qua-ngrok)
- [Phần 11. Bước tiếp theo](#phần-11-bước-tiếp-theo)
- [Phụ lục A. Lỗi thường gặp](#phụ-lục-a-lỗi-thường-gặp)
- [Phụ lục B. Thuật ngữ](#phụ-lục-b-thuật-ngữ)

---

## Phần 0. Bức tranh tổng thể

### 0.1. Kiến trúc

```
Trình duyệt (người dùng / người xem demo)
        │
        ▼
Next.js (cổng 3000)  ── rewrites /api/* ──▶  FastAPI (cổng 8000, chỉ trong máy)
                                                   │
                         ┌─────────────────────────┼──────────────────────┐
                         ▼                         ▼                      ▼
                  Ollama (cổng 11434)       File index (data/)      Reranker (CPU)
                  - qwen3.5:4b  (chat)      - chunks + vector       bge-reranker-v2-m3
                  - qwen3-embedding:0.6b
```

- **Next.js** chỉ lo giao diện. Mọi request `/api/...` được Next.js chuyển tiếp sang FastAPI, vì vậy trình duyệt **không bao giờ gọi thẳng** FastAPI hay Ollama. Khi demo qua ngrok, bạn chỉ expose cổng 3000.
- **FastAPI (Python)** chứa toàn bộ logic AI. Python được chọn vì hệ sinh thái xử lý PDF, NLP tiếng Việt và reranker đều mạnh nhất ở đây.
- **Ollama** chạy hai model: một model chat để trả lời, một embedding model để biến văn bản thành vector.

### 0.2. Pipeline sẽ xây

```
INDEXING (khi upload, chạy một lần):
PDF → trích text + làm sạch → cắt đoạn theo Chương/Điều → gắn tiêu đề ngữ cảnh
    → embedding → lưu vector (+ BM25 tạo khi cần)

QUERY (mỗi câu hỏi):
Câu hỏi → [viết lại nếu có lịch sử] → vector search (+ BM25 → RRF)
       → [rerank] → điểm thấp? → TỪ CHỐI
       → prompt nghiêm ngặt → LLM trả JSON + trích dẫn
       → code kiểm chứng trích dẫn có thật? → không → TỪ CHỐI
       → trả lời + số trang
```

### 0.3. Chiến lược làm

Làm **phiên bản tối thiểu chạy được trước** (Phần 2–6), rồi bật dần từng nâng cấp (Phần 7–8) và **đo** sau mỗi lần bật (Phần 9). Các nâng cấp được điều khiển bằng cờ trong file `.env`:

| Cờ | Bật ở phần | Tác dụng |
|---|---|---|
| `USE_BM25` | 7 | Thêm tìm kiếm từ khóa, gộp với vector bằng RRF |
| `USE_RERANK` | 7 | Chấm lại độ liên quan bằng reranker |
| `USE_REWRITE` | 8 | Viết lại câu hỏi tiếp nối thành câu đầy đủ |

Nhờ có cờ, bạn so sánh được bật và tắt từng kỹ thuật trên cùng bộ câu hỏi. Đây chính là cách học xem kỹ thuật nào thực sự có ích.

### 0.4. Cấu trúc thư mục cuối cùng

```
doc-qa/
├── backend/
│   ├── .env
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py        # đọc cấu hình từ .env
│   │   ├── llm.py           # gọi chat model
│   │   ├── embedder.py      # gọi embedding model
│   │   ├── pdf_parser.py    # trích + làm sạch text
│   │   ├── chunker.py       # cắt đoạn theo cấu trúc
│   │   ├── store.py         # lưu/tải index, vector search
│   │   ├── bm25.py          # tìm theo từ khóa + RRF (Phần 7)
│   │   ├── reranker.py      # rerank (Phần 7)
│   │   ├── prompts.py       # toàn bộ prompt + JSON schema
│   │   ├── verify.py        # kiểm chứng trích dẫn
│   │   ├── memory.py        # lịch sử hội thoại
│   │   ├── pipeline.py      # ghép tất cả thành luồng xử lý
│   │   └── main.py          # API FastAPI
│   ├── eval/
│   │   ├── questions.json
│   │   └── run_eval.py
│   └── data/                # index của các file đã upload (tự tạo)
└── frontend/                # Next.js
```

---

## Phần 1. Chuẩn bị môi trường

### 1.1. Cài Ollama và tải model

1. Tải bộ cài Windows tại `https://ollama.com/download` và cài đặt.
2. Đặt biến môi trường cho Ollama: **Settings → System → About → Advanced system settings → Environment Variables → User variables → New**:

   | Biến | Giá trị | Ý nghĩa |
   |---|---|---|
   | `OLLAMA_KEEP_ALIVE` | `30m` | Giữ model trong VRAM 30 phút sau lần dùng cuối, tránh phải nạp lại (nạp lại mất vài giây đến vài chục giây) |
   | `OLLAMA_NUM_PARALLEL` | `2` | Cho phép 2 request chạy song song. Tăng lên 3 khi demo nhiều người (Phần 10) |

   Sau khi đặt biến, **thoát hẳn Ollama** (chuột phải icon ở khay hệ thống → Quit) rồi mở lại để biến có hiệu lực.

3. Mở PowerShell và tải model:

   ```powershell
   ollama pull qwen3.5:4b
   ollama pull qwen3-embedding:0.6b
   ollama list
   ```

   > Tên tag có thể thay đổi theo thời gian. Nếu `pull` báo không tìm thấy, vào `https://ollama.com/library` tìm "qwen3.5" và "qwen3-embedding" để lấy tag đúng, sau đó sửa tương ứng trong `.env` ở Phần 2.

4. Kiểm tra model chat:

   ```powershell
   ollama run qwen3.5:4b --verbose
   ```

   Gõ thử một câu tiếng Việt. Ghi lại `eval rate` (token/giây). Thoát bằng `/bye`. Sau đó chạy:

   ```powershell
   ollama ps
   ```

   Cột PROCESSOR phải là `100% GPU`.

### 1.2. Cài Python

- Dùng **Python 3.11 hoặc 3.12** (một số thư viện NLP và torch chưa hỗ trợ tốt các phiên bản quá mới).
- Kiểm tra: `python --version`.

### 1.3. Cài Node.js

- Dùng Node.js bản LTS. Kiểm tra: `node --version` và `npm --version`.

### 1.4. Tạo thư mục project

```powershell
mkdir doc-qa
cd doc-qa
mkdir backend
```

---

## Phần 2. Khung backend và kết nối model

### 2.1. Môi trường ảo Python

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
```

**Vì sao cần venv:** mỗi project có bộ thư viện riêng, không đụng nhau và không làm bẩn Python hệ thống. Sau khi `activate`, đầu dòng lệnh có `(.venv)`. **Mỗi lần mở terminal mới để chạy backend đều phải activate lại.**

> Nếu PowerShell báo lỗi "running scripts is disabled", chạy một lần: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 2.2. Cài thư viện

Tạo file `backend/requirements.txt`:

```text
fastapi
uvicorn[standard]
python-multipart
python-dotenv
ollama
pymupdf
numpy
rapidfuzz
rank-bm25
underthesea
sentence-transformers
```

Ý nghĩa từng thư viện:

| Thư viện | Dùng để |
|---|---|
| `fastapi`, `uvicorn` | Viết và chạy API |
| `python-multipart` | Cho phép FastAPI nhận file upload |
| `python-dotenv` | Đọc file `.env` |
| `ollama` | Gọi Ollama từ Python |
| `pymupdf` | Trích text từ PDF (import với tên `fitz`) |
| `numpy` | Tính toán vector |
| `rapidfuzz` | So khớp chuỗi gần đúng khi kiểm chứng trích dẫn |
| `rank-bm25` | Tìm kiếm theo từ khóa (Phần 7) |
| `underthesea` | Tách từ tiếng Việt cho BM25 (Phần 7) |
| `sentence-transformers` | Chạy reranker (Phần 7). Tự cài kèm `torch` |

```powershell
pip install -r requirements.txt
```

Lần cài đầu sẽ hơi lâu vì `torch` khá nặng. Bản `torch` mặc định trên Windows chạy CPU, và như vậy là **đúng ý** vì ta sẽ cho reranker chạy CPU để nhường VRAM cho Ollama (giải thích ở Phần 7).

### 2.3. File cấu hình `.env`

Tạo `backend/.env`:

```ini
# --- Model ---
OLLAMA_HOST=http://localhost:11434
CHAT_MODEL=qwen3.5:4b
EMBED_MODEL=qwen3-embedding:0.6b
RERANK_MODEL=BAAI/bge-reranker-v2-m3
RERANK_DEVICE=cpu
NUM_CTX=8192
THINK=false

# --- Cắt đoạn ---
CHUNK_WORDS=350
CHUNK_OVERLAP_WORDS=40

# --- Tìm kiếm ---
TOP_K_RETRIEVE=20
TOP_K_CONTEXT=4
MIN_VECTOR_SCORE=0.45
MIN_RERANK_SCORE=0.30

# --- Hội thoại ---
HISTORY_TURNS=3

# --- Cờ nâng cấp (bật dần ở Phần 7, 8) ---
USE_BM25=false
USE_RERANK=false
USE_REWRITE=false

DATA_DIR=data
```

**Vì sao để cấu hình trong `.env`:** khi chuyển từ laptop sang server (Ollama sang vLLM, model 4B sang 27B), bạn chỉ sửa file này, **không sửa code**.

Các con số `MIN_VECTOR_SCORE` và `MIN_RERANK_SCORE` chỉ là điểm khởi đầu. Bạn sẽ chỉnh lại chúng bằng số liệu đo được ở Phần 9.

### 2.4. `app/__init__.py` và `app/config.py`

Tạo thư mục `backend/app/` và file rỗng `backend/app/__init__.py`. File rỗng này biến thư mục `app` thành một **package** Python, nhờ đó các file bên trong import lẫn nhau được bằng `from . import ...`.

`backend/app/config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()  # đọc file .env vào biến môi trường


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


# Model
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3.5:4b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6b")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_DEVICE = os.getenv("RERANK_DEVICE", "cpu")
NUM_CTX = _int("NUM_CTX", 8192)
THINK = _bool("THINK", False)

# Cắt đoạn
CHUNK_WORDS = _int("CHUNK_WORDS", 350)
CHUNK_OVERLAP_WORDS = _int("CHUNK_OVERLAP_WORDS", 40)

# Tìm kiếm
TOP_K_RETRIEVE = _int("TOP_K_RETRIEVE", 20)
TOP_K_CONTEXT = _int("TOP_K_CONTEXT", 4)
MIN_VECTOR_SCORE = _float("MIN_VECTOR_SCORE", 0.45)
MIN_RERANK_SCORE = _float("MIN_RERANK_SCORE", 0.30)

# Hội thoại
HISTORY_TURNS = _int("HISTORY_TURNS", 3)

# Cờ nâng cấp
USE_BM25 = _bool("USE_BM25", False)
USE_RERANK = _bool("USE_RERANK", False)
USE_REWRITE = _bool("USE_REWRITE", False)

DATA_DIR = os.getenv("DATA_DIR", "data")
```

**Giải thích:**
- Biến môi trường luôn là chuỗi, nên các hàm `_bool`, `_int`, `_float` chuyển chúng về đúng kiểu dữ liệu.
- `os.getenv("TÊN", mặc_định)`: nếu `.env` thiếu một biến thì dùng giá trị mặc định, chương trình không bị lỗi.

### 2.5. `app/llm.py`: gọi chat model

```python
import json
from ollama import Client

from . import config

_client = Client(host=config.OLLAMA_HOST)


def chat(messages: list[dict], json_schema: dict | None = None, temperature: float = 0.0) -> str:
    """Gửi danh sách messages cho chat model, trả về nội dung văn bản."""
    kwargs = {
        "model": config.CHAT_MODEL,
        "messages": messages,
        "options": {"temperature": temperature, "num_ctx": config.NUM_CTX},
        "think": config.THINK,
    }
    if json_schema is not None:
        kwargs["format"] = json_schema
    resp = _client.chat(**kwargs)
    return resp.message.content or ""


def chat_json(messages: list[dict], json_schema: dict) -> dict | None:
    """Như chat(), nhưng ép output theo JSON schema và parse thành dict."""
    raw = chat(messages, json_schema=json_schema)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
```

**Giải thích:**
- **`messages`**: danh sách hội thoại theo chuẩn chung (`system`, `user`, `assistant`), đã giới thiệu ở phần lý thuyết. Model không nhớ gì, mọi ngữ cảnh đều nằm trong danh sách này.
- **`temperature=0`**: model luôn chọn từ có xác suất cao nhất. Output ổn định và ít "sáng tạo", đúng thứ cần cho hỏi đáp tài liệu.
- **`num_ctx`**: độ dài context tối đa (token). Mặc định của Ollama khá nhỏ và sẽ **cắt bớt mà không báo**, nên phải đặt rõ ràng.
- **`think`**: các model Qwen mới có chế độ "suy nghĩ" trước khi trả lời. Chế độ này cho kết quả tốt hơn với bài toán khó nhưng chậm hơn nhiều. Tắt đi để chạy nhanh trên laptop. Nếu Ollama báo lỗi liên quan tới `think`, xóa dòng đó đi.
- **`format`**: truyền JSON schema để Ollama **ép** model trả đúng cấu trúc (structured output). Đây là nền tảng cho bước kiểm chứng ở Phần 4.
- **Vì sao gom mọi lời gọi model vào một file:** sau này đổi sang vLLM hay một API khác, bạn chỉ sửa `llm.py`.

### 2.6. `app/embedder.py`: gọi embedding model

```python
import numpy as np
from ollama import Client

from . import config

_client = Client(host=config.OLLAMA_HOST)

# Qwen3-Embedding được huấn luyện để nhận "chỉ dẫn" ở phía câu hỏi.
# Tài liệu thì embed nguyên văn, câu hỏi thì thêm chỉ dẫn này phía trước.
QUERY_INSTRUCTION = (
    "Instruct: Given a question, retrieve passages from the document that answer the question\n"
    "Query: "
)


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-12, None)


def embed_documents(texts: list[str], batch_size: int = 16) -> np.ndarray:
    """Embed danh sách đoạn văn. Trả về ma trận (số_đoạn × số_chiều), đã chuẩn hóa."""
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        resp = _client.embed(model=config.EMBED_MODEL, input=texts[i : i + batch_size])
        vectors.extend(resp.embeddings)
    return _normalize(np.array(vectors, dtype=np.float32))


def embed_query(question: str) -> np.ndarray:
    """Embed một câu hỏi. Trả về vector 1 chiều, đã chuẩn hóa."""
    resp = _client.embed(model=config.EMBED_MODEL, input=[QUERY_INSTRUCTION + question])
    return _normalize(np.array(resp.embeddings, dtype=np.float32))[0]
```

**Giải thích:**
- **Batch (`batch_size=16`)**: gửi 16 đoạn trong một request thay vì 35 request riêng lẻ, nhanh hơn nhiều.
- **Chuẩn hóa (normalize)**: chia mỗi vector cho độ dài của nó để độ dài bằng 1. Khi đó **tích vô hướng (dot product) của hai vector chính bằng cosine similarity**, chỉ cần một phép nhân ma trận là tính được độ giống nhau với tất cả các đoạn.
- **`QUERY_INSTRUCTION`**: câu hỏi và đoạn văn có hình thức rất khác nhau (câu hỏi ngắn, đoạn văn dài). Chỉ dẫn này giúp model biết vector của câu hỏi cần "gần" với vector của đoạn chứa câu trả lời. Chỉ dẫn viết bằng tiếng Anh vì đó là dạng model được huấn luyện, nhưng câu hỏi vẫn bằng tiếng Việt.

### 2.7. ✅ Kiểm tra Phần 2

Tạo file tạm `backend/test_models.py`:

```python
from app import llm, embedder

print("CHAT:", llm.chat([{"role": "user", "content": "Chào bạn, trả lời một câu ngắn."}]))

v1 = embedder.embed_query("Học phí ngành công nghệ thông tin là bao nhiêu?")
docs = embedder.embed_documents([
    "Học phí ngành Công nghệ thông tin năm 2026 là 15 triệu đồng mỗi học kỳ.",
    "Ký túc xá có 500 phòng, ưu tiên sinh viên năm nhất.",
])
print("Số chiều vector:", v1.shape)
print("Độ giống với 2 đoạn:", docs @ v1)
```

```powershell
python test_models.py
```

Kết quả mong đợi: model chat trả lời được, và **điểm của đoạn học phí cao hơn rõ rệt so với đoạn ký túc xá**. Nếu đúng như vậy thì bạn vừa tận mắt thấy "tìm kiếm theo nghĩa" hoạt động. Xong thì xóa file test này.

---

## Phần 3. Indexing: PDF → đoạn văn → vector

### 3.1. `app/pdf_parser.py`: trích và làm sạch text

```python
import re
from collections import Counter

import fitz  # PyMuPDF

PAGE_NUMBER_RE = re.compile(r"^\s*(trang\s*)?\d+(\s*/\s*\d+)?\s*$", re.IGNORECASE)


def _extract_pages(pdf_path: str) -> list[str]:
    with fitz.open(pdf_path) as doc:
        return [page.get_text("text") for page in doc]


def _remove_repeated_lines(pages_lines: list[list[str]]) -> list[list[str]]:
    """Bỏ các dòng xuất hiện ở >= 60% số trang (thường là header/footer)."""
    n = len(pages_lines)
    if n < 3:
        return pages_lines
    counter: Counter[str] = Counter()
    for lines in pages_lines:
        counter.update({l.strip() for l in lines if l.strip()})
    repeated = {line for line, count in counter.items() if count >= n * 0.6}
    return [[l for l in lines if l.strip() not in repeated] for lines in pages_lines]


def parse_pdf(pdf_path: str) -> list[tuple[int, str]]:
    """Trả về danh sách (số_trang, dòng_text) đã làm sạch, theo thứ tự trong file."""
    pages_lines = [page.splitlines() for page in _extract_pages(pdf_path)]
    pages_lines = _remove_repeated_lines(pages_lines)

    result: list[tuple[int, str]] = []
    for page_no, lines in enumerate(pages_lines, start=1):
        for line in lines:
            line = line.strip()
            if not line or PAGE_NUMBER_RE.match(line):
                continue
            result.append((page_no, line))
    return result
```

**Giải thích:**
- **Vì sao trả về `(số_trang, dòng)`** thay vì một chuỗi dài: để mỗi đoạn văn sau này biết mình nằm ở trang nào, từ đó trích dẫn được "(trang 7)".
- **`_remove_repeated_lines`**: header/footer (tên trường, tên văn bản) lặp lại ở mọi trang. Nếu giữ lại, chúng làm nhiễu vector của mọi đoạn. Mẹo nhận diện: dòng nào xuất hiện ở hầu hết các trang thì gần như chắc chắn là header/footer.
- **`PAGE_NUMBER_RE`**: bỏ các dòng chỉ chứa số trang, kiểu `7`, `Trang 7`, `7/20`.
- **`with fitz.open(...)`**: tự đóng file sau khi đọc xong. Trên Windows, file đang mở thì không xóa được, điều này sẽ quan trọng ở Phần 5.
- **Giới hạn:** PDF scan (ảnh chụp) sẽ không trích được chữ nào, cần OCR. Ta sẽ phát hiện trường hợp này và báo lỗi rõ ràng ở `pipeline.py`. Bảng phức tạp cũng có thể bị trích lộn xộn. Hãy **mở file kết quả ra đọc bằng mắt** ở bước kiểm tra cuối phần này.

### 3.2. `app/chunker.py`: cắt đoạn theo cấu trúc

```python
import re
from dataclasses import dataclass

CHAPTER_RE = re.compile(r"^(chương|phần|mục)\s+[ivxlcdm\d]+\b", re.IGNORECASE)
ARTICLE_RE = re.compile(r"^điều\s+\d+", re.IGNORECASE)


@dataclass
class Chunk:
    id: str
    text: str        # nội dung gốc: dùng để hiển thị và kiểm chứng trích dẫn
    header: str      # tiêu đề ngữ cảnh: "Tên file > Chương II > Điều 5. ..."
    page_start: int
    page_end: int

    def text_for_search(self) -> str:
        """Văn bản đưa vào embedding/BM25/reranker: có thêm tiêu đề ngữ cảnh."""
        return f"[{self.header}]\n{self.text}"


def _split_section(lines: list[tuple[int, str]], max_words: int, overlap_words: int):
    """Cắt một mục dài thành nhiều phần ~max_words từ, chồng lấn ~overlap_words từ."""
    parts, current, count = [], [], 0
    for page, line in lines:
        words = len(line.split())
        if current and count + words > max_words:
            parts.append(current)
            # Giữ lại vài dòng cuối của phần vừa cắt làm phần chồng lấn
            carry, carry_count = [], 0
            for item in reversed(current):
                w = len(item[1].split())
                if carry_count + w > overlap_words:
                    break
                carry.insert(0, item)
                carry_count += w
            current, count = carry, carry_count
        current.append((page, line))
        count += words
    if current:
        parts.append(current)
    return parts


def chunk_document(
    lines: list[tuple[int, str]], doc_title: str, max_words: int, overlap_words: int
) -> list[Chunk]:
    # Bước 1: gom các dòng thành "mục" theo tiêu đề Chương / Điều
    sections: list[tuple[str, str, list[tuple[int, str]]]] = []
    chapter, article = "", ""
    current: list[tuple[int, str]] = []

    for page, line in lines:
        is_chapter = bool(CHAPTER_RE.match(line))
        is_article = bool(ARTICLE_RE.match(line))
        if (is_chapter or is_article) and current:
            sections.append((chapter, article, current))
            current = []
        if is_chapter:
            chapter, article = line[:100], ""
        elif is_article:
            article = line[:120]
        current.append((page, line))
    if current:
        sections.append((chapter, article, current))

    # Bước 2: mục nào dài thì cắt nhỏ tiếp, rồi tạo Chunk
    chunks: list[Chunk] = []
    for chap, art, sec_lines in sections:
        header = " > ".join(x for x in (doc_title, chap, art) if x)
        for part in _split_section(sec_lines, max_words, overlap_words):
            chunks.append(
                Chunk(
                    id=f"c{len(chunks)}",
                    text="\n".join(line for _, line in part),
                    header=header,
                    page_start=part[0][0],
                    page_end=part[-1][0],
                )
            )
    return chunks
```

**Giải thích:**
- **Bước 1 (cắt theo cấu trúc):** đi qua từng dòng. Gặp dòng bắt đầu bằng "Chương ..." hay "Điều ..." thì đóng mục cũ, mở mục mới. Như vậy mỗi Điều nằm trọn trong một mục, một ý không bị chia đôi. Văn bản hành chính Việt Nam rất hợp với cách này.
- **Ghi nhớ `chapter` và `article` hiện tại:** khi đi tới Điều 5, biến `chapter` vẫn đang giữ "Chương II", nên đoạn đó biết nó thuộc chương nào.
- **Bước 2 (`_split_section`):** Điều nào quá dài (vượt `CHUNK_WORDS` từ) thì cắt tiếp. Đơn vị cắt là **dòng**, không cắt giữa dòng.
- **Chồng lấn:** khi cắt, vài dòng cuối của phần trước được lặp lại ở đầu phần sau, để ý nằm vắt qua chỗ cắt vẫn trọn vẹn trong ít nhất một phần.
- **Đếm "từ" thay vì token:** đếm token chính xác cần tokenizer của model. Đếm từ (với tiếng Việt là đếm âm tiết) là xấp xỉ đủ tốt. 350 từ tiếng Việt vào khoảng 450–550 token.
- **`text_for_search()` (tiêu đề ngữ cảnh):** đoạn "Thời hạn là 15 ngày" đứng một mình thì vô nghĩa. Khi thêm `[Quy chế > Chương II > Điều 5. Phúc khảo]` vào đầu, cả embedding lẫn LLM đều biết đó là thời hạn phúc khảo.
- **Vì sao tách `text` và `text_for_search`:** `text` là nguyên văn trong file, dùng để kiểm chứng trích dẫn. Phần tiêu đề do ta thêm vào, không có trong file nên không được tính khi kiểm chứng.

> **Tùy chỉnh:** nếu tài liệu của bạn đánh đề mục kiểu "1.", "1.1", "I.", "II." thì sửa hai regex `CHAPTER_RE` và `ARTICLE_RE` cho phù hợp. Đây là chỗ đáng đầu tư nhất để tăng độ chính xác.

### 3.3. `app/store.py`: lưu index và tìm theo vector

```python
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from . import config
from .chunker import Chunk


class DocumentIndex:
    def __init__(self, doc_id: str, title: str, chunks: list[Chunk], embeddings: np.ndarray):
        self.doc_id = doc_id
        self.title = title
        self.chunks = chunks
        self.embeddings = embeddings  # ma trận (số_đoạn × số_chiều), đã chuẩn hóa
        self.bm25 = None              # tạo khi cần (Phần 7)

    def vector_search(self, query_vec: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        """Trả về [(vị_trí_đoạn, điểm_cosine)] sắp xếp giảm dần."""
        scores = self.embeddings @ query_vec
        order = np.argsort(-scores)[:top_k]
        return [(int(i), float(scores[i])) for i in order]


_cache: dict[str, DocumentIndex] = {}


def _doc_dir(doc_id: str) -> Path:
    return Path(config.DATA_DIR) / doc_id


def save_index(index: DocumentIndex) -> None:
    folder = _doc_dir(index.doc_id)
    folder.mkdir(parents=True, exist_ok=True)
    meta = {
        "doc_id": index.doc_id,
        "title": index.title,
        "chunks": [asdict(c) for c in index.chunks],
    }
    (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(folder / "embeddings.npy", index.embeddings)
    _cache[index.doc_id] = index


def load_index(doc_id: str) -> DocumentIndex | None:
    if doc_id in _cache:
        return _cache[doc_id]
    folder = _doc_dir(doc_id)
    if not (folder / "meta.json").exists():
        return None
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    index = DocumentIndex(
        doc_id=meta["doc_id"],
        title=meta["title"],
        chunks=[Chunk(**c) for c in meta["chunks"]],
        embeddings=np.load(folder / "embeddings.npy"),
    )
    _cache[doc_id] = index
    return index
```

**Giải thích:**
- **Vì sao chưa dùng vector database:** một file 20 trang chỉ có khoảng 35–60 đoạn. Nhân ma trận numpy cho ngần ấy đoạn mất chưa tới 1 mili giây. Tự viết như vậy giúp bạn **thấy rõ vector search thực chất chỉ là một phép nhân ma trận rồi sắp xếp**. Khi cần hàng chục nghìn đoạn hoặc nhiều người dùng thì chuyển sang pgvector (Phần 11), lúc đó chỉ phải sửa file này.
- **`self.embeddings @ query_vec`**: nhân ma trận (n × d) với vector (d) ra n điểm số, mỗi điểm là cosine similarity giữa câu hỏi và một đoạn (vì cả hai đều đã chuẩn hóa).
- **`np.argsort(-scores)`**: lấy thứ tự sắp xếp giảm dần (thêm dấu trừ để đảo chiều).
- **Lưu thành hai file:** `meta.json` (nội dung đoạn, đọc bằng mắt được) và `embeddings.npy` (ma trận vector dạng nhị phân, đọc ghi nhanh).
- **`_cache`**: giữ index trong RAM sau lần tải đầu, không phải đọc ổ cứng mỗi lần hỏi.
- **`ensure_ascii=False`**: giữ nguyên tiếng Việt có dấu trong JSON thay vì chuyển thành `\u1ec7`.

### 3.4. ✅ Kiểm tra Phần 3

Chuẩn bị một PDF mẫu khoảng 20 trang (quy chế, thông báo...), đặt vào thư mục `backend/`, đặt tên `sample.pdf`. Tạo file tạm `backend/test_index.py`:

```python
from app import pdf_parser, chunker, config

lines = pdf_parser.parse_pdf("sample.pdf")
print("Số dòng:", len(lines))

chunks = chunker.chunk_document(lines, "sample", config.CHUNK_WORDS, config.CHUNK_OVERLAP_WORDS)
print("Số đoạn:", len(chunks))
for c in chunks[:5]:
    print("=" * 60)
    print(f"{c.id} | trang {c.page_start}-{c.page_end} | {c.header}")
    print(c.text[:300])
```

```powershell
python test_index.py
```

**Đọc kỹ output bằng mắt**, vì đây là bước bị bỏ qua nhiều nhất:
- Header/footer đã bị loại chưa?
- Tiêu đề Chương/Điều có được nhận ra không? Nếu `header` chỉ có tên file thì regex chưa khớp với cách đánh đề mục trong tài liệu của bạn.
- Bảng biểu có bị trích lộn xộn không?

---

## Phần 4. Hỏi đáp: tìm kiếm, sinh câu trả lời, kiểm chứng

### 4.1. `app/prompts.py`: toàn bộ prompt ở một nơi

```python
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
- Chỉ xuất ra đúng một câu hỏi, không giải thích, không trả lời.

Ví dụ:
Lịch sử:
Hỏi: Học phí ngành A là bao nhiêu?
Đáp: Học phí ngành A là 15 triệu đồng/học kỳ.
Câu mới: Còn ngành B thì sao?
Viết lại: Học phí ngành B là bao nhiêu?

Lịch sử:
{history}
Câu mới: {question}
Viết lại:"""
```

**Giải thích:**
- **`ANSWER_SCHEMA`**: model bị ép trả về đúng ba trường. `found` cho model một "lối thoát" hợp lệ khi không tìm thấy, thay vì bị dồn vào thế phải viết ra điều gì đó.
- **Quy tắc 2** ngăn lỗi lan truyền: nếu câu trả lời ở lượt 2 sai, lượt 3 không được dựa vào nó.
- **Quy tắc 4 ("chép chính xác từng chữ")**: chuẩn bị cho bước kiểm chứng bằng code.
- **`<<< >>>`**: tách rõ phần dữ liệu (tài liệu) với phần chỉ dẫn, để nội dung trong file không bị model hiểu nhầm thành lệnh.
- **Nhãn `[Đoạn i | Trang ... | ...]`**: model biết mỗi đoạn đến từ đâu.
- **`(Hiểu đầy đủ là: ...)`**: khi câu hỏi đã được viết lại (Phần 8), đưa cả hai bản cho model. Model 4B hiểu câu hỏi đầy đủ tốt hơn câu ngắn kiểu "còn ngành B thì sao?".
- **Vì sao gom prompt vào một file:** prompt là thứ bạn sẽ chỉnh nhiều nhất. Để một chỗ thì dễ sửa và dễ so sánh các phiên bản.

### 4.2. `app/verify.py`: kiểm chứng trích dẫn bằng code

```python
import re
import unicodedata

from rapidfuzz import fuzz

from .chunker import Chunk

MIN_QUOTE_CHARS = 8


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:\"'“”‘’()")


def _find_quote(quote: str, chunks: list[Chunk], fuzzy_threshold: int) -> Chunk | None:
    q = normalize(quote)
    if len(q) < MIN_QUOTE_CHARS:
        return None  # quá ngắn, không đủ làm bằng chứng

    # 1) Khớp chính xác (sau chuẩn hóa)
    for c in chunks:
        if q in normalize(c.text):
            return c

    # 2) Khớp gần đúng: chấp nhận sai lệch nhỏ (model chép sai 1-2 chữ)
    best, best_score = None, 0.0
    for c in chunks:
        score = fuzz.partial_ratio(q, normalize(c.text))
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= fuzzy_threshold else None


def verify_quotes(quotes: list[str], chunks: list[Chunk], fuzzy_threshold: int = 90) -> list[dict] | None:
    """Trả về danh sách trích dẫn kèm trang nếu TẤT CẢ đều có thật; ngược lại trả về None."""
    if not quotes:
        return None
    citations = []
    for q in quotes:
        c = _find_quote(q, chunks, fuzzy_threshold)
        if c is None:
            return None
        citations.append({"quote": q, "page": c.page_start, "section": c.header})
    return citations
```

**Giải thích:**
- **Ý tưởng cốt lõi:** không tin lời model, mà kiểm tra bằng code. Model nói "tài liệu viết rằng X", code đi tìm X trong tài liệu. Không thấy thì từ chối.
- **Kiểm chứng với `chunks` được đưa vào prompt** (không phải cả file): model chỉ được phép trích từ những gì nó đã được xem.
- **`unicodedata.normalize("NFC", ...)`: rất quan trọng với tiếng Việt.** Một chữ "ệ" có thể được lưu thành 1 ký tự (dạng dựng sẵn) hoặc nhiều ký tự ghép (chữ "e" + dấu mũ + dấu nặng). PDF hay dùng dạng ghép, model hay xuất dạng dựng sẵn. Nhìn bằng mắt giống hệt nhau nhưng so sánh chuỗi thì khác. NFC đưa cả hai về cùng một dạng.
- **Gộp khoảng trắng, viết thường, bỏ dấu câu ở hai đầu:** để khác biệt nhỏ như xuống dòng hay dấu chấm cuối câu không làm một trích dẫn đúng bị đánh trượt.
- **`partial_ratio`**: đo mức độ khớp của câu trích với **đoạn con** giống nhất trong văn bản (0–100). Ngưỡng 90 cho phép sai khoảng một vài chữ.
- **`MIN_QUOTE_CHARS`**: chặn những trích dẫn quá ngắn như "có" hay "15 ngày". Chuỗi ngắn như vậy gần như chắc chắn tìm thấy ở đâu đó, nên không có giá trị làm bằng chứng.
- **Giới hạn cần biết:** lớp này bắt được trích dẫn **bịa**, nhưng không bắt được trường hợp trích dẫn đúng mà **diễn giải sai**. Vì vậy giao diện luôn hiện đoạn trích cạnh câu trả lời để người đọc tự đối chiếu.

### 4.3. `app/memory.py`: lịch sử hội thoại

```python
from collections import defaultdict

_sessions: dict[str, list[dict]] = defaultdict(list)


def get_history(key: str, turns: int) -> list[dict]:
    """Lấy `turns` lượt gần nhất (mỗi lượt gồm 1 câu hỏi + 1 câu trả lời)."""
    return list(_sessions[key][-turns * 2 :])


def add_turn(key: str, question: str, answer: str) -> None:
    _sessions[key].append({"role": "user", "content": question})
    _sessions[key].append({"role": "assistant", "content": answer})


def clear(key: str) -> None:
    _sessions.pop(key, None)
```

**Giải thích:**
- **`key`** sẽ có dạng `doc_id:session_id`. Mỗi người dùng với mỗi tài liệu có lịch sử riêng, nên 3 người demo cùng lúc không bị lẫn lịch sử của nhau.
- **`[-turns * 2:]`** (cửa sổ trượt): mỗi lượt có 2 message, nên lấy `turns × 2` message cuối. Các lượt cũ hơn bị bỏ để không vượt ngân sách context.
- **Giới hạn:** lưu trong RAM nên **khởi động lại server là mất lịch sử**. Như vậy là đủ cho demo. Lên production thì lưu vào Redis hoặc PostgreSQL, và chỉ phải sửa file này.

### 4.4. `app/pipeline.py`: ghép tất cả lại

```python
import uuid

from . import chunker, config, embedder, llm, memory, pdf_parser, prompts, store, verify

REFUSAL = "Tài liệu không có thông tin để trả lời câu hỏi này."


# ---------------------------------------------------------------- INDEXING
def ingest_pdf(pdf_path: str, title: str) -> store.DocumentIndex:
    lines = pdf_parser.parse_pdf(pdf_path)
    if not lines:
        raise ValueError("Không trích được chữ nào từ PDF. Có thể đây là bản scan, cần OCR.")

    chunks = chunker.chunk_document(lines, title, config.CHUNK_WORDS, config.CHUNK_OVERLAP_WORDS)
    vectors = embedder.embed_documents([c.text_for_search() for c in chunks])

    index = store.DocumentIndex(uuid.uuid4().hex, title, chunks, vectors)
    store.save_index(index)
    return index


# ---------------------------------------------------------------- QUERY
def _rewrite_question(history: list[dict], question: str) -> str:
    history_text = "\n".join(
        ("Hỏi: " if m["role"] == "user" else "Đáp: ") + m["content"] for m in history
    )
    prompt = prompts.REWRITE_PROMPT.format(history=history_text, question=question)
    out = llm.chat([{"role": "user", "content": prompt}]).strip()
    first_line = out.splitlines()[0].strip() if out else ""
    return first_line or question


def _retrieve(index: store.DocumentIndex, query: str):
    """Trả về (danh_sách_ứng_viên, kết_quả_vector) — mỗi phần tử là (vị_trí_đoạn, điểm)."""
    q_vec = embedder.embed_query(query)
    vector_hits = index.vector_search(q_vec, config.TOP_K_RETRIEVE)
    if not config.USE_BM25:
        return vector_hits, vector_hits

    from .bm25 import BM25Index, rrf_fuse  # chỉ import khi bật cờ

    if index.bm25 is None:
        index.bm25 = BM25Index([c.text_for_search() for c in index.chunks])
    keyword_hits = index.bm25.search(query, config.TOP_K_RETRIEVE)
    fused = rrf_fuse([vector_hits, keyword_hits])[: config.TOP_K_RETRIEVE]
    return fused, vector_hits


def answer_question(doc_id: str, session_id: str, question: str) -> dict:
    index = store.load_index(doc_id)
    if index is None:
        raise ValueError("Không tìm thấy tài liệu. Hãy upload lại.")

    key = f"{doc_id}:{session_id}"
    history = memory.get_history(key, config.HISTORY_TURNS)

    # B1. Viết lại câu hỏi tiếp nối
    search_query = question
    if config.USE_REWRITE and history:
        search_query = _rewrite_question(history, question)

    # B2. Tìm kiếm
    candidates, vector_hits = _retrieve(index, search_query)

    # B3. Rerank + chọn ngưỡng từ chối
    if config.USE_RERANK:
        from .reranker import rerank

        ranked = rerank(search_query, [(i, index.chunks[i].text_for_search()) for i, _ in candidates])
        top = ranked[: config.TOP_K_CONTEXT]
        gate = config.MIN_RERANK_SCORE
    else:
        top = candidates[: config.TOP_K_CONTEXT]
        gate = config.MIN_VECTOR_SCORE

    # Điểm dùng để quyết định: điểm rerank (nếu bật) hoặc cosine cao nhất
    best_score = top[0][1] if (config.USE_RERANK and top) else (vector_hits[0][1] if vector_hits else 0.0)

    # B4. Ghép ngữ cảnh: giữ thứ tự xuất hiện trong văn bản
    context_chunks = [index.chunks[i] for i in sorted(i for i, _ in top)]

    debug = {
        "search_query": search_query,
        "best_score": round(best_score, 4),
        "gate": gate,
        "rejected_reason": None,
        "retrieved": [
            {
                "page_start": index.chunks[i].page_start,
                "page_end": index.chunks[i].page_end,
                "header": index.chunks[i].header,
                "score": round(s, 4),
            }
            for i, s in top
        ],
    }

    def finish(answer: str, found: bool, citations: list[dict]) -> dict:
        memory.add_turn(key, question, answer)
        return {"answer": answer, "found": found, "citations": citations, "debug": debug}

    # Lớp 1: chặn trước khi gọi LLM
    if best_score < gate:
        debug["rejected_reason"] = "low_retrieval_score"
        return finish(REFUSAL, False, [])

    # B5. Sinh câu trả lời
    messages = (
        [{"role": "system", "content": prompts.SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": prompts.build_user_message(context_chunks, question, search_query)}]
    )
    result = llm.chat_json(messages, prompts.ANSWER_SCHEMA)

    if result is None:
        debug["rejected_reason"] = "invalid_json"
        return finish(REFUSAL, False, [])
    if not result.get("found"):
        debug["rejected_reason"] = "model_not_found"
        return finish(REFUSAL, False, [])

    # B6. Kiểm chứng trích dẫn
    citations = verify.verify_quotes(result.get("quotes", []), context_chunks)
    if citations is None:
        debug["rejected_reason"] = "quote_not_verified"
        return finish(REFUSAL, False, [])

    return finish(result.get("answer", "").strip(), True, citations)
```

**Giải thích theo từng bước:**

- **Indexing (`ingest_pdf`):** đúng luồng đã vẽ: parse → chunk → embed → lưu. `uuid.uuid4().hex` tạo `doc_id` ngẫu nhiên gồm 32 ký tự hex, không đoán được.
- **B1:** chỉ viết lại khi bật cờ và **có lịch sử**. Câu hỏi đầu tiên không có gì để kế thừa nên bỏ qua, tiết kiệm một lượt gọi model.
- **B2:** vector search luôn chạy. Khi bật BM25 thì gộp thêm kết quả từ khóa. `vector_hits` được trả riêng ra vì điểm cosine dùng làm ngưỡng từ chối khi chưa có reranker.
- **B3, chọn ngưỡng:**
  - Chưa bật rerank: dùng **cosine cao nhất** so với `MIN_VECTOR_SCORE`.
  - Đã bật rerank: dùng **điểm rerank cao nhất** so với `MIN_RERANK_SCORE`. Điểm rerank đáng tin hơn nhiều.
  - Vì sao không dùng điểm RRF làm ngưỡng: RRF chỉ phản ánh thứ hạng, không phản ánh mức độ liên quan tuyệt đối. Đoạn đứng đầu luôn có điểm RRF cao, kể cả khi câu hỏi hoàn toàn không liên quan.
- **B4:** sắp các đoạn theo **thứ tự trong văn bản** thay vì theo điểm. Model đọc mạch lạc hơn khi Điều 4 đứng trước Điều 5.
- **Lớp 1 (`best_score < gate`):** từ chối mà **không gọi LLM**. Đây là lớp chống bịa chắc chắn nhất, vì model không được gọi thì không thể bịa.
- **B5:** thứ tự messages là `system` (quy tắc), rồi lịch sử, rồi tài liệu kèm câu hỏi. Tài liệu đặt ở message cuối, gần câu hỏi nhất, để model chú ý tới nó nhiều nhất.
- **B6:** model nói tìm thấy nhưng trích dẫn không có thật thì vẫn từ chối.
- **`debug`:** trả về để giao diện hiển thị và script đánh giá phân tích. Khi một câu trả lời sai, nhìn `rejected_reason` và `retrieved` là biết ngay lỗi nằm ở khâu tìm kiếm hay khâu sinh câu trả lời.
- **`finish`:** mọi nhánh đều lưu lượt hỏi vào lịch sử, kể cả nhánh từ chối, để câu hỏi tiếp nối vẫn hiểu được ngữ cảnh.

> **Vì sao câu trả lời không stream (hiện chữ dần)?** Phải có câu trả lời **đầy đủ** thì mới kiểm chứng được trích dẫn. Nếu stream, người dùng sẽ thấy câu trả lời trước rồi mới bị "thu hồi" khi kiểm chứng thất bại. Đây là đánh đổi có chủ đích: chậm hơn một chút nhưng an toàn. Phần 11 có gợi ý cách hiển thị trạng thái tiến trình để bù lại.

---

## Phần 5. API với FastAPI

### 5.1. `app/main.py`

```python
import os
import re
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from . import config, pipeline

app = FastAPI(title="Doc QA API")

DOC_ID_RE = re.compile(r"^[0-9a-f]{32}$")
MAX_UPLOAD_MB = 20


class ChatRequest(BaseModel):
    doc_id: str
    session_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "chat_model": config.CHAT_MODEL,
        "embed_model": config.EMBED_MODEL,
        "flags": {"bm25": config.USE_BM25, "rerank": config.USE_RERANK, "rewrite": config.USE_REWRITE},
    }


@app.post("/api/documents")
def upload_document(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Chỉ hỗ trợ file PDF.")

    data = file.file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File vượt quá {MAX_UPLOAD_MB}MB.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        index = pipeline.ingest_pdf(tmp_path, title=Path(file.filename).stem)
    except ValueError as e:
        raise HTTPException(422, str(e))
    finally:
        os.remove(tmp_path)

    return {
        "doc_id": index.doc_id,
        "title": index.title,
        "num_chunks": len(index.chunks),
        "num_pages": max((c.page_end for c in index.chunks), default=0),
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not DOC_ID_RE.match(req.doc_id):
        raise HTTPException(400, "doc_id không hợp lệ.")
    if not req.question.strip():
        raise HTTPException(400, "Câu hỏi trống.")
    try:
        return pipeline.answer_question(req.doc_id, req.session_id, req.question.strip())
    except ValueError as e:
        raise HTTPException(404, str(e))
```

**Giải thích:**
- **Vì sao dùng `def` (không phải `async def`):** các hàm trong pipeline là **blocking** (chờ model trả lời). Với endpoint `def`, FastAPI tự chạy request trong một thread riêng, nên 3 người hỏi cùng lúc không chặn nhau. Nếu viết `async def` mà bên trong gọi hàm blocking thì cả server bị đứng trong lúc chờ.
- **`ChatRequest` (Pydantic):** tự kiểm tra dữ liệu gửi lên, sai kiểu hoặc thiếu trường thì tự trả lỗi 422. `max_length=2000` ngăn ai đó gửi câu hỏi siêu dài làm tràn context.
- **`DOC_ID_RE`: bảo mật.** `doc_id` được dùng để ghép đường dẫn thư mục. Nếu không kiểm tra, kẻ xấu có thể gửi `../../` để đọc file ngoài thư mục `data/` (lỗi path traversal). Chỉ chấp nhận đúng 32 ký tự hex.
- **File tạm:** PyMuPDF cần đường dẫn file, nên ghi dữ liệu upload ra file tạm, xử lý xong thì xóa trong khối `finally` (luôn chạy, kể cả khi có lỗi). `delete=False` cần thiết trên Windows, vì Windows không cho mở lại một file tạm đang mở.
- **Mã lỗi HTTP:** 400 là dữ liệu sai, 404 là không tìm thấy, 413 là file quá lớn, 422 là không xử lý được (ví dụ PDF scan). Frontend sẽ hiển thị nội dung `detail` của lỗi.

### 5.2. ✅ Chạy và kiểm tra Phần 5

```powershell
# trong backend/, đã activate .venv
uvicorn app.main:app --reload --port 8000
```

- `--reload`: tự khởi động lại khi bạn sửa code, rất tiện khi đang phát triển.
- Mở trình duyệt vào `http://localhost:8000/docs`. FastAPI tự sinh **trang tài liệu API (Swagger)**, nơi bạn thử API trực tiếp:
  1. `POST /api/documents` → **Try it out** → chọn `sample.pdf` → **Execute** → chép `doc_id`.
  2. `POST /api/chat` → điền `doc_id`, `session_id` (gõ tùy ý, ví dụ `test1`), `question` → **Execute**.
  3. Thử ba loại câu hỏi: có trong file, không liên quan ("giá vàng hôm nay"), và câu bẫy (cùng chủ đề nhưng file không có thông tin).

Đọc `debug` trong kết quả để hiểu hệ thống đã quyết định như thế nào. **🎉 Đến đây backend tối thiểu đã chạy được.**

---

## Phần 6. Frontend Next.js

Mở **terminal mới** (giữ terminal backend đang chạy).

> **Phiên bản:** phần này được viết và kiểm tra với **Next.js 16.4 + React 19.3 + Tailwind CSS 4** (bản `create-next-app` tạo ra vào thời điểm viết). Next.js 16 khác khá nhiều so với các hướng dẫn cũ trên mạng (Next 13–15), nên các chỗ khác biệt đều được ghi chú ⚠️ bên dưới. Khi gặp thứ lạ, tài liệu đúng phiên bản nằm ngay trong `frontend/node_modules/next/dist/docs/`.

Cấu trúc thư mục frontend khi xong phần này:

```
frontend/
├── next.config.ts         # rewrites /api → backend (6.2)
├── lib/
│   └── api.ts             # kiểu dữ liệu + hàm gọi API (6.3)
├── components/
│   ├── HealthBadge.tsx    # trạng thái backend (6.4)
│   ├── UploadPanel.tsx    # tải PDF (6.5)
│   └── ChatPanel.tsx      # khung chat (6.6)
└── app/
    ├── layout.tsx         # sửa lang + tiêu đề (6.7)
    └── page.tsx           # ghép các component (6.7)
```

### 6.1. Tạo project

```powershell
cd doc-qa
npx create-next-app@latest frontend
```

Chọn **"Yes, use recommended defaults"** (TypeScript, ESLint, Tailwind CSS, App Router, alias `@/*`, không dùng `src/`).

> Nếu bạn tự chọn dùng thư mục `src/`, mọi đường dẫn `app/...`, `components/...`, `lib/...` bên dưới sẽ nằm trong `src/`.

Mở `frontend/next.config.ts` vừa được tạo ra, bạn sẽ thấy create-next-app đã viết sẵn một số cấu hình:

- **`turbopack.rules` cho `*.css`**: đây chính là chỗ **nạp Tailwind CSS**. Project mới không còn file `postcss.config.mjs` như trước, Tailwind chạy qua loader này. ⚠️ **Xóa đi là toàn bộ class Tailwind mất tác dụng.**
- **`cacheComponents: true`** + **`partialPrefetching: true`**: chế độ render mới của Next 16. Next sẽ **prerender** (render sẵn lúc build) mọi trang có thể, và **báo lỗi build** nếu trong lúc prerender có code tạo giá trị ngẫu nhiên như `Math.random()`, `Date.now()`, `crypto.randomUUID()`. Điều này ảnh hưởng trực tiếp đến cách tạo `sessionId` ở bước 6.7.
- **`experimental.agentFeedback`**: tính năng hỗ trợ AI coding agent, không ảnh hưởng gì, cứ giữ.

Ngoài ra còn file `AGENTS.md` do `next dev` tự tạo, dành cho các AI agent đọc. Không cần quan tâm.

### 6.2. Chuyển tiếp `/api` sang backend: `next.config.ts`

⚠️ **Không thay toàn bộ file**, mà **thêm** `rewrites`, `allowedDevOrigins` và `proxyTimeout` vào cấu hình có sẵn. File hoàn chỉnh:

```ts
import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Chuyển tiếp mọi request /api/* sang FastAPI
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },

  // Cho phép mở dev server qua tên miền ngrok (Phần 10)
  allowedDevOrigins: ["*.ngrok-free.app", "*.ngrok-free.dev", "*.ngrok.app"],

  experimental: {
    agentFeedback: true,
    // Upload + embedding trên laptop có thể mất hơn 30 giây (mặc định),
    // nên nới thời gian chờ của proxy lên 3 phút.
    proxyTimeout: 180_000,
  },

  // --- Phần do create-next-app tạo sẵn: GIỮ NGUYÊN ---
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
```

**Giải thích:**
- **`BACKEND_URL`**: đọc từ biến môi trường, không có thì dùng `http://localhost:8000`. Lên server chỉ cần đặt biến này, không phải sửa code.
- **`rewrites`**: trình duyệt gọi `/api/chat` (cùng địa chỉ với trang web). Server Next.js âm thầm chuyển tiếp sang `http://localhost:8000/api/chat` rồi trả kết quả về. `:path*` nghĩa là "khớp mọi đoạn đường dẫn phía sau", nên `/api/documents`, `/api/health`... đều được chuyển. Ba lợi ích:
  1. **Không cần cấu hình CORS**, vì với trình duyệt mọi request đều cùng nguồn (same-origin).
  2. **Backend không bị lộ ra ngoài**: khi demo qua ngrok chỉ expose cổng 3000.
  3. Lên server thì chỉ đổi biến `BACKEND_URL`.
- **`allowedDevOrigins`**: ở Next 16, dev server (`npm run dev`) mặc định **chặn** các request đến từ tên miền khác `localhost`. Khi mở qua link ngrok ở Phần 10, nếu thiếu dòng này trang sẽ hiện ra nhưng bấm không phản hồi (JavaScript không nạp được). Dấu `*` khớp với một nhãn tên miền bất kỳ, ví dụ `abcd-1234.ngrok-free.app`. Chỉ ảnh hưởng chế độ dev; `npm start` không cần.
- **`experimental.proxyTimeout`**: thời gian tối đa (mili giây) Next chờ backend trả lời khi chuyển tiếp qua rewrites. Mặc định khoảng 30 giây, không đủ cho lần upload đầu khi Ollama còn phải nạp embedding model vào VRAM. `180_000` là cách viết số có dấu phân cách của JavaScript, bằng `180000` (3 phút). Tùy chọn này vẫn có trong Next 16.4 (đã kiểm tra trong `next/dist/server/config-shared.d.ts`).

> **Lưu ý:** mỗi lần sửa `next.config.ts` phải **dừng và chạy lại** `npm run dev`, Next không tự nạp lại file này.

### 6.3. `lib/api.ts`: các hàm gọi API

Tạo thư mục `frontend/lib/` và file `frontend/lib/api.ts`:

```ts
export type DocInfo = {
  doc_id: string;
  title: string;
  num_chunks: number;
  num_pages: number;
};

export type Citation = { quote: string; page: number; section: string };

export type RetrievedChunk = { page_start: number; page_end: number; header: string; score: number };

export type ChatResult = {
  answer: string;
  found: boolean;
  citations: Citation[];
  debug: {
    search_query: string;
    best_score: number;
    gate: number;
    rejected_reason: string | null;
    retrieved: RetrievedChunk[];
  };
};

export type HealthInfo = {
  status: string;
  chat_model: string;
  embed_model: string;
  flags: { bm25: boolean; rerank: boolean; rewrite: boolean };
};

/** Giới hạn phải khớp với MAX_UPLOAD_MB trong backend/app/main.py */
export const MAX_UPLOAD_MB = 20;

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Lỗi ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") {
        // Lỗi do code mình chủ động raise HTTPException(...)
        message = data.detail;
      } else if (Array.isArray(data?.detail)) {
        // Lỗi 422 do Pydantic kiểm tra dữ liệu: detail là một mảng
        message = data.detail.map((d: { msg?: string }) => d.msg).join("; ");
      }
    } catch {
      // Response không phải JSON: thường là backend chưa chạy,
      // Next.js không chuyển tiếp được nên trả về trang lỗi 500.
      if (res.status >= 500) message = "Không kết nối được backend. Kiểm tra uvicorn đã chạy ở cổng 8000 chưa.";
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<DocInfo> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/documents", { method: "POST", body: form });
  return handle<DocInfo>(res);
}

export async function askQuestion(docId: string, sessionId: string, question: string): Promise<ChatResult> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_id: docId, session_id: sessionId, question }),
  });
  return handle<ChatResult>(res);
}

export async function getHealth(): Promise<HealthInfo> {
  const res = await fetch("/api/health", { cache: "no-store" });
  return handle<HealthInfo>(res);
}

/** Tạo mã phiên. crypto.randomUUID chỉ có ở localhost/https, nên có phương án dự phòng. */
export function newSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}
```

**Giải thích:**
- **Các `type`** phản chiếu đúng cấu trúc JSON mà backend trả về (đối chiếu với `main.py` và hàm `finish` trong `pipeline.py`). TypeScript sẽ báo lỗi nếu bạn gõ sai tên trường, ví dụ `citation` thay vì `citations`. `RetrievedChunk` được tách thành kiểu riêng để dễ đọc và dùng lại.
- **`MAX_UPLOAD_MB`**: để frontend kiểm tra kích thước file **trước khi** upload, tránh gửi 50MB lên rồi mới bị backend từ chối. Con số phải khớp với `MAX_UPLOAD_MB` trong `main.py`; đổi một bên thì đổi cả bên kia.
- **`handle<T>`**: hàm dùng chung để xử lý response. `<T>` là **generic**: người gọi nói trước "tôi chờ kiểu `DocInfo`" thì hàm trả về đúng kiểu đó. Nếu lỗi, hàm đọc thông báo rồi ném ra `Error`, để component chỉ cần một khối `try/catch`. Có **ba dạng lỗi** cần phân biệt:
  1. `detail` là **chuỗi**: lỗi do code của bạn chủ động `raise HTTPException(400, "...")`. Hiện nguyên văn.
  2. `detail` là **mảng**: lỗi **422** do Pydantic tự kiểm tra `ChatRequest` (ví dụ câu hỏi dài quá 2000 ký tự). FastAPI trả về dạng `[{ "msg": "...", "loc": [...] }, ...]`, nên ghép các `msg` lại. Bản cũ chỉ hiện "Lỗi 422", khó hiểu.
  3. Response **không phải JSON** và mã ≥ 500: gần như chắc chắn là **backend chưa chạy**. Next.js không chuyển tiếp được nên trả về chữ `Internal Server Error`, `res.json()` ném lỗi và ta rơi vào `catch`. Hiện thông báo dễ hiểu thay vì "Lỗi 500".
- **`FormData`**: định dạng chuẩn để gửi file. **Không tự đặt header `Content-Type`**, vì trình duyệt sẽ tự đặt kèm "boundary" (chuỗi phân cách các phần dữ liệu). Tên trường `"file"` phải trùng tên tham số `file: UploadFile` trong FastAPI.
- **`getHealth`**: gọi `/api/health` để biết backend còn sống và đang dùng model nào. `cache: "no-store"` yêu cầu luôn lấy dữ liệu mới.
- **`newSessionId`**: `crypto.randomUUID()` chỉ có trong **ngữ cảnh an toàn** (`localhost` hoặc `https`). Nếu mở qua `http://192.168.x.x:3000` trong mạng LAN thì hàm này **không tồn tại** và trang sẽ lỗi. Phương án dự phòng ghép thời gian hiện tại (`Date.now()` đổi sang cơ số 36 cho ngắn) với một chuỗi ngẫu nhiên. Mã phiên chỉ cần **không trùng** giữa các tab, không cần an toàn mật mã, nên cách này đủ dùng.
- **URL tương đối `/api/...`**: đi qua rewrites ở bước 6.2.

### 6.4. `components/HealthBadge.tsx`: trạng thái backend

Tạo thư mục `frontend/components/` và file `HealthBadge.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { getHealth, type HealthInfo } from "@/lib/api";

export default function HealthBadge() {
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setError(e instanceof Error ? e.message : "Lỗi không xác định"));
  }, []);

  if (error) return <p className="mb-4 text-xs text-red-600">● Backend: {error}</p>;
  if (!health) return <p className="mb-4 text-xs text-gray-500">● Đang kiểm tra backend...</p>;

  const flags = Object.entries(health.flags)
    .filter(([, on]) => on)
    .map(([name]) => name);

  return (
    <p className="mb-4 text-xs text-gray-500">
      <span className="text-green-600">●</span> {health.chat_model} · {health.embed_model}
      {flags.length > 0 && ` · bật: ${flags.join(", ")}`}
    </p>
  );
}
```

**Giải thích:**
- Dòng nhỏ dưới tiêu đề cho biết ngay: backend có chạy không, đang dùng model nào, cờ nâng cấp nào (BM25, rerank, rewrite ở Phần 7, 8) đang bật. Khi so sánh kết quả trước/sau nâng cấp, nhìn vào đây là biết đang ở cấu hình nào, khỏi nhầm.
- **`useEffect(..., [])`**: mảng phụ thuộc rỗng nghĩa là chỉ chạy **một lần** sau khi component hiện lên trình duyệt. Đây là chỗ đúng để gọi API khi trang mở. Vì `useEffect` không chạy lúc prerender, cách này không vi phạm quy tắc của `cacheComponents`.
- **Ba trạng thái hiển thị**: lỗi (đỏ), đang chờ (xám), thành công (chấm xanh). Cùng mẫu `data / loading / error` như các component khác, chỉ khác là "loading" được suy ra từ việc `health` còn `null`.
- **`Object.entries(health.flags)`** biến `{ bm25: false, rerank: false, rewrite: true }` thành `[["bm25", false], ...]`, sau đó `filter` giữ cờ đang bật và `map` lấy tên. Cú pháp `[, on]` nghĩa là bỏ qua phần tử đầu (tên), chỉ lấy phần tử thứ hai (giá trị).
- Khi backend tắt, badge hiện ngay "Không kết nối được backend..." nên bạn biết lỗi ở đâu trước khi upload.

> Lưu ý: badge chỉ kiểm tra **một lần** lúc mở trang. Nếu bạn bật backend sau, tải lại trang (F5) để cập nhật.

### 6.5. `components/UploadPanel.tsx`

```tsx
"use client";

import { useState } from "react";
import { MAX_UPLOAD_MB, uploadDocument, type DocInfo } from "@/lib/api";

export default function UploadPanel({ onUploaded }: { onUploaded: (doc: DocInfo) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleSelect(selected: File | null) {
    setError(null);
    if (selected && !selected.name.toLowerCase().endsWith(".pdf")) {
      setError("Chỉ hỗ trợ file PDF.");
      selected = null;
    } else if (selected && selected.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`File vượt quá ${MAX_UPLOAD_MB}MB.`);
      selected = null;
    }
    setFile(selected);
  }

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      onUploaded(await uploadDocument(file));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi không xác định");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-gray-300 p-6 dark:border-gray-700">
      <h2 className="mb-1 text-lg font-semibold">1. Tải tài liệu PDF</h2>
      <p className="mb-4 text-sm text-gray-500">
        Hệ thống chỉ trả lời dựa trên nội dung file này. Tối đa {MAX_UPLOAD_MB}MB, PDF có chữ (không phải bản scan).
      </p>
      <input
        type="file"
        accept="application/pdf,.pdf"
        disabled={loading}
        onChange={(e) => handleSelect(e.target.files?.[0] ?? null)}
        className="mb-4 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-gray-100 file:px-3 file:py-2 dark:file:bg-gray-800"
      />
      {file && (
        <p className="mb-4 text-sm text-gray-500">
          {file.name} · {(file.size / 1024 / 1024).toFixed(1)}MB
        </p>
      )}
      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className="rounded-lg bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {loading ? "Đang xử lý tài liệu..." : "Tải lên"}
      </button>
      {loading && (
        <p className="mt-3 text-sm text-gray-500">
          Lần đầu có thể mất 1–2 phút vì Ollama phải nạp embedding model.
        </p>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}
```

**Giải thích:**
- **`"use client"`**: trong App Router, component mặc định chạy trên server (Server Component). Component này dùng `useState` và sự kiện `onClick`, tức là cần chạy trong trình duyệt, nên phải khai báo là client component.
- **Ba state** `file`, `loading`, `error` là mẫu chuẩn cho mọi thao tác bất đồng bộ: có dữ liệu gì, đang chờ hay không, có lỗi gì.
- **`handleSelect`**: kiểm tra đuôi `.pdf` và kích thước **ngay khi chọn file**. Thuộc tính `accept` trên thẻ `input` chỉ là gợi ý cho hộp thoại chọn file, người dùng vẫn chọn "All files" được, nên phải kiểm tra lại bằng code. Backend cũng kiểm tra lần nữa, vì không bao giờ tin hoàn toàn vào dữ liệu từ trình duyệt.
- **`onUploaded`**: component không tự quyết định làm gì sau khi upload xong, mà báo lên component cha. Cách này gọi là "lifting state up", giúp component dễ tái sử dụng.
- **`disabled={!file || loading}`**: chặn bấm khi chưa chọn file hoặc khi đang xử lý, tránh upload hai lần. Ô chọn file cũng bị khóa khi đang upload.
- **`(file.size / 1024 / 1024).toFixed(1)`**: đổi byte sang MB, làm tròn 1 chữ số thập phân.
- **Class `file:...`**: tiền tố `file:` của Tailwind áp dụng style cho **nút "Choose file"** bên trong thẻ `input type="file"`, vốn rất khó style bằng CSS thường.
- **Dòng nhắc khi đang tải**: lần upload đầu có thể mất 1–2 phút, nhắc trước để người dùng không tưởng app bị treo.

### 6.6. `components/ChatPanel.tsx`

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { askQuestion, type ChatResult, type DocInfo } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
  result?: ChatResult;
  isError?: boolean;
};

export default function ChatPanel({ doc, sessionId }: { doc: DocInfo; sessionId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send() {
    const question = input.trim();
    if (!question || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);
    try {
      const result = await askQuestion(doc.doc_id, sessionId, question);
      setMessages((prev) => [...prev, { role: "assistant", content: result.answer, result }]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Lỗi không xác định";
      setMessages((prev) => [...prev, { role: "assistant", content: msg, isError: true }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function bubbleClass(m: Message) {
    const base = "max-w-[85%] rounded-2xl px-4 py-2";
    if (m.role === "user") return `${base} bg-blue-600 text-white`;
    if (m.isError) return `${base} bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300`;
    if (m.result && !m.result.found)
      return `${base} bg-amber-50 text-amber-900 dark:bg-amber-950 dark:text-amber-200`;
    return `${base} bg-gray-100 dark:bg-gray-800`;
  }

  return (
    <div className="flex h-[70vh] flex-col rounded-xl border border-gray-300 dark:border-gray-700">
      <div className="border-b border-gray-300 px-4 py-3 text-sm dark:border-gray-700">
        <span className="font-semibold">{doc.title}</span>
        <span className="text-gray-500">
          {" "}
          · {doc.num_pages} trang · {doc.num_chunks} đoạn
        </span>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-center text-sm text-gray-500">Đặt câu hỏi về nội dung tài liệu.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div className={bubbleClass(m)}>
              <p className="whitespace-pre-wrap">
                {m.isError && "⚠️ "}
                {m.content}
              </p>

              {m.result && m.result.citations.length > 0 && (
                <div className="mt-3 space-y-2 border-t border-gray-300 pt-2 dark:border-gray-600">
                  {m.result.citations.map((c, j) => (
                    <blockquote key={j} className="text-xs text-gray-600 dark:text-gray-300">
                      <span className="font-semibold">
                        Trang {c.page}
                        {c.section && ` · ${c.section}`}
                      </span>
                      <br />“{c.quote}”
                    </blockquote>
                  ))}
                </div>
              )}

              {m.result && (
                <details className="mt-2 text-xs text-gray-500">
                  <summary className="cursor-pointer">
                    Chi tiết xử lý · điểm {m.result.debug.best_score} / ngưỡng {m.result.debug.gate}
                    {m.result.debug.rejected_reason && ` · ${m.result.debug.rejected_reason}`}
                  </summary>
                  <pre className="mt-1 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(m.result.debug, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        ))}
        {loading && <p className="text-sm text-gray-500">Đang tìm trong tài liệu...</p>}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 border-t border-gray-300 p-3 dark:border-gray-700">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.nativeEvent.isComposing) {
              e.preventDefault();
              send();
            }
          }}
          maxLength={2000}
          placeholder="Nhập câu hỏi..."
          className="flex-1 rounded-lg border border-gray-300 bg-transparent px-3 py-2 dark:border-gray-700"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
        >
          Gửi
        </button>
      </div>
    </div>
  );
}
```

**Giải thích:**
- **Kiểu `Message`** có thêm `isError`, để phân biệt **lỗi kỹ thuật** (mất kết nối, 404) với **câu trả lời từ chối** của hệ thống. Hai thứ này ý nghĩa rất khác nhau: từ chối là RAG đang làm đúng việc, còn lỗi là có gì đó hỏng.
- **`setMessages((prev) => [...prev, ...])`**: luôn dùng dạng **hàm** khi state mới phụ thuộc vào state cũ. Hàm `send` có `await` ở giữa, nếu viết `[...messages, ...]` thì giá trị `messages` có thể đã cũ và tin nhắn bị mất.
- **Hiện câu hỏi ngay trước khi gọi API**: người dùng thấy phản hồi tức thì, không có cảm giác ứng dụng bị treo.
- **`useRef` + `scrollIntoView`**: một thẻ `div` rỗng ở cuối danh sách. Mỗi khi `messages` hoặc `loading` đổi thì cuộn tới thẻ đó, tức là tự cuộn xuống tin mới nhất.
- **`inputRef.current?.focus()`** trong `finally`: trả con trỏ về ô nhập sau mỗi câu trả lời, để hỏi tiếp không cần bấm chuột.
- **`bubbleClass`**: chọn màu bong bóng theo 4 trường hợp: người dùng (xanh dương), lỗi (đỏ), từ chối `found: false` (vàng hổ phách), trả lời bình thường (xám). Nhìn màu là biết ngay câu nào hệ thống không trả lời được, rất tiện khi soạn bộ câu hỏi đánh giá ở Phần 9.
- **`e.nativeEvent.isComposing`**: **quan trọng với người gõ tiếng Việt bằng Unikey hoặc bộ gõ IME.** Khi bộ gõ đang ghép dấu, phím Enter có thể dùng để chốt chữ. Nếu không kiểm tra điều kiện này, câu hỏi sẽ bị gửi đi lúc đang gõ dở. `e.preventDefault()` chặn hành vi mặc định của Enter.
- **`maxLength={2000}`**: khớp với `max_length=2000` của `question` trong `ChatRequest` (`main.py`), chặn từ phía giao diện.
- **Trích dẫn dưới câu trả lời**: hiện số trang, tên mục (`section`) và đoạn trích nguyên văn, để người dùng đối chiếu ngay với nguồn. Đây là lớp bảo vệ cuối cùng chống ảo giác, đặt vào tay con người. Cú pháp `{c.section && ...}` chỉ hiện tên mục khi có.
- **`<details>` "Chi tiết xử lý"**: dòng tóm tắt hiện sẵn **điểm tìm kiếm / ngưỡng** và **lý do từ chối** (nếu có), bấm vào mới thấy toàn bộ `debug`. Khi một câu bị từ chối, nhìn dòng này là biết ngay do điểm thấp (`low_retrieval_score`), do model không tìm thấy (`model_not_found`) hay do trích dẫn không khớp (`quote_not_verified`), từ đó biết nên chỉnh chỗ nào. Lúc demo cho người ngoài có thể ẩn đi.

### 6.7. `app/layout.tsx` và `app/page.tsx`

**a) `app/layout.tsx`**: chỉ sửa 2 chỗ trong file có sẵn, phần còn lại giữ nguyên:

```tsx
export const metadata: Metadata = {
  title: "Hỏi đáp tài liệu",
  description: "Hỏi đáp tài liệu PDF với Qwen (RAG)",
};

// ...

    <html
      lang="vi"
      // ...giữ nguyên className
    >
```

- **`metadata`**: chữ hiện trên tab trình duyệt và khi chia sẻ link.
- **`lang="vi"`**: báo cho trình duyệt biết trang là tiếng Việt, để trình đọc màn hình đọc đúng giọng và trình duyệt không hỏi "Dịch trang này?".
- ⚠️ Kiểu `LayoutProps<"/">` trong file là kiểu Next 16 **tự sinh** khi chạy `npm run dev` hoặc `npm run build`. Nếu VS Code báo `Cannot find name 'LayoutProps'` trước khi chạy lần nào, cứ chạy `npm run dev` một lần (hoặc `npx next typegen`) là hết.

**b) `app/page.tsx`**: thay toàn bộ nội dung:

```tsx
"use client";

import { useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import HealthBadge from "@/components/HealthBadge";
import UploadPanel from "@/components/UploadPanel";
import { newSessionId, type DocInfo } from "@/lib/api";

type Session = { doc: DocInfo; sessionId: string };

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);

  return (
    <main className="mx-auto w-full max-w-3xl p-6">
      <h1 className="mb-2 text-2xl font-bold">Hỏi đáp tài liệu</h1>
      <HealthBadge />

      {!session ? (
        <UploadPanel onUploaded={(doc) => setSession({ doc, sessionId: newSessionId() })} />
      ) : (
        <>
          <div className="mb-3 flex gap-2">
            <button
              onClick={() => setSession({ doc: session.doc, sessionId: newSessionId() })}
              className="rounded-lg border border-gray-300 px-3 py-1 text-sm dark:border-gray-700"
            >
              Cuộc trò chuyện mới
            </button>
            <button
              onClick={() => setSession(null)}
              className="rounded-lg border border-gray-300 px-3 py-1 text-sm dark:border-gray-700"
            >
              Đổi tài liệu
            </button>
          </div>
          <ChatPanel key={session.sessionId} doc={session.doc} sessionId={session.sessionId} />
        </>
      )}
    </main>
  );
}
```

**Giải thích:**
- **Gộp `doc` và `sessionId` vào một state `session`**: hai giá trị này luôn đi cùng nhau. Chưa có tài liệu thì cũng chưa cần mã phiên. Gộp lại thì chỉ có hai trạng thái rõ ràng: `null` (đang chờ upload) hoặc có đủ cả hai.
- ⚠️ **Vì sao tạo `sessionId` trong sự kiện, không dùng `useState(() => crypto.randomUUID())`**: với `cacheComponents: true` (mặc định ở Next 16), lúc `npm run build` Next **prerender** trang này trên server, và mọi lệnh tạo giá trị ngẫu nhiên chạy trong lúc render đều làm build **thất bại** (`Error occurred prerendering page "/"`). Đã thử: cách cũ chạy được với `npm run dev` nhưng **hỏng khi build**. Đặt `newSessionId()` bên trong `onUploaded` và `onClick` thì nó chỉ chạy khi người dùng thao tác trên trình duyệt, không bao giờ chạy lúc prerender. Một lợi ích phụ: mỗi lần upload tài liệu mới là có phiên mới, lịch sử không bị lẫn.
- **`sessionId`**: mỗi phiên trò chuyện có một mã ngẫu nhiên, gửi kèm mọi câu hỏi. Backend ghép `doc_id:session_id` làm khóa để tách lịch sử của từng người (`memory.py`).
- **`key={session.sessionId}` trên `ChatPanel`**: một mẹo React rất hữu ích. Khi `key` thay đổi (bấm "Cuộc trò chuyện mới" hoặc upload tài liệu khác), React **hủy component cũ và tạo component mới hoàn toàn**, nên mọi state bên trong (danh sách tin nhắn, ô nhập) tự được xóa sạch, không cần viết code reset. Vì mỗi lần đổi tài liệu đều tạo `sessionId` mới, chỉ cần `sessionId` làm key là đủ.
- **"Cuộc trò chuyện mới"**: giữ nguyên tài liệu, chỉ tạo `sessionId` mới. Backend coi như một người dùng mới không có lịch sử.
- **"Đổi tài liệu"**: đặt `session` về `null`, quay lại màn hình upload.
- **`"use client"` ở page**: trang cần `useState` nên phải là client component. Next vẫn prerender được phần HTML ban đầu (màn hình upload) vì lúc đó không có gì ngẫu nhiên.

### 6.8. ✅ Chạy toàn hệ thống

```powershell
cd frontend
npm run dev
```

Mở `http://localhost:3000` và kiểm tra lần lượt:

1. Dòng trạng thái dưới tiêu đề có **chấm xanh** và tên hai model. Nếu báo "Không kết nối được backend", kiểm tra lại terminal uvicorn.
2. Upload PDF, thấy tên tài liệu cùng số trang và số đoạn.
3. Hỏi một câu **có** trong tài liệu: câu trả lời nền xám kèm trích dẫn có số trang.
4. Hỏi một câu **không có** trong tài liệu: bong bóng vàng "Tài liệu không có thông tin...". Mở "Chi tiết xử lý" xem lý do.
5. Gõ tiếng Việt có dấu bằng Unikey rồi nhấn Enter: câu hỏi không bị gửi khi đang gõ dở.
6. Bấm "Cuộc trò chuyện mới": khung chat trống, hỏi câu tiếp nối kiểu "còn cái kia thì sao?" thì hệ thống không còn nhớ ngữ cảnh cũ.

Cuối cùng chạy build một lần để chắc code không có lỗi kiểu dữ liệu hay lỗi prerender:

```powershell
npm run lint
npm run build
```

Build thành công sẽ có bảng `Route (app)` với dòng `○ /` (trang được prerender tĩnh). Muốn chạy bản build: `npm start`.

**🎉 Đến đây bạn đã có một ứng dụng RAG hoàn chỉnh chạy end-to-end.**

Lúc này hệ thống mới dùng **vector search**. Hãy chạy đánh giá (Phần 9) để có **số liệu nền (baseline)** trước khi bật các nâng cấp ở Phần 7 và 8.

---

## Phần 7. Nâng cấp tìm kiếm: BM25 + RRF + Rerank

### 7.1. `app/bm25.py`: tìm theo từ khóa + gộp RRF

```python
import numpy as np
from rank_bm25 import BM25Okapi
from underthesea import word_tokenize


def tokenize_vi(text: str) -> list[str]:
    # "Học phí ngành CNTT" -> "Học_phí ngành CNTT" -> ["học_phí", "ngành", "cntt"]
    return word_tokenize(text, format="text").lower().split()


class BM25Index:
    def __init__(self, texts: list[str]):
        self.bm25 = BM25Okapi([tokenize_vi(t) for t in texts])

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        scores = self.bm25.get_scores(tokenize_vi(query))
        order = np.argsort(-scores)[:top_k]
        return [(int(i), float(scores[i])) for i in order if scores[i] > 0]


def rrf_fuse(rankings: list[list[tuple[int, float]]], k: int = 60) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion: gộp nhiều bảng xếp hạng thành một."""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (idx, _score) in enumerate(ranking, start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: -x[1])
```

**Giải thích:**
- **Vì sao cần BM25 khi đã có vector:** vector giỏi tìm theo **ý nghĩa** ("hạn chót" khớp với "thời hạn cuối cùng") nhưng hay trượt với **mã số, tên riêng, số hiệu** ("Điều 12", "mã ngành 7480201"). BM25 tìm theo **từ khóa chính xác** nên bắt những trường hợp này rất tốt. Hai cách bổ sung cho nhau.
- **Tách từ tiếng Việt:** tiếng Việt viết cách theo âm tiết, nhưng một "từ" có thể gồm nhiều âm tiết. Không tách từ thì "học phí" thành hai từ rời "học" và "phí", khớp lung tung với "học sinh", "chi phí"... `underthesea` nối các âm tiết của cùng một từ bằng dấu gạch dưới: `học_phí`.
- **`if scores[i] > 0`**: bỏ các đoạn không có từ khóa nào trùng với câu hỏi.
- **RRF:** mỗi đoạn được cộng `1/(60 + thứ_hạng)` từ mỗi bảng xếp hạng mà nó xuất hiện. Đoạn đứng hạng 1 ở cả hai bảng được `1/61 + 1/61`, cao hơn hẳn đoạn chỉ xuất hiện ở một bảng. Hằng số 60 làm cho chênh lệch giữa các hạng đầu không quá gắt. Ta dùng thứ hạng thay vì điểm số vì điểm cosine (0–1) và điểm BM25 (0–vài chục) có thang đo khác nhau, không cộng trực tiếp được.
- Lần đầu dùng, `underthesea` có thể tải thêm dữ liệu nên chậm. Các lần sau sẽ nhanh.

**Bật thử:** trong `.env` đặt `USE_BM25=true`. Với `--reload`, uvicorn **không** tự nhận thay đổi trong `.env`, nên phải dừng (Ctrl+C) rồi chạy lại uvicorn. Kiểm tra bằng `http://localhost:8000/api/health` xem cờ đã bật chưa.

### 7.2. `app/reranker.py`

```python
from sentence_transformers import CrossEncoder

from . import config

_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder(config.RERANK_MODEL, device=config.RERANK_DEVICE, max_length=512)
    return _model


def rerank(query: str, candidates: list[tuple[int, str]]) -> list[tuple[int, float]]:
    """candidates: [(vị_trí_đoạn, nội_dung)]. Trả về [(vị_trí_đoạn, điểm)] giảm dần."""
    if not candidates:
        return []
    model = _get_model()
    scores = model.predict([(query, text) for _, text in candidates])
    ranked = sorted(zip((i for i, _ in candidates), scores), key=lambda x: -x[1])
    return [(int(i), float(s)) for i, s in ranked]
```

**Giải thích:**
- **Khác biệt giữa embedding và reranker:**
  - Embedding (bi-encoder): mã hóa câu hỏi và đoạn văn **riêng rẽ** thành hai vector rồi so sánh. Nhanh, vector của đoạn văn tính sẵn được một lần, nhưng độ chính xác vừa phải.
  - Reranker (cross-encoder): đọc **câu hỏi và đoạn văn cùng lúc** trong một lượt, nên thấy được mối liên hệ chi tiết giữa từng từ. Chính xác hơn nhiều nhưng chậm, và không tính sẵn trước được.
  - Vì vậy ta dùng embedding lọc nhanh ra 20 ứng viên, rồi dùng reranker chấm kỹ 20 ứng viên đó.
- **`bge-reranker-v2-m3`**: model đa ngôn ngữ, xử lý tiếng Việt tốt, khoảng 570 triệu tham số. Lần chạy đầu sẽ tự tải về từ Hugging Face (khoảng 1–2GB, mất vài phút).
- **`device="cpu"`**: VRAM 6GB đã dành cho chat model (~3GB) và embedding model (~0.6GB). Cho reranker chạy CPU để Ollama không bị đẩy sang CPU. Chấm 20 đoạn trên i7-13800H mất khoảng một đến vài giây.
- **Nạp lười (lazy loading) với `_get_model()`**: model chỉ được nạp ở lần gọi đầu tiên, rồi giữ lại cho các lần sau. Server vẫn khởi động nhanh, và khi `USE_RERANK=false` thì model không bao giờ được nạp.
- **`max_length=512`**: reranker chỉ đọc tối đa 512 token mỗi cặp. Đoạn 350 từ tiếng Việt nằm gần giới hạn này, phần thừa ở cuối đoạn sẽ bị cắt. Nếu thấy rerank kém, thử giảm `CHUNK_WORDS` xuống khoảng 250.
- **Điểm số**: với model này, `predict` trả về điểm trong khoảng 0–1. Ngưỡng `MIN_RERANK_SCORE=0.30` chỉ là điểm xuất phát, phải chỉnh lại bằng số liệu ở Phần 9.

**Bật thử:** đặt `USE_RERANK=true` trong `.env`, khởi động lại uvicorn.

---

## Phần 8. Hiểu hội thoại: viết lại câu hỏi

Phần code đã có sẵn trong `pipeline.py` (`_rewrite_question`) và `prompts.py` (`REWRITE_PROMPT`). Chỉ cần bật `USE_REWRITE=true` rồi khởi động lại uvicorn.

**Cách kiểm tra:**
1. Hỏi: "Học phí ngành A là bao nhiêu?"
2. Hỏi tiếp: "Còn ngành B thì sao?"
3. Mở "Chi tiết xử lý" của câu trả lời thứ hai. `search_query` phải là một câu đầy đủ, kiểu "Học phí ngành B là bao nhiêu?".

**So sánh có và không có viết lại:** tắt `USE_REWRITE`, hỏi lại đúng chuỗi câu trên rồi xem `retrieved`. Thường bạn sẽ thấy hệ thống tìm ra những đoạn nói về ngành B nhưng không liên quan tới học phí. Đó chính là lỗi mà bước viết lại sửa được.

**Nhắc lại các nguyên tắc đã cài trong code:**
- Câu đã viết lại chỉ dùng để **tìm kiếm** và làm rõ ý cho model. Lịch sử lưu và hiển thị vẫn là câu gốc của người dùng.
- Mỗi lượt đều **tìm kiếm lại từ đầu**, không dùng lại kết quả của lượt trước.
- Kiểm chứng trích dẫn luôn so với **văn bản gốc**, không bao giờ so với lịch sử.

---

## Phần 9. Đánh giá chất lượng

> Không đo thì không biết thay đổi của mình làm hệ thống tốt lên hay tệ đi.

### 9.1. `eval/questions.json`

Tạo thư mục `backend/eval/`. Viết **20–30 câu hỏi** cho file PDF mẫu, chia ba nhóm:

```json
[
  { "question": "Hạn chót nộp hồ sơ xét tuyển là ngày nào?", "type": "in_doc", "expected_page": 3 },
  { "question": "Thí sinh được phúc khảo trong bao nhiêu ngày?", "type": "in_doc", "expected_page": 12 },
  { "question": "Giá vàng hôm nay bao nhiêu?", "type": "out_of_scope" },
  { "question": "Viết cho tôi một bài thơ về mùa thu", "type": "out_of_scope" },
  { "question": "Học phí ngành Y khoa là bao nhiêu?", "type": "trap" }
]
```

| Nhóm | Ý nghĩa | Kết quả đúng |
|---|---|---|
| `in_doc` | Có trong file. Ghi trang chứa đáp án vào `expected_page` | Trả lời, trích dẫn đúng trang |
| `out_of_scope` | Hoàn toàn không liên quan | Từ chối |
| `trap` | **Cùng chủ đề nhưng file không có thông tin** | Từ chối. Đây là nhóm dễ gây bịa nhất |

Nhóm `trap` là nhóm quan trọng nhất. Hãy viết nhiều câu loại này, ví dụ file chỉ có học phí của ba ngành thì hỏi học phí của ngành thứ tư.

### 9.2. `eval/run_eval.py`

```python
import argparse
import json
import uuid
from pathlib import Path

from app import config, pipeline


def page_hit(item: dict, result: dict) -> bool:
    """Đoạn chứa trang đáp án có nằm trong các đoạn được đưa vào prompt không? (recall@k)"""
    p = item.get("expected_page")
    if p is None:
        return False
    return any(r["page_start"] <= p <= r["page_end"] for r in result["debug"]["retrieved"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-id", required=True)
    parser.add_argument("--questions", default="eval/questions.json")
    args = parser.parse_args()

    items = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    stats = {"in_doc": [0, 0, 0], "out_of_scope": [0, 0], "trap": [0, 0]}
    failures = []

    for item in items:
        # Mỗi câu một session mới để lịch sử không ảnh hưởng kết quả
        result = pipeline.answer_question(args.doc_id, uuid.uuid4().hex, item["question"])
        t = item["type"]

        if t == "in_doc":
            hit = page_hit(item, result)
            stats[t][0] += 1
            stats[t][1] += int(result["found"])
            stats[t][2] += int(hit)
            if not result["found"] or not hit:
                failures.append((item, result))
        else:
            stats[t][0] += 1
            refused = not result["found"]
            stats[t][1] += int(refused)
            if not refused:
                failures.append((item, result))

    print(f"\nCấu hình: BM25={config.USE_BM25} RERANK={config.USE_RERANK} REWRITE={config.USE_REWRITE}")
    n, answered, hits = stats["in_doc"]
    if n:
        print(f"[in_doc]       trả lời {answered}/{n} ({answered / n:.0%}) | recall@{config.TOP_K_CONTEXT}: {hits}/{n} ({hits / n:.0%})")
    for t in ("out_of_scope", "trap"):
        n, refused = stats[t]
        if n:
            print(f"[{t:<12}] từ chối đúng {refused}/{n} ({refused / n:.0%})")

    print(f"\n--- {len(failures)} câu cần xem lại ---")
    for item, result in failures:
        d = result["debug"]
        print(f"\n[{item['type']}] {item['question']}")
        print(f"  found={result['found']} | reason={d['rejected_reason']} | best={d['best_score']} (ngưỡng {d['gate']})")
        print(f"  trang lấy được: {[r['page_start'] for r in d['retrieved']]} | trả lời: {result['answer'][:120]}")


if __name__ == "__main__":
    main()
```

Chạy (trong `backend/`, đã activate `.venv`). `doc_id` lấy từ lúc upload, hoặc xem tên thư mục trong `data/`:

```powershell
python -m eval.run_eval --doc-id <doc_id>
```

**Giải thích:**
- **`python -m eval.run_eval`** (chạy dạng module từ thư mục `backend/`): nhờ vậy Python tìm thấy package `app` để import.
- Script gọi thẳng `pipeline.answer_question` mà không qua HTTP, nên không cần bật uvicorn khi chạy đánh giá. Script vẫn đọc cấu hình từ `.env` như server.
- **recall@k**: đoạn chứa đáp án có lọt vào top k đoạn đưa cho model không. Nếu không lọt thì model **không thể** trả lời đúng, và lỗi nằm ở **khâu tìm kiếm**.

### 9.3. Đọc kết quả và chỉnh sửa

Chạy đánh giá ở từng cấu hình, rồi ghi số liệu vào một bảng:

| Cấu hình | Trả lời đúng (in_doc) | recall@4 | Từ chối đúng (out_of_scope) | Từ chối đúng (trap) |
|---|---|---|---|---|
| Vector (baseline) | | | | |
| + BM25 | | | | |
| + Rerank | | | | |

Dùng `rejected_reason` để chẩn đoán lỗi:

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `in_doc` bị từ chối, `reason=low_retrieval_score` | Ngưỡng quá cao | Giảm `MIN_VECTOR_SCORE` / `MIN_RERANK_SCORE` |
| `in_doc` có recall thấp | Tìm kiếm kém | Kiểm tra cắt đoạn (Phần 3.4), bật BM25/rerank |
| `in_doc` có recall tốt nhưng `reason=model_not_found` | Model 4B không nhận ra câu trả lời | Chỉnh prompt, giảm số đoạn đưa vào, hoặc dùng model lớn hơn |
| `reason=quote_not_verified` nhiều | Model chép trích dẫn không chính xác | Hạ `fuzzy_threshold` xuống khoảng 85, xem `normalize` |
| `trap` / `out_of_scope` bị trả lời | Ngưỡng quá thấp, hoặc model bịa | Tăng ngưỡng, xem câu trích dẫn đã lọt qua kiểm chứng như thế nào |

**Chọn ngưỡng:** ngưỡng càng cao thì từ chối càng nhiều, ít bịa hơn nhưng bỏ sót câu đúng nhiều hơn. Với hệ thống hỏi đáp quy chế hay văn bản hành chính, **bịa nguy hiểm hơn bỏ sót**, nên hãy ưu tiên nhóm `trap` đạt gần 100% rồi mới tối ưu nhóm `in_doc`.

---

## Phần 10. Demo qua ngrok

1. Đổi biến môi trường `OLLAMA_NUM_PARALLEL=3` (khởi động lại Ollama).
2. Trước buổi demo: upload file và hỏi một câu để **làm nóng**, cho mọi model đã được nạp sẵn.
3. Cắm sạc, chọn chế độ **Best performance**, tắt chế độ ngủ của máy.
4. Nên chạy bản build cho nhanh và ổn định hơn chế độ dev: trong `frontend/` chạy `npm run build` rồi `npm start`.
5. Expose **chỉ cổng Next.js**, kèm mật khẩu:

   ```powershell
   ngrok http 3000 --basic-auth "demo:matkhau-cua-ban"
   ```

6. Gửi link `https://....ngrok-free...` cùng user/pass cho người xem.

**Vì sao an toàn:** người xem chỉ vào được Next.js. Next.js chuyển `/api/*` sang FastAPI trong máy. FastAPI và Ollama **không hề lộ ra internet**.

**Theo dõi trong lúc demo:** mở thêm một terminal, chạy `ollama ps` để chắc chắn model vẫn chạy `100% GPU`.

---

## Phần 11. Bước tiếp theo

Xếp theo thứ tự nên làm:

1. **Mở rộng cửa sổ ngữ cảnh**: khi chọn được một đoạn, lấy thêm đoạn liền trước và liền sau (nếu cùng Điều). Gợi ý: sửa bước B4 trong `pipeline.py`, thêm `i-1` và `i+1` vào tập đoạn, nhớ kiểm tra ngân sách token.
2. **Hiển thị trạng thái tiến trình**: dùng Server-Sent Events (SSE) để gửi các trạng thái "Đang tìm...", "Đang đọc tài liệu...", "Đang kiểm chứng...". Câu trả lời cuối vẫn gửi trọn vẹn sau khi kiểm chứng.
3. **PDF scan**: thêm OCR (ví dụ PaddleOCR, hỗ trợ tiếng Việt tốt) trong `pdf_parser.py` khi trích ra không có chữ.
4. **Bảng biểu**: dùng `pdfplumber` hoặc Docling để trích bảng thành dạng Markdown, giữ trọn bảng trong một đoạn.
5. **Nhiều tài liệu**: chuyển `store.py` sang **pgvector** trên PostgreSQL, thêm cột `doc_id` để lọc khi tìm kiếm.
6. **Lịch sử bền vững**: chuyển `memory.py` sang Redis hoặc PostgreSQL.
7. **Lên server GPU**: chạy **vLLM** với model lớn hơn (ví dụ Qwen3.8-27B). Sửa `llm.py` dùng thư viện `openai` trỏ tới vLLM; structured output trên vLLM dùng tham số `response_format` hoặc guided decoding. Embedding có thể tiếp tục chạy bằng Ollama hoặc chuyển sang chế độ embedding của vLLM.
8. **Đóng gói Docker Compose**: các service `frontend`, `backend`, `ollama`/`vllm`, `postgres`.
9. **Fine-tune (khi đã có dữ liệu)**: dùng log hỏi đáp thực tế đã được người kiểm duyệt làm dữ liệu QLoRA cho model 4B, chủ yếu để model tuân thủ định dạng và trích dẫn chính xác hơn. Luôn đo bằng bộ đánh giá ở Phần 9 trước và sau khi fine-tune.

---

## Phụ lục A. Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `model "..." not found` | Sai tên tag hoặc chưa pull | `ollama list` để xem tên đúng, sửa `.env` |
| `Connection refused` tới cổng 11434 | Ollama chưa chạy | Mở ứng dụng Ollama |
| Trả lời rất chậm | Model bị đẩy sang CPU | `ollama ps`: nếu không phải `100% GPU` thì giảm `NUM_CTX` (ví dụ 4096), giảm `OLLAMA_NUM_PARALLEL`, đóng ứng dụng đang dùng GPU |
| Lỗi liên quan tham số `think` | Phiên bản Ollama hoặc model không hỗ trợ | Xóa dòng `"think": config.THINK` trong `llm.py` |
| Upload báo lỗi 422 "không trích được chữ" | PDF scan | Cần OCR (Phần 11) |
| Upload bị timeout từ phía Next.js | Xử lý lâu hơn thời gian chờ của proxy | Tăng `experimental.proxyTimeout` trong `next.config.ts` rồi dừng và chạy lại `npm run dev`. Nếu phiên bản Next.js không có tùy chọn này, xóa nó đi và cho frontend gọi thẳng backend khi dev (khi đó cần bật CORS trong FastAPI) |
| Giao diện báo "Không kết nối được backend" | uvicorn chưa chạy, hoặc chạy khác cổng 8000 | Chạy lại backend (Phần 5.2), hoặc đặt biến `BACKEND_URL` cho đúng rồi chạy lại `npm run dev` |
| `npm run build` báo `Error occurred prerendering page "/"` | Có `crypto.randomUUID()`, `Math.random()` hoặc `Date.now()` chạy trong lúc render, bị `cacheComponents` chặn | Chuyển lệnh đó vào trong sự kiện (`onClick`, callback) hoặc `useEffect`, như bước 6.7 |
| Mất hết style Tailwind sau khi sửa `next.config.ts` | Đã xóa khối `turbopack.rules` do create-next-app tạo | Thêm lại khối đó (xem file mẫu ở 6.2) |
| `Cannot find name 'LayoutProps'` | Kiểu do Next tự sinh, chưa sinh lần nào | Chạy `npm run dev` một lần hoặc `npx next typegen` |
| Mở qua link ngrok, trang hiện nhưng bấm không phản hồi | Dev server chặn tên miền lạ | Kiểm tra `allowedDevOrigins` trong `next.config.ts` có khớp tên miền ngrok, hoặc demo bằng `npm run build` + `npm start` |
| `crypto.randomUUID is not a function` | Mở trang qua `http://` không phải localhost (vd IP LAN) | Dùng `newSessionId()` trong `lib/api.ts` (đã có phương án dự phòng) |
| Trích dẫn đúng nhưng vẫn bị từ chối | Khác biệt Unicode hoặc khoảng trắng | Kiểm tra `normalize` trong `verify.py`, hạ `fuzzy_threshold` |
| Sửa `.env` mà không thấy thay đổi | `--reload` không theo dõi `.env` | Dừng uvicorn và chạy lại |
| `ModuleNotFoundError: app` khi chạy eval | Chạy sai thư mục hoặc sai cách | Đứng ở `backend/`, chạy `python -m eval.run_eval ...` |
| Gõ tiếng Việt bị gửi khi chưa xong | Enter trong lúc bộ gõ đang ghép dấu | Đã xử lý bằng `isComposing`. Kiểm tra lại code `onKeyDown` |
| Lần hỏi đầu tiên rất chậm | Model đang được nạp vào VRAM / reranker đang tải về | Làm nóng trước, đặt `OLLAMA_KEEP_ALIVE` |

## Phụ lục B. Thuật ngữ

| Thuật ngữ | Giải thích ngắn |
|---|---|
| **LLM** | Mô hình ngôn ngữ lớn, ở đây là chat model `qwen3.5:4b` |
| **Token** | Đơn vị văn bản mà model xử lý, nhỏ hơn hoặc bằng một từ |
| **Context (`num_ctx`)** | Lượng token tối đa model "nhìn thấy" trong một lần gọi |
| **Embedding / vector** | Dãy số biểu diễn ý nghĩa của văn bản. Văn bản cùng nghĩa thì vector gần nhau |
| **Cosine similarity** | Độ giống nhau giữa hai vector (gần 1 là rất giống) |
| **Chunk** | Một đoạn văn bản nhỏ được cắt ra từ tài liệu |
| **RAG** | Retrieval-Augmented Generation: tìm thông tin, đưa vào prompt, rồi sinh câu trả lời |
| **BM25** | Thuật toán tìm kiếm theo từ khóa cổ điển |
| **RRF** | Reciprocal Rank Fusion: gộp nhiều bảng xếp hạng dựa trên thứ hạng |
| **Reranker (cross-encoder)** | Model chấm độ liên quan bằng cách đọc câu hỏi và đoạn văn cùng lúc |
| **Structured output** | Ép model trả về đúng một cấu trúc JSON cho trước |
| **Hallucination (ảo giác)** | Model tạo ra thông tin không có trong nguồn |
| **recall@k** | Tỷ lệ câu hỏi mà đoạn chứa đáp án nằm trong top k kết quả tìm được |
| **Temperature** | Mức độ ngẫu nhiên khi sinh văn bản. 0 là ổn định nhất |
| **Quantization (Q4, Q8)** | Nén trọng số model xuống ít bit hơn để tiết kiệm bộ nhớ |

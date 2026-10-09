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
KEEP_ALIVE = os.getenv("KEEP_ALIVE", "30m")              # giữ model trong VRAM bao lâu sau lần gọi cuối
EMBED_NUM_CTX = _int("EMBED_NUM_CTX", 2048)              # context của embedding model (đoạn văn ~600-800 token)
RERANK_MAX_LENGTH = _int("RERANK_MAX_LENGTH", 512)       # số token tối đa reranker đọc cho mỗi cặp
RERANK_TRUST_REMOTE_CODE = _bool("RERANK_TRUST_REMOTE_CODE", False)  # cần True với một số model (vd gte)

# Cắt đoạn
CHUNK_WORDS = _int("CHUNK_WORDS", 350)
CHUNK_OVERLAP_WORDS = _int("CHUNK_OVERLAP_WORDS", 40)

# Tìm kiếm
TOP_K_RETRIEVE = _int("TOP_K_RETRIEVE", 20)
TOP_K_CONTEXT = _int("TOP_K_CONTEXT", 4)
MIN_VECTOR_SCORE = _float("MIN_VECTOR_SCORE", 0.45)
MIN_RERANK_SCORE = _float("MIN_RERANK_SCORE", 0.30)     # ngưỡng TIN CẬY: dưới mức này vẫn hỏi model nhưng nhắc chặt hơn
# Ngưỡng CỨNG: dưới mức này từ chối ngay, không hỏi model (câu hỏi gần như chắc chắn không liên quan tài liệu).
# Câu hỏi đời thường của sinh viên hay có điểm rerank 0.01-0.3 dù đã tìm đúng đoạn -> ngưỡng cứng phải thấp.
HARD_RERANK_SCORE = _float("HARD_RERANK_SCORE", 0.005)
HARD_VECTOR_SCORE = _float("HARD_VECTOR_SCORE", 0.35)    # như trên, cho chế độ Nhanh (không rerank)
MAX_UPLOAD_MB = _int("MAX_UPLOAD_MB", 100)               # dung lượng PDF tối đa khi upload

# Hội thoại
HISTORY_TURNS = _int("HISTORY_TURNS", 3)

# Cờ nâng cấp (dùng khi chạy pipeline trực tiếp, vd benchmark; giao diện/API dùng chế độ trong trang Cài đặt)
USE_BM25 = _bool("USE_BM25", False)
USE_RERANK = _bool("USE_RERANK", False)
USE_REWRITE = _bool("USE_REWRITE", False)

# Chế độ trả lời: fast | balanced | accurate (xem app/options.py).
# DEFAULT_MODE: chế độ mặc định ban đầu của trang Cài đặt (admin đổi được trên giao diện).
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "balanced")
# MODE: chỉ dùng cho benchmark. Để trống = dùng các cờ USE_* ở trên như cũ.
MODE = os.getenv("MODE", "")
# Nạp sẵn model + chỉ mục khi khởi động backend, để người hỏi đầu tiên không phải chờ
WARMUP = _bool("WARMUP", True)

DATA_DIR = os.getenv("DATA_DIR", "data")

# Database (Postgres + pgvector, xem docker-compose.yml)
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://docshelf:docshelf_dev_123@127.0.0.1:5433/docshelf"
)
DB_POOL_SIZE = _int("DB_POOL_SIZE", 5)
DB_MAX_OVERFLOW = _int("DB_MAX_OVERFLOW", 10)

# Đăng nhập
JWT_SECRET = os.getenv("JWT_SECRET", "")                 # BẮT BUỘC đặt trong .env (chuỗi ngẫu nhiên dài)
JWT_EXPIRE_MINUTES = _int("JWT_EXPIRE_MINUTES", 60 * 24 * 7)  # 7 ngày
COOKIE_SECURE = _bool("COOKIE_SECURE", False)            # True khi chạy HTTPS thật

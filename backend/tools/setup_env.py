"""Hỗ trợ setup.bat (chạy trong backend/):

    python -m tools.setup_env           tạo .env từ .env.example (nếu chưa có) + sinh JWT_SECRET nếu đang trống
    python -m tools.setup_env --models  in tên 2 model Ollama cần tải (đọc từ .env), mỗi dòng một tên

Viết bằng Python thay vì trong file .bat: xử lý chuỗi trong .bat rất dễ hỏng (dấu ngoặc kép, ký tự đặc biệt).
"""
import re
import secrets
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ENV = BACKEND / ".env"
EXAMPLE = BACKEND / ".env.example"
EMPTY_SECRET = re.compile(r"^JWT_SECRET=[ \t]*$", re.MULTILINE)


def ensure_env() -> None:
    if ENV.exists():
        print("   Đã có backend\\.env, giữ nguyên các giá trị đang có.")
    else:
        ENV.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print("   Đã tạo backend\\.env từ .env.example.")

    text = ENV.read_text(encoding="utf-8")
    if EMPTY_SECRET.search(text):
        # Khóa ký token đăng nhập: ngẫu nhiên, 64 ký tự, chỉ nằm trên máy này
        text = EMPTY_SECRET.sub("JWT_SECRET=" + secrets.token_urlsafe(48), text, count=1)
        ENV.write_text(text, encoding="utf-8")
        print("   Đã sinh JWT_SECRET ngẫu nhiên.")


def print_models() -> None:
    from dotenv import dotenv_values

    values = dotenv_values(ENV)
    print(values.get("CHAT_MODEL") or "qwen3.5:4b")
    print(values.get("EMBED_MODEL") or "qwen3-embedding:0.6b")


if __name__ == "__main__":
    print_models() if "--models" in sys.argv else ensure_env()

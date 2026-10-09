"""Đo thời gian gọi Ollama: so sánh localhost với 127.0.0.1.

Cách chạy (trong backend/, đã activate .venv):
    python -m tools.check_latency

Nếu localhost ~2000 ms còn 127.0.0.1 vài trăm ms -> đổi OLLAMA_HOST trong .env thành
http://127.0.0.1:11434
"""
import time

from ollama import Client

from app import config

HOSTS = ["http://localhost:11434", "http://127.0.0.1:11434"]
ROUNDS = 3
IDLE_SECONDS = 6  # > 5s: kết nối keep-alive của httpx hết hạn, giống khoảng nghỉ giữa 2 câu hỏi thật

for host in HOSTS:
    client = Client(host=host)
    for i in range(ROUNDS):
        t = time.perf_counter()
        client.embed(
            model=config.EMBED_MODEL,
            input=["thử tốc độ"],
            keep_alive=config.KEEP_ALIVE,
            options={"num_ctx": config.EMBED_NUM_CTX},
        )
        ms = (time.perf_counter() - t) * 1000
        print(f"{host:<26} lần {i + 1}: {ms:7.0f} ms")
        if i < ROUNDS - 1:
            time.sleep(IDLE_SECONDS)
    print()

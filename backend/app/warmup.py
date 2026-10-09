"""Nạp sẵn mọi thứ ngay khi backend khởi động, chạy ngầm, không chặn việc khởi động.

Không có bước này, người hỏi ĐẦU TIÊN sau mỗi lần khởi động phải chờ thêm:
  - nạp reranker vào RAM: 5-15 giây
  - Ollama nạp model trả lời + model embedding vào VRAM: vài giây mỗi model
  - đọc tài liệu từ DB + dựng chỉ mục BM25
"""
import logging
import threading
import time

from sqlalchemy import select

from . import config, embedder, llm, store
from .db import SessionLocal
from .models import Document

log = logging.getLogger("docshelf.warmup")

MAX_DOCS = 50  # chỉ nạp sẵn 50 tài liệu mới nhất, tránh tốn RAM khi kệ rất lớn


def _step(name: str, fn) -> None:
    t = time.perf_counter()
    try:
        fn()
        log.warning("warmup: %s xong (%.1fs)", name, time.perf_counter() - t)
    except Exception as e:  # khởi động nóng là phần phụ: lỗi ở đây không được làm sập backend
        log.warning("warmup: %s lỗi: %s", name, e)


def _load_docs() -> None:
    from .bm25 import BM25Index

    with SessionLocal() as db:
        ids = db.scalars(select(Document.id).order_by(Document.created_at.desc()).limit(MAX_DOCS)).all()
    for doc_id in ids:
        index = store.load_index(doc_id)  # tài liệu cũ chưa có token BM25 sẽ được tách từ + lưu ở đây
        if index is not None and index.bm25 is None:
            index.bm25 = BM25Index(index.get_tokens())


def _reranker() -> None:
    from .reranker import rerank

    rerank("khởi động", [(0, "khởi động reranker")])


def run() -> None:
    _step("model embedding", lambda: embedder.embed_query("khởi động"))
    # prompt rỗng: Ollama chỉ nạp model vào VRAM, không sinh chữ
    _step("model trả lời", lambda: llm._client.generate(model=config.CHAT_MODEL, prompt="", keep_alive=config.KEEP_ALIVE))
    _step("reranker", _reranker)
    _step("tài liệu + chỉ mục BM25", _load_docs)


def start_in_background() -> None:
    if config.WARMUP:
        threading.Thread(target=run, name="warmup", daemon=True).start()

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
        resp = _client.embed(
            model=config.EMBED_MODEL,
            input=texts[i : i + batch_size],
            keep_alive=config.KEEP_ALIVE,
            options={"num_ctx": config.EMBED_NUM_CTX},
        )
        vectors.extend(resp.embeddings)
    return _normalize(np.array(vectors, dtype=np.float32))


def embed_query(question: str) -> np.ndarray:
    """Embed một câu hỏi. Trả về vector 1 chiều, đã chuẩn hóa."""
    resp = _client.embed(
        model=config.EMBED_MODEL,
        input=[QUERY_INSTRUCTION + question],
        keep_alive=config.KEEP_ALIVE,
        options={"num_ctx": config.EMBED_NUM_CTX},
    )
    return _normalize(np.array(resp.embeddings, dtype=np.float32))[0]

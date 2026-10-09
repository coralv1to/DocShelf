import numpy as np
from rank_bm25 import BM25Okapi
from underthesea import word_tokenize


def tokenize_vi(text: str) -> list[str]:
    # "Học phí ngành CNTT" -> "Học_phí ngành CNTT" -> ["học_phí", "ngành", "cntt"]
    return word_tokenize(text, format="text").lower().split()


class BM25Index:
    """Chỉ mục từ khóa. Nhận danh sách token đã tách sẵn (lưu trong DB, cột chunks.search_tokens),
    vì tách từ tiếng Việt cho cả tài liệu mất vài giây — làm một lần lúc upload thay vì mỗi lần hỏi."""

    def __init__(self, tokenized: list[list[str]]):
        self.bm25 = BM25Okapi(tokenized)

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

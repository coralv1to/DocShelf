"""Tùy chọn cho MỘT lượt hỏi: chạy những bước nào, ngưỡng bao nhiêu.

Trước đây pipeline đọc thẳng config.USE_RERANK, config.TOP_K_RETRIEVE...: một giá trị chung cho mọi người.
Giờ mỗi câu hỏi nhận một Options riêng, nên người A hỏi chế độ "Nhanh" và người B hỏi chế độ "Kỹ"
cùng lúc được, không ảnh hưởng nhau.

3 chế độ có sẵn:
  fast      Nhanh    : không rerank. Nhanh nhất, độ chính xác thấp hơn một chút.
  balanced  Cân bằng : có rerank, nhưng bỏ qua các bước không cần cho câu hỏi đó
                       (câu đã đủ nghĩa thì không viết lại; câu hỏi vị trí đã rõ thì không rerank).
  accurate  Kỹ       : luôn viết lại câu hỏi theo hội thoại, luôn rerank. Chậm nhất.
"""
from dataclasses import dataclass, replace

from . import config

MODES = ("fast", "balanced", "accurate")

MODE_INFO = {
    "fast": {
        "label": "Nhanh",
        "description": "Không chấm lại kết quả tìm kiếm (rerank). Nhanh nhất, đôi khi kém chính xác hơn.",
    },
    "balanced": {
        "label": "Cân bằng",
        "description": "Có chấm lại kết quả, nhưng bỏ qua các bước không cần cho từng câu hỏi. Khuyên dùng.",
    },
    "accurate": {
        "label": "Kỹ",
        "description": "Luôn hiểu câu hỏi theo hội thoại và luôn chấm lại kết quả. Chậm nhất.",
    },
}

# Các bước mỗi chế độ bật / tắt
_PRESETS = {
    "fast": {"use_bm25": True, "use_rerank": False, "rewrite": "smart", "skip_rerank_when_clear": True},
    "balanced": {"use_bm25": True, "use_rerank": True, "rewrite": "smart", "skip_rerank_when_clear": True},
    "accurate": {"use_bm25": True, "use_rerank": True, "rewrite": "always", "skip_rerank_when_clear": False},
}


@dataclass(frozen=True)
class Options:
    mode: str                     # fast | balanced | accurate | legacy (benchmark dùng cờ USE_*)
    use_bm25: bool
    use_rerank: bool
    rewrite: str                  # "off" | "smart" (chỉ khi câu hỏi phụ thuộc hội thoại) | "always"
    skip_rerank_when_clear: bool  # câu hỏi vị trí + vector và BM25 cùng chọn 1 đoạn -> không rerank
    top_k_retrieve: int
    top_k_context: int
    min_vector_score: float       # ngưỡng tin cậy (không rerank)
    min_rerank_score: float       # ngưỡng tin cậy (có rerank)
    hard_vector_score: float      # ngưỡng cứng: thấp hơn thì từ chối ngay, không hỏi model
    hard_rerank_score: float
    history_turns: int


def tuning_from_config() -> dict:
    """Các tham số số (ngưỡng, số đoạn...) lấy từ .env — giá trị mặc định của trang Cài đặt."""
    return {
        "top_k_retrieve": config.TOP_K_RETRIEVE,
        "top_k_context": config.TOP_K_CONTEXT,
        "min_vector_score": config.MIN_VECTOR_SCORE,
        "min_rerank_score": config.MIN_RERANK_SCORE,
        "hard_vector_score": config.HARD_VECTOR_SCORE,
        "hard_rerank_score": config.HARD_RERANK_SCORE,
        "history_turns": config.HISTORY_TURNS,
    }


def for_mode(mode: str, tuning: dict | None = None) -> Options:
    if mode not in _PRESETS:
        mode = "balanced"
    return Options(mode=mode, **_PRESETS[mode], **{**tuning_from_config(), **(tuning or {})})


def from_config() -> Options:
    """Dùng khi gọi pipeline trực tiếp (benchmark): đọc config tại thời điểm gọi."""
    if config.MODE in _PRESETS:
        return for_mode(config.MODE)
    return Options(  # cách cũ: theo từng cờ USE_* trong .env
        mode="legacy",
        use_bm25=config.USE_BM25,
        use_rerank=config.USE_RERANK,
        rewrite="always" if config.USE_REWRITE else "off",
        skip_rerank_when_clear=False,
        **tuning_from_config(),
    )


__all__ = ["MODES", "MODE_INFO", "Options", "for_mode", "from_config", "replace"]

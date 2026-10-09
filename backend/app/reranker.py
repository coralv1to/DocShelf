from sentence_transformers import CrossEncoder

from . import config

_model: CrossEncoder | None = None
_loaded_key: tuple | None = None  # cấu hình của model đang nạp, để biết khi nào cần nạp lại


def _get_model() -> CrossEncoder:
    """Nạp model khi cần; nạp lại nếu cấu hình (tên model, thiết bị, max_length) đã đổi."""
    global _model, _loaded_key
    key = (config.RERANK_MODEL, config.RERANK_DEVICE, config.RERANK_MAX_LENGTH, config.RERANK_TRUST_REMOTE_CODE)
    if _model is None or key != _loaded_key:
        _model = CrossEncoder(
            config.RERANK_MODEL,
            device=config.RERANK_DEVICE,
            max_length=config.RERANK_MAX_LENGTH,
            trust_remote_code=config.RERANK_TRUST_REMOTE_CODE,
        )
        _loaded_key = key
    return _model


def rerank(query: str, candidates: list[tuple[int, str]]) -> list[tuple[int, float]]:
    """candidates: [(vị_trí_đoạn, nội_dung)]. Trả về [(vị_trí_đoạn, điểm)] giảm dần."""
    if not candidates:
        return []
    model = _get_model()
    scores = model.predict([(query, text) for _, text in candidates])
    ranked = sorted(zip((i for i, _ in candidates), scores), key=lambda x: -x[1])
    return [(int(i), float(s)) for i, s in ranked]

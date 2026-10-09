"""Cài đặt do admin chỉnh trên giao diện (trang Cài đặt), lưu trong bảng app_settings.

Giá trị chưa từng được lưu thì lấy mặc định từ .env. Đổi trên giao diện có hiệu lực ngay ở câu hỏi tiếp theo,
không cần khởi động lại backend.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import config
from . import options as opts_mod
from .models import AppSetting

# Mô tả từng cài đặt: kiểu, giới hạn, giải thích (giao diện dùng để dựng form)
SPEC: dict[str, dict] = {
    "default_mode": {
        "type": "mode",
        "label": "Chế độ trả lời mặc định",
        "help": "Áp dụng cho mọi câu hỏi, trừ khi người dùng tự chọn chế độ khác (nếu được phép).",
    },
    "allow_user_mode": {
        "type": "bool",
        "label": "Cho người dùng tự chọn chế độ",
        "help": "Bật: ô chat có nút chọn Nhanh / Cân bằng / Kỹ. Tắt: mọi người dùng chế độ mặc định.",
    },
    "top_k_retrieve": {
        "type": "int", "min": 3, "max": 30,
        "label": "Số đoạn tìm ban đầu",
        "help": "Số đoạn lấy ra ở bước tìm kiếm để rerank. Nhiều hơn: ít bỏ sót hơn nhưng rerank chậm hơn "
                "(~1 giây/đoạn trên CPU).",
    },
    "top_k_context": {
        "type": "int", "min": 1, "max": 8,
        "label": "Số đoạn đưa cho model",
        "help": "Số đoạn tốt nhất đưa cho model đọc để trả lời. Nhiều hơn: đủ ngữ cảnh hơn nhưng model đọc lâu hơn.",
    },
    "min_vector_score": {
        "type": "float", "min": 0.0, "max": 1.0, "step": 0.01,
        "label": "Ngưỡng từ chối khi không rerank",
        "help": "Điểm tìm kiếm theo nghĩa (cosine) thấp hơn ngưỡng thì từ chối. Cao hơn: ít bịa hơn, "
                "nhưng dễ từ chối nhầm.",
    },
    "min_rerank_score": {
        "type": "float", "min": 0.0, "max": 1.0, "step": 0.01,
        "label": "Ngưỡng từ chối khi có rerank",
        "help": "Điểm rerank thấp hơn ngưỡng thì từ chối. Cao hơn: ít bịa hơn, nhưng dễ từ chối nhầm.",
    },
    "history_turns": {
        "type": "int", "min": 0, "max": 10,
        "label": "Số lượt hội thoại nhớ",
        "help": "Số cặp hỏi-đáp gần nhất dùng để hiểu câu hỏi nối tiếp. 0 = không nhớ.",
    },
}


def defaults() -> dict:
    mode = config.DEFAULT_MODE if config.DEFAULT_MODE in opts_mod.MODES else "balanced"
    return {"default_mode": mode, "allow_user_mode": True, **opts_mod.tuning_from_config()}


def get_all(db: Session) -> dict:
    values = defaults()
    for row in db.query(AppSetting).all():
        if row.key in SPEC:
            values[row.key] = row.value
    return values


def _validate(key: str, value):
    spec = SPEC.get(key)
    if spec is None:
        raise HTTPException(400, f"Không có cài đặt '{key}'.")
    kind = spec["type"]
    if kind == "mode":
        if value not in opts_mod.MODES:
            raise HTTPException(400, f"Chế độ không hợp lệ: {value}")
        return value
    if kind == "bool":
        if not isinstance(value, bool):
            raise HTTPException(400, f"'{spec['label']}' phải là bật/tắt.")
        return value
    try:
        num = int(value) if kind == "int" else float(value)
    except (TypeError, ValueError):
        raise HTTPException(400, f"'{spec['label']}' phải là số.")
    if not spec["min"] <= num <= spec["max"]:
        raise HTTPException(400, f"'{spec['label']}' phải trong khoảng {spec['min']} – {spec['max']}.")
    return num


def update(db: Session, changes: dict) -> dict:
    clean = {k: _validate(k, v) for k, v in changes.items()}
    merged = {**get_all(db), **clean}
    if merged["top_k_context"] > merged["top_k_retrieve"]:
        raise HTTPException(400, "Số đoạn đưa cho model không được lớn hơn số đoạn tìm ban đầu.")
    for key, value in clean.items():
        row = db.get(AppSetting, key)
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return get_all(db)


def reset(db: Session) -> dict:
    db.query(AppSetting).delete()
    db.commit()
    return get_all(db)


def options_for(db: Session, requested_mode: str | None) -> opts_mod.Options:
    """Options cho một câu hỏi: chế độ người dùng chọn (nếu được phép) hoặc chế độ mặc định."""
    values = get_all(db)
    mode = values["default_mode"]
    if requested_mode and values["allow_user_mode"]:
        if requested_mode not in opts_mod.MODES:
            raise HTTPException(400, f"Chế độ không hợp lệ: {requested_mode}. Chọn: {', '.join(opts_mod.MODES)}")
        mode = requested_mode
    tuning = {k: values[k] for k in opts_mod.tuning_from_config()}
    return opts_mod.for_mode(mode, tuning)


def public_info(db: Session) -> dict:
    """Thông tin chế độ cho mọi người dùng (không lộ các ngưỡng)."""
    values = get_all(db)
    return {
        "default_mode": values["default_mode"],
        "allow_user_mode": values["allow_user_mode"],
        "modes": [{"id": m, **opts_mod.MODE_INFO[m]} for m in opts_mod.MODES],
    }

"""Kết nối Postgres bằng SQLAlchemy.

- engine: "đường ống" tới database, tạo một lần cho cả ứng dụng (có pool kết nối bên trong).
- SessionLocal: mỗi lần làm việc với DB thì mở một Session (giống một phiên giao dịch), xong thì đóng.
- get_db: dependency cho FastAPI — mỗi request nhận một Session riêng, request xong tự đóng.
"""
from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from . import config

# pool_pre_ping: trước khi dùng một kết nối cũ trong pool thì "ping" thử,
# tránh lỗi khi Postgres vừa khởi động lại (vd tắt/mở Docker Desktop).
# pool_size / max_overflow: số kết nối DB mỗi tiến trình backend giữ sẵn / được mở thêm khi đông.
# Nhiều worker thì tổng = số worker × (pool_size + max_overflow), phải nhỏ hơn max_connections của Postgres (100).
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
)

# expire_on_commit=False: sau commit vẫn đọc được thuộc tính của object mà không phải query lại
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Lớp cha của mọi bảng (xem models.py)."""

    # Quy ước đặt tên khóa/ràng buộc: Alembic cần tên cố định để sau này sửa hoặc xóa được ràng buộc
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

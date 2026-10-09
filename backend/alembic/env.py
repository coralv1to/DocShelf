"""Alembic: quản lý thay đổi cấu trúc bảng theo từng "phiên bản" (migration).

Lệnh thường dùng (trong backend/, đã activate .venv):
    alembic upgrade head                          # tạo / cập nhật bảng lên bản mới nhất
    alembic revision --autogenerate -m "mô tả"    # sau khi sửa app/models.py: sinh migration mới
    alembic downgrade -1                          # quay lại 1 bản
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import config as app_config
from app import models  # noqa: F401  (import để các bảng được đăng ký vào Base.metadata)
from app.db import Base

config = context.config
config.set_main_option("sqlalchemy.url", app_config.DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Các bảng trong database. Mỗi class = một bảng, mỗi thuộc tính Mapped[...] = một cột.

Quan hệ:
    users 1 ── n chat_sessions 1 ── n messages
    documents 1 ── n chunks
    documents 1 ── n chat_sessions
    api_clients 1 ── n documents, chat_sessions   (hệ thống ngoài tích hợp qua /api/v1)

Tách dữ liệu: tài liệu có api_client_id = NULL là tài liệu của kệ nội bộ (giao diện DocShelf);
tài liệu của một hệ thống ngoài chỉ hệ thống đó thấy được.

Thay đổi cấu trúc bảng thì KHÔNG sửa DB bằng tay: sửa file này rồi tạo migration Alembic
(xem backend/alembic/README.md).
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id() -> str:
    """Mã 32 ký tự hex (uuid4 bỏ dấu gạch) — cùng dạng với doc_id cũ trong thư mục data/."""
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    full_name: Mapped[str] = mapped_column(String(100), default="")
    password_hash: Mapped[str] = mapped_column(String(100))  # bcrypt, KHÔNG bao giờ lưu mật khẩu gốc
    role: Mapped[str] = mapped_column(String(10), default="user")  # "admin" | "user"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiClient(Base):
    """Một hệ thống ngoài được cấp API key (vd hệ thống quản lý đào tạo gọi DocShelf)."""

    __tablename__ = "api_clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    key_prefix: Mapped[str] = mapped_column(String(12))  # vài ký tự đầu của key, để nhận diện khi liệt kê
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 của key, KHÔNG lưu key gốc
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        # Cùng một file chỉ có 1 bản trong mỗi "kệ" (kệ nội bộ, hoặc kệ riêng của từng hệ thống ngoài).
        # nulls_not_distinct: coi NULL (kệ nội bộ) là bằng nhau, để chặn trùng cả ở kệ nội bộ.
        UniqueConstraint("file_sha256", "api_client_id", postgresql_nulls_not_distinct=True),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(300))
    filename: Mapped[str] = mapped_column(String(300))
    # Mã băm nội dung file: cùng một file upload 2 lần sẽ bị chặn
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    num_pages: Mapped[int] = mapped_column(Integer, default=0)
    num_chunks: Mapped[int] = mapped_column(Integer, default=0)
    embed_model: Mapped[str] = mapped_column(String(100))  # model đã dùng để embed: đổi model thì phải index lại
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    api_client_id: Mapped[int | None] = mapped_column(ForeignKey("api_clients.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # cascade: xóa tài liệu thì xóa luôn các đoạn và các cuộc trò chuyện về tài liệu đó
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Chunk.position",
        passive_deletes=True,  # để Postgres tự xóa theo (ON DELETE CASCADE), nhanh hơn xóa từng dòng
    )
    uploader: Mapped[User | None] = relationship()


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)      # thứ tự đoạn trong tài liệu (0, 1, 2...)
    chunk_key: Mapped[str] = mapped_column(String(20))  # "c0", "c1"... hoặc "overview" (chunker.Chunk.id)
    text: Mapped[str] = mapped_column(Text)
    header: Mapped[str] = mapped_column(Text)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    # Vector() không ghi số chiều: đổi sang embedding model khác số chiều không cần sửa bảng.
    # Đổi lại không tạo được index HNSW — không sao, vì mỗi lần chỉ tìm trong 1 tài liệu (vài trăm đoạn).
    embedding = mapped_column(Vector())
    # Kết quả tách từ tiếng Việt cho BM25 (các token cách nhau bởi dấu cách), tính sẵn lúc upload
    search_tokens: Mapped[str | None] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="chunks")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    # Chủ cuộc trò chuyện: người dùng nội bộ (user_id), HOẶC hệ thống ngoài (api_client_id + user_ref)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    api_client_id: Mapped[int | None] = mapped_column(ForeignKey("api_clients.id"), index=True)
    user_ref: Mapped[str | None] = mapped_column(String(100))  # mã người dùng bên hệ thống ngoài (tùy chọn)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))  # lấy từ câu hỏi đầu tiên
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Message.id", passive_deletes=True
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)     # nội dung hiển thị đầy đủ
    # Bản ngắn đưa vào lịch sử khi viết lại câu hỏi tiếp theo (câu từ chối / dàn ý dài làm rối LLM)
    history_text: Mapped[str] = mapped_column(Text, default="")
    # False với câu chào/cảm ơn/chửi...: vẫn hiện trên giao diện nhưng không đưa vào lịch sử cho LLM
    in_context: Mapped[bool] = mapped_column(Boolean, default=True)
    found: Mapped[bool | None] = mapped_column(Boolean)
    citations: Mapped[list | None] = mapped_column(JSONB)
    debug: Mapped[dict | None] = mapped_column(JSONB)  # giữ cả câu trích bị từ chối để chẩn đoán
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class AppSetting(Base):
    """Cài đặt do admin chỉnh trên giao diện (chế độ trả lời mặc định, ngưỡng...). Mỗi dòng một khóa."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

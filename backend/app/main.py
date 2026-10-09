import hashlib
import logging
import os
import re
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from . import api_v1, app_settings, auth, chat_service, config, locate, pipeline, store, warmup
from .auth import AdminUser, CurrentUser
from .db import engine, get_db
from .models import ChatSession, Document, Message

log = logging.getLogger("docshelf")

DOC_ID_RE = re.compile(r"^[0-9a-f]{32}$")
MAX_UPLOAD_MB = 20

DB = Annotated[Session, Depends(get_db)]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Kiểm tra cấu hình ngay khi khởi động, để lỗi hiện rõ thay vì hỏng ở request đầu tiên."""
    auth._secret()  # thiếu JWT_SECRET -> báo lỗi kèm cách tạo
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as e:
        raise RuntimeError(
            "Không kết nối được Postgres. Kiểm tra Docker Desktop đang chạy và đã `docker compose up -d`, "
            f"DATABASE_URL trong .env đúng chưa. Chi tiết: {e.orig}"
        ) from None
    warmup.start_in_background()  # nạp sẵn model + tài liệu, chạy ngầm
    yield


app = FastAPI(title="DocShelf API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(api_v1.router)  # API cho hệ thống ngoài, xem docs/02-production-va-tich-hop-api.md


def _check_doc_id(doc_id: str) -> None:
    if not DOC_ID_RE.match(doc_id):
        raise HTTPException(400, "doc_id không hợp lệ.")


def _get_doc(db: Session, doc_id: str) -> Document:
    """Tài liệu trên kệ nội bộ. Tài liệu của hệ thống ngoài (qua /api/v1) không truy cập được ở đây."""
    _check_doc_id(doc_id)
    doc = db.get(Document, doc_id)
    if doc is None or doc.api_client_id is not None:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    return doc



def _doc_info(doc: Document) -> dict:
    return {
        "doc_id": doc.id,
        "title": doc.title,
        "filename": doc.filename,
        "num_chunks": doc.num_chunks,
        "num_pages": doc.num_pages,
        "uploaded_by": (doc.uploader.full_name or doc.uploader.username) if doc.uploader else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "has_source": store.source_pdf(doc.id).exists(),
    }


# ==================================================================== hệ thống
@app.get("/api/health")
def health(db: DB):
    return {
        "status": "ok",
        "chat_model": config.CHAT_MODEL,
        "embed_model": config.EMBED_MODEL,
        "default_mode": app_settings.get_all(db)["default_mode"],
    }


# ==================================================================== cài đặt
@app.get("/api/settings")
def public_settings(_user: CurrentUser, db: DB):
    """Các chế độ trả lời + chế độ mặc định + người dùng có được tự chọn không."""
    return app_settings.public_info(db)


@app.get("/api/admin/settings")
def admin_get_settings(_admin: AdminUser, db: DB):
    return {
        "values": app_settings.get_all(db),
        "defaults": app_settings.defaults(),
        "spec": app_settings.SPEC,
        "modes": app_settings.public_info(db)["modes"],
    }


@app.put("/api/admin/settings")
def admin_update_settings(changes: dict, _admin: AdminUser, db: DB):
    app_settings.update(db, changes)
    return admin_get_settings(_admin, db)


@app.post("/api/admin/settings/reset")
def admin_reset_settings(_admin: AdminUser, db: DB):
    app_settings.reset(db)
    return admin_get_settings(_admin, db)


# ==================================================================== kệ tài liệu
@app.get("/api/documents")
def list_documents(_user: CurrentUser, db: DB):
    docs = db.scalars(
        select(Document).where(Document.api_client_id.is_(None)).order_by(Document.created_at.desc())
    ).all()
    return [_doc_info(d) for d in docs]


@app.post("/api/documents")
def upload_document(admin: AdminUser, db: DB, file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Chỉ hỗ trợ file PDF.")

    data = file.file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File vượt quá {MAX_UPLOAD_MB}MB.")

    sha = hashlib.sha256(data).hexdigest()
    existing = store.find_by_sha256(db, sha)
    if existing is not None:
        raise HTTPException(409, f"Tài liệu này đã có trên kệ: “{existing.title}”.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        index = pipeline.ingest_pdf(
            tmp_path, title=Path(filename).stem, filename=filename, file_sha256=sha, uploaded_by=admin.id
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except IntegrityError:  # hai người cùng upload một file một lúc
        raise HTTPException(409, "Tài liệu này đã có trên kệ.")
    finally:
        os.remove(tmp_path)

    db.expire_all()  # tài liệu vừa được ghi bằng session khác (trong store.py) -> đọc lại
    return _doc_info(_get_doc(db, index.doc_id))


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str, _user: CurrentUser, db: DB):
    return _doc_info(_get_doc(db, doc_id))


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str, _admin: AdminUser, db: DB):
    doc = _get_doc(db, doc_id)
    pipeline.forget_document(doc_id)
    store.delete_document(db, doc)
    return {"ok": True}


@app.get("/api/documents/{doc_id}/pages/{page}/image")
def page_image(doc_id: str, page: int, _user: CurrentUser):
    _check_doc_id(doc_id)
    pdf = store.source_pdf(doc_id)
    if not pdf.exists():
        raise HTTPException(404, "Không có file PDF gốc. Hãy upload lại tài liệu.")
    try:
        png = locate.render_page_png(pdf, page)
    except IndexError as e:
        raise HTTPException(404, str(e))
    # Trang PDF không bao giờ đổi -> cho trình duyệt cache 1 ngày
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})


# ==================================================================== cuộc trò chuyện
def _get_own_session(db: Session, session_id: str, user_id: int) -> ChatSession:
    chat = db.get(ChatSession, session_id) if DOC_ID_RE.match(session_id) else None
    # Không phải của mình thì báo "không tìm thấy" (không tiết lộ là phiên đó tồn tại)
    if chat is None or chat.user_id != user_id:
        raise HTTPException(404, "Không tìm thấy cuộc trò chuyện.")
    return chat


def _session_info(chat: ChatSession, num_messages: int | None = None) -> dict:
    info = {
        "session_id": chat.id,
        "doc_id": chat.document_id,
        "title": chat.title,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
    }
    if num_messages is not None:
        info["num_messages"] = num_messages
    return info


@app.get("/api/sessions")
def list_sessions(user: CurrentUser, db: DB, doc_id: str | None = None):
    """Các cuộc trò chuyện của chính người đang đăng nhập (lọc theo tài liệu nếu có doc_id)."""
    q = select(ChatSession).where(ChatSession.user_id == user.id)
    if doc_id:
        _check_doc_id(doc_id)
        q = q.where(ChatSession.document_id == doc_id)
    chats = db.scalars(q.order_by(ChatSession.updated_at.desc()).limit(100)).all()
    return [_session_info(c) for c in chats]


@app.get("/api/sessions/{session_id}/messages")
def get_messages(session_id: str, user: CurrentUser, db: DB):
    chat = _get_own_session(db, session_id, user.id)
    out = []
    for m in chat.messages:
        item = {"role": m.role, "content": m.content}
        if m.role == "assistant":
            # Dựng lại đúng dạng kết quả /api/chat để giao diện hiển thị nguồn, nhãn từ chối...
            item["result"] = {
                "answer": m.content,
                "found": bool(m.found),
                "citations": m.citations or [],
                "debug": m.debug or {},
            }
        out.append(item)
    return {"session": _session_info(chat, len(out)), "messages": out}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, user: CurrentUser, db: DB):
    chat = _get_own_session(db, session_id, user.id)
    db.delete(chat)
    db.commit()
    return {"ok": True}


class ChatRequest(BaseModel):
    doc_id: str
    session_id: str | None = Field(default=None, max_length=32)  # None = bắt đầu cuộc trò chuyện mới
    question: str = Field(min_length=1, max_length=2000)
    mode: Literal["fast", "balanced", "accurate"] | None = None  # fast | balanced | accurate; None = chế độ mặc định


@app.post("/api/chat")
def chat(req: ChatRequest, user: CurrentUser, db: DB):
    doc = _get_doc(db, req.doc_id)
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Câu hỏi trống.")
    chat_service.check_embed_model(doc)

    # Lấy (hoặc tạo) cuộc trò chuyện
    if req.session_id:
        chat_session = _get_own_session(db, req.session_id, user.id)
        if chat_session.document_id != doc.id:
            raise HTTPException(400, "Cuộc trò chuyện này thuộc tài liệu khác.")
    else:
        chat_session = ChatSession(user_id=user.id, document_id=doc.id, title=chat_service.make_title(question))
        db.add(chat_session)
        db.commit()

    result = chat_service.ask(db, doc, chat_session, question, mode=req.mode)
    return {**result, "session": _session_info(chat_session)}


# Đếm nhanh (dùng cho trang quản trị sau này)
@app.get("/api/stats")
def stats(_admin: AdminUser, db: DB):
    return {
        "documents": db.scalar(select(func.count(Document.id))),
        "sessions": db.scalar(select(func.count(ChatSession.id))),
        "messages": db.scalar(select(func.count(Message.id))),
    }

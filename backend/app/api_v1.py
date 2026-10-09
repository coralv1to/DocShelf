"""API tích hợp cho hệ thống ngoài: /api/v1/...

Xác thực bằng header  X-API-Key: dsk_...   (tạo key: python -m app.cli create-api-key <tên>)

Luồng điển hình (chi tiết + ví dụ: docs/02-production-va-tich-hop-api.md):
  1. Backend hệ thống ngoài nhận file từ người dùng -> POST /api/v1/documents -> nhận doc_id, lưu vào DB của họ.
  2. Người dùng bấm vào file để chat -> POST /api/v1/chat với doc_id (+ session_id để hỏi tiếp)
     -> câu trả lời chỉ dựa trên đúng tài liệu đó, kèm trích dẫn và số trang.

Tách dữ liệu: mỗi API client chỉ thấy tài liệu và cuộc trò chuyện do chính nó tạo ra.
"""
import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import chat_service, config, locate, pipeline, store
from .db import get_db
from .models import ApiClient, ChatSession, Document

router = APIRouter(prefix="/api/v1", tags=["Tích hợp (API key)"])

ID_RE = re.compile(r"^[0-9a-f]{32}$")
MAX_UPLOAD_MB = config.MAX_UPLOAD_MB

DB = Annotated[Session, Depends(get_db)]


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def get_api_client(db: DB, x_api_key: Annotated[str | None, Header()] = None) -> ApiClient:
    if not x_api_key:
        raise HTTPException(401, "Thiếu header X-API-Key.")
    client = db.scalar(select(ApiClient).where(ApiClient.key_hash == hash_key(x_api_key)))
    if client is None or not client.is_active:
        raise HTTPException(401, "API key không hợp lệ hoặc đã bị thu hồi.")
    client.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return client


Client = Annotated[ApiClient, Depends(get_api_client)]


def _get_doc(db: Session, client: ApiClient, doc_id: str) -> Document:
    doc = db.get(Document, doc_id) if ID_RE.match(doc_id) else None
    if doc is None or doc.api_client_id != client.id:  # tài liệu của client khác coi như không tồn tại
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    return doc


def _doc_out(doc: Document, duplicate: bool = False) -> dict:
    return {
        "doc_id": doc.id,
        "title": doc.title,
        "filename": doc.filename,
        "num_pages": doc.num_pages,
        "num_chunks": doc.num_chunks,
        "embed_model": doc.embed_model,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "duplicate": duplicate,
    }


def _get_session(db: Session, client: ApiClient, session_id: str, user_ref: str | None) -> ChatSession:
    chat = db.get(ChatSession, session_id) if ID_RE.match(session_id) else None
    if chat is None or chat.api_client_id != client.id:
        raise HTTPException(404, "Không tìm thấy cuộc trò chuyện.")
    # Cuộc trò chuyện gắn với một người dùng bên hệ thống ngoài: người khác không mở được
    if chat.user_ref is not None and user_ref != chat.user_ref:
        raise HTTPException(404, "Không tìm thấy cuộc trò chuyện.")
    return chat


def _citation_out(c: dict) -> dict:
    return {
        "quote": c["quote"],
        "page": c["page"],
        "section": c.get("section", ""),
        "rects": c.get("rects", []),  # vùng cần tô trên ảnh trang: [x0, y0, x1, y1], tỉ lệ 0..1
    }


# ==================================================================== tài liệu
@router.post("/documents", status_code=status.HTTP_201_CREATED)
def upload_document(
    response: Response,
    client: Client,
    db: DB,
    file: UploadFile = File(...),
    title: str | None = Form(default=None, max_length=300),
):
    """Upload PDF. Trả về doc_id để hệ thống ngoài lưu lại.

    Gửi lại đúng file đã có -> trả về tài liệu cũ (HTTP 200, duplicate = true), không index lại.
    """
    filename = Path(file.filename or "document.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Chỉ hỗ trợ file PDF.")
    data = file.file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File vượt quá {MAX_UPLOAD_MB}MB.")

    sha = hashlib.sha256(data).hexdigest()
    existing = store.find_by_sha256(db, sha, client.id)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return _doc_out(existing, duplicate=True)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        index = pipeline.ingest_pdf(
            tmp_path,
            title=(title or "").strip() or Path(filename).stem,
            filename=filename,
            file_sha256=sha,
            api_client_id=client.id,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except IntegrityError:  # cùng file được gửi 2 lần cùng lúc
        db.rollback()
        existing = store.find_by_sha256(db, sha, client.id)
        if existing is None:
            raise
        response.status_code = status.HTTP_200_OK
        return _doc_out(existing, duplicate=True)
    finally:
        os.remove(tmp_path)

    db.expire_all()
    return _doc_out(_get_doc(db, client, index.doc_id))


@router.get("/documents")
def list_documents(client: Client, db: DB, limit: int = 100, offset: int = 0):
    docs = db.scalars(
        select(Document)
        .where(Document.api_client_id == client.id)
        .order_by(Document.created_at.desc())
        .limit(min(limit, 500))
        .offset(offset)
    ).all()
    return [_doc_out(d) for d in docs]


@router.get("/documents/{doc_id}")
def get_document(doc_id: str, client: Client, db: DB):
    return _doc_out(_get_doc(db, client, doc_id))


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, client: Client, db: DB):
    """Xóa tài liệu + mọi cuộc trò chuyện về tài liệu đó."""
    doc = _get_doc(db, client, doc_id)
    pipeline.forget_document(doc.id)
    store.delete_document(db, doc)
    return {"ok": True}


@router.get("/documents/{doc_id}/pages/{page}/image")
def page_image(doc_id: str, page: int, client: Client, db: DB):
    """Ảnh PNG của một trang (để hiện trang nguồn và tô vùng trích dẫn)."""
    doc = _get_doc(db, client, doc_id)
    pdf = store.source_pdf(doc.id)
    if not pdf.exists():
        raise HTTPException(404, "Không có file PDF gốc.")
    try:
        png = locate.render_page_png(pdf, page)
    except IndexError as e:
        raise HTTPException(404, str(e))
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})


# ==================================================================== hỏi đáp
class ChatIn(BaseModel):
    doc_id: str
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=32)  # None = bắt đầu cuộc trò chuyện mới
    user_ref: str | None = Field(default=None, max_length=100)    # mã người dùng bên hệ thống ngoài
    mode: Literal["fast", "balanced", "accurate"] | None = None                                        # fast | balanced | accurate; None = mặc định
    include_debug: bool = False                                    # true: trả thêm thông tin chẩn đoán


@router.post("/chat")
def chat(req: ChatIn, client: Client, db: DB):
    doc = _get_doc(db, client, req.doc_id)
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Câu hỏi trống.")
    chat_service.check_embed_model(doc)

    if req.session_id:
        chat_session = _get_session(db, client, req.session_id, req.user_ref)
        if chat_session.document_id != doc.id:
            raise HTTPException(400, "Cuộc trò chuyện này thuộc tài liệu khác.")
    else:
        chat_session = ChatSession(
            api_client_id=client.id, user_ref=req.user_ref, document_id=doc.id,
            title=chat_service.make_title(question),
        )
        db.add(chat_session)
        db.commit()

    result = chat_service.ask(db, doc, chat_session, question, mode=req.mode)
    debug = result["debug"]
    out = {
        "session_id": chat_session.id,
        "doc_id": doc.id,
        "answer": result["answer"],
        "found": result["found"],
        # Khi found = false: not_in_doc | unsure | unverified | figure | chitchat
        "refusal_kind": None if result["found"] else debug.get("refusal_kind"),
        "mode": debug.get("mode"),
        "citations": [_citation_out(c) for c in result["citations"]],
        # Ví dụ minh họa do model tự nghĩ (KHÔNG có trong tài liệu) khi người dùng xin ví dụ; null nếu không có.
        # Hệ thống ngoài nên hiển thị tách riêng và ghi rõ nhãn này.
        "example": result.get("example"),
        # high = đoạn tìm được khớp rõ với câu hỏi; medium = khớp yếu hơn, nên khuyên người dùng mở nguồn kiểm tra
        "confidence": debug.get("confidence") if result["found"] else None,
    }
    if req.include_debug:
        out["debug"] = debug
    return out


@router.get("/sessions")
def list_sessions(client: Client, db: DB, doc_id: str | None = None, user_ref: str | None = None):
    q = select(ChatSession).where(ChatSession.api_client_id == client.id)
    if doc_id:
        q = q.where(ChatSession.document_id == doc_id)
    if user_ref:
        q = q.where(ChatSession.user_ref == user_ref)
    chats = db.scalars(q.order_by(ChatSession.updated_at.desc()).limit(100)).all()
    return [
        {"session_id": c.id, "doc_id": c.document_id, "user_ref": c.user_ref, "title": c.title,
         "updated_at": c.updated_at.isoformat() if c.updated_at else None}
        for c in chats
    ]


@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str, client: Client, db: DB, user_ref: str | None = None):
    chat = _get_session(db, client, session_id, user_ref)
    return {
        "session_id": chat.id,
        "doc_id": chat.document_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                **(
                    {"found": bool(m.found), "citations": [_citation_out(c) for c in (m.citations or [])]}
                    if m.role == "assistant"
                    else {}
                ),
            }
            for m in chat.messages
        ],
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, client: Client, db: DB, user_ref: str | None = None):
    chat = _get_session(db, client, session_id, user_ref)
    db.delete(chat)
    db.commit()
    return {"ok": True}

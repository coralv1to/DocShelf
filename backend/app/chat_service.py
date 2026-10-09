"""Logic hỏi đáp dùng chung cho giao diện DocShelf (/api/chat) và API tích hợp (/api/v1/chat).

Một lượt hỏi:
  1. Đọc lịch sử cuộc trò chuyện từ DB (bỏ các lượt chào hỏi)
  2. Chạy pipeline RAG trên đúng một tài liệu
  3. Lưu câu hỏi + câu trả lời vào DB
"""
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import app_settings, config, pipeline
from .models import ChatSession, Document, Message

SESSION_TITLE_MAX = 80


def check_embed_model(doc: Document) -> None:
    """Câu hỏi phải được embed bằng đúng model đã dùng khi index tài liệu, nếu không kết quả tìm kiếm vô nghĩa."""
    if doc.embed_model != config.EMBED_MODEL:
        raise HTTPException(
            409,
            f"Tài liệu được index bằng {doc.embed_model}, hệ thống đang dùng {config.EMBED_MODEL}. "
            "Quản trị viên cần chạy: python -m app.cli reindex --all",
        )


def make_title(question: str) -> str:
    return question if len(question) <= SESSION_TITLE_MAX else question[: SESSION_TITLE_MAX - 1] + "…"


def ask(db: Session, doc: Document, chat_session: ChatSession, question: str, mode: str | None = None) -> dict:
    """Trả lời `question` trong `chat_session` (đã tồn tại trong DB). Trả về kết quả pipeline.

    mode: chế độ người dùng chọn (fast | balanced | accurate); None = chế độ mặc định trong trang Cài đặt.
    """
    check_embed_model(doc)
    opts = app_settings.options_for(db, mode)

    # Lịch sử cho LLM: lượt hỏi + bản ngắn của câu trả lời, bỏ các lượt chào hỏi (in_context = False)
    rows = db.scalars(
        select(Message)
        .where(Message.session_id == chat_session.id, Message.in_context.is_(True))
        .order_by(Message.id.desc())
        .limit(max(opts.history_turns, 1) * 2)
    ).all()
    history = [{"role": m.role, "content": m.history_text or m.content} for m in reversed(rows)]
    db.commit()  # kết thúc giao dịch đọc: trả kết nối DB về pool trong lúc chờ LLM (có thể 10-20 giây)

    try:
        result = pipeline.answer_question(doc.id, chat_session.id, question, history=history, opts=opts)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except ConnectionError:
        raise HTTPException(503, "Không kết nối được Ollama. Kiểm tra Ollama đang chạy chưa.")

    history_answer = result.pop("history_answer", None)
    in_context = history_answer is not None  # None = câu chào hỏi/cảm ơn: hiện trên giao diện, không đưa cho LLM
    db.add_all([
        Message(session_id=chat_session.id, role="user", content=question, history_text=question,
                in_context=in_context),
        Message(session_id=chat_session.id, role="assistant", content=result["answer"],
                history_text=history_answer or "", in_context=in_context, found=result["found"],
                citations=result["citations"], debug=result["debug"]),
    ])
    chat_session.updated_at = func.now()
    db.commit()
    db.refresh(chat_session)  # đọc lại updated_at do Postgres vừa ghi
    return result

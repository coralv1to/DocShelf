"""Lưu / nạp tài liệu đã index.

Trước: mỗi tài liệu là một thư mục data/<doc_id>/ gồm meta.json + embeddings.npy.
Giờ:   nội dung đoạn văn + vector nằm trong Postgres (bảng documents, chunks).
       Thư mục data/<doc_id>/ chỉ còn file PDF gốc (source.pdf) để hiển thị trang nguồn.

Phần còn lại của ứng dụng (pipeline.py, benchmark) vẫn làm việc với DocumentIndex
y như cũ, nên không phải sửa gì khi đổi cách lưu trữ.
"""
import shutil
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .chunker import Chunk
from .db import SessionLocal
from .models import Chunk as ChunkRow
from .models import Document


class DocumentIndex:
    def __init__(
        self,
        doc_id: str,
        title: str,
        chunks: list[Chunk],
        embeddings: np.ndarray,
        tokens: list[list[str]] | None = None,
    ):
        self.doc_id = doc_id
        self.title = title
        self.chunks = chunks
        self.embeddings = embeddings  # ma trận (số_đoạn × số_chiều), đã chuẩn hóa
        self.tokens = tokens          # token tiếng Việt của từng đoạn cho BM25 (tách sẵn, lưu trong DB)
        self.bm25 = None              # dựng từ self.tokens ở lần tìm kiếm đầu tiên (rất nhanh)

    def get_tokens(self) -> list[list[str]]:
        if self.tokens is None:
            self.tokens = tokenize_chunks(self.chunks)
        return self.tokens

    def vector_search(self, query_vec: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        """Trả về [(vị_trí_đoạn, điểm_cosine)] sắp xếp giảm dần."""
        scores = self.embeddings @ query_vec
        order = np.argsort(-scores)[:top_k]
        return [(int(i), float(scores[i])) for i in order]


# Cache trong RAM: nạp từ DB một lần, các câu hỏi sau dùng lại (kèm cả BM25 đã dựng).
_cache: dict[str, DocumentIndex] = {}


def tokenize_chunks(chunks: list[Chunk]) -> list[list[str]]:
    """Tách từ tiếng Việt cho BM25 (underthesea, mất vài giây với tài liệu dài)."""
    from .bm25 import tokenize_vi  # import khi cần: underthesea nạp khá lâu

    return [tokenize_vi(c.text_for_search()) for c in chunks]


def doc_dir(doc_id: str) -> Path:
    return Path(config.DATA_DIR) / doc_id


def source_pdf(doc_id: str) -> Path:
    """Đường dẫn file PDF gốc của tài liệu."""
    return doc_dir(doc_id) / "source.pdf"


def save_index(
    index: DocumentIndex,
    pdf_path: str | Path,
    *,
    filename: str,
    num_pages: int,
    file_sha256: str | None = None,
    uploaded_by: int | None = None,
    api_client_id: int | None = None,
) -> None:
    """Ghi tài liệu + các đoạn + vector vào DB, chép PDF gốc vào data/<doc_id>/source.pdf."""
    tokens = index.get_tokens()  # tách từ ngay lúc upload, lần hỏi đầu tiên không phải chờ
    folder = doc_dir(index.doc_id)
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pdf_path, source_pdf(index.doc_id))
    try:
        with SessionLocal() as db:
            doc = Document(
                id=index.doc_id,
                title=index.title,
                filename=filename,
                file_sha256=file_sha256,
                num_pages=num_pages,
                num_chunks=len(index.chunks),
                embed_model=config.EMBED_MODEL,
                uploaded_by=uploaded_by,
                api_client_id=api_client_id,
            )
            doc.chunks = [
                ChunkRow(
                    position=pos,
                    chunk_key=c.id,
                    text=c.text,
                    header=c.header,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    embedding=index.embeddings[pos],
                    search_tokens=" ".join(tokens[pos]),
                )
                for pos, c in enumerate(index.chunks)
            ]
            db.add(doc)
            db.commit()
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)  # ghi DB lỗi thì không để lại file mồ côi
        raise
    _cache[index.doc_id] = index


def replace_chunks(index: DocumentIndex) -> None:
    """Thay toàn bộ đoạn của một tài liệu ĐÃ CÓ (đọc lại PDF bằng bộ cắt đoạn mới).

    Giữ nguyên doc_id, file PDF và các cuộc trò chuyện; chỉ thay bảng chunks.
    """
    tokens = index.get_tokens()
    with SessionLocal() as db:
        doc = db.get(Document, index.doc_id)
        if doc is None:
            raise ValueError(f"Không có tài liệu {index.doc_id}")
        db.query(ChunkRow).filter(ChunkRow.document_id == index.doc_id).delete()
        db.add_all([
            ChunkRow(
                document_id=index.doc_id,
                position=pos,
                chunk_key=c.id,
                text=c.text,
                header=c.header,
                page_start=c.page_start,
                page_end=c.page_end,
                embedding=index.embeddings[pos],
                search_tokens=" ".join(tokens[pos]),
            )
            for pos, c in enumerate(index.chunks)
        ])
        doc.num_chunks = len(index.chunks)
        doc.embed_model = config.EMBED_MODEL
        db.commit()
    _cache[index.doc_id] = index


def load_index(doc_id: str) -> DocumentIndex | None:
    if doc_id in _cache:
        return _cache[doc_id]
    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        if doc is None:
            return None
        rows = db.scalars(
            select(ChunkRow).where(ChunkRow.document_id == doc_id).order_by(ChunkRow.position)
        ).all()
        chunks = [
            Chunk(id=r.chunk_key, text=r.text, header=r.header, page_start=r.page_start, page_end=r.page_end)
            for r in rows
        ]
        # pgvector trả mỗi vector về dạng numpy array -> xếp chồng thành ma trận
        embeddings = np.stack([np.asarray(r.embedding, dtype=np.float32) for r in rows])
        index = DocumentIndex(doc_id=doc.id, title=doc.title, chunks=chunks, embeddings=embeddings)

        # Token BM25: tài liệu upload trước khi có cột search_tokens thì tách từ một lần rồi lưu lại
        if any(r.search_tokens is None for r in rows):
            tokens = index.get_tokens()
            for r, t in zip(rows, tokens):
                r.search_tokens = " ".join(t)
            db.commit()
        else:
            index.tokens = [r.search_tokens.split() for r in rows]
    _cache[doc_id] = index
    return index


def find_by_sha256(db: Session, sha: str, api_client_id: int | None = None) -> Document | None:
    """Tìm tài liệu cùng nội dung trong cùng một kệ (kệ nội bộ nếu api_client_id là None)."""
    owner = Document.api_client_id.is_(None) if api_client_id is None else Document.api_client_id == api_client_id
    return db.scalar(select(Document).where(Document.file_sha256 == sha, owner))


def evict(doc_id: str) -> None:
    """Bỏ tài liệu khỏi cache RAM (vd sau khi index lại) để lần hỏi sau nạp lại từ DB."""
    _cache.pop(doc_id, None)


def delete_document(db: Session, doc: Document) -> None:
    """Xóa tài liệu khỏi DB (các đoạn + cuộc trò chuyện xóa theo), xóa file PDF và cache."""
    doc_id = doc.id
    db.delete(doc)
    db.commit()
    shutil.rmtree(doc_dir(doc_id), ignore_errors=True)
    _cache.pop(doc_id, None)

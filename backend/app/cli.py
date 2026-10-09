"""Lệnh quản trị chạy từ dòng lệnh (trong backend/, đã activate .venv).

    python -m app.cli create-user admin --role admin --name "Quản trị viên"
    python -m app.cli create-user sv01 --name "Nguyễn Văn A"
    python -m app.cli set-password sv01
    python -m app.cli set-active sv01 --off        # khóa tài khoản (--on để mở lại)
    python -m app.cli list-users
    python -m app.cli import-legacy                # chuyển tài liệu cũ trong data/ vào database

    python -m app.cli create-api-key he-thong-dao-tao   # cấp API key cho hệ thống ngoài (key chỉ hiện 1 lần)
    python -m app.cli list-api-keys
    python -m app.cli revoke-api-key he-thong-dao-tao   # thu hồi key

    python -m app.cli reindex --all                # embed lại mọi tài liệu sau khi đổi EMBED_MODEL
    python -m app.cli reindex --doc <doc_id>
    python -m app.cli reparse --all                # đọc lại PDF gốc bằng bộ cắt đoạn mới (sau khi nâng cấp code)
    python -m app.cli reparse --doc <doc_id>

Mật khẩu được hỏi bằng getpass: gõ không hiện chữ, không lưu vào lịch sử lệnh.
"""
import argparse
import getpass
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path

import numpy as np
from sqlalchemy import func, select

from . import chunker, config, embedder, locate
from .api_v1 import hash_key
from .auth import hash_password
from .db import SessionLocal
from .models import ApiClient, Chunk, Document, User

USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,50}$")
MIN_PASSWORD = 8


def _ask_password() -> str:
    while True:
        pw = getpass.getpass(f"Mật khẩu (tối thiểu {MIN_PASSWORD} ký tự): ")
        if len(pw) < MIN_PASSWORD:
            print("  Mật khẩu quá ngắn.")
            continue
        if getpass.getpass("Nhập lại mật khẩu: ") != pw:
            print("  Hai lần nhập không khớp.")
            continue
        return pw


def _find_user(db, username: str) -> User:
    user = db.scalar(select(User).where(User.username == username.lower()))
    if user is None:
        sys.exit(f"Không có tài khoản '{username}'.")
    return user


def create_user(args) -> None:
    username = args.username.strip().lower()
    if not USERNAME_RE.match(username):
        sys.exit("Tên đăng nhập 3-50 ký tự, chỉ gồm a-z, 0-9, dấu chấm, gạch dưới, gạch ngang.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)):
            sys.exit(f"Tài khoản '{username}' đã tồn tại. Đổi mật khẩu: python -m app.cli set-password {username}")
        password = _ask_password()
        db.add(User(username=username, full_name=args.name or "", password_hash=hash_password(password),
                    role=args.role))
        db.commit()
    print(f"Đã tạo tài khoản '{username}' (quyền: {args.role}).")


def set_password(args) -> None:
    with SessionLocal() as db:
        user = _find_user(db, args.username)
        user.password_hash = hash_password(_ask_password())
        db.commit()
    print(f"Đã đổi mật khẩu cho '{user.username}'.")


def set_active(args) -> None:
    with SessionLocal() as db:
        user = _find_user(db, args.username)
        user.is_active = args.on
        db.commit()
    print(f"Tài khoản '{user.username}': {'đang hoạt động' if args.on else 'đã khóa'}.")


def list_users(_args) -> None:
    with SessionLocal() as db:
        users = db.scalars(select(User).order_by(User.id)).all()
    if not users:
        print("Chưa có tài khoản nào. Tạo admin: python -m app.cli create-user admin --role admin")
    for u in users:
        state = "" if u.is_active else "  [đã khóa]"
        print(f"{u.id:>3}  {u.username:<20} {u.role:<6} {u.full_name}{state}")


def import_legacy(_args) -> None:
    """Đọc data/<doc_id>/meta.json + embeddings.npy (cách lưu cũ) rồi ghi vào database.

    Không phải embed lại. Thư mục giữ nguyên (source.pdf vẫn được dùng để hiện trang nguồn);
    sau khi kiểm tra ổn có thể xóa meta.json và embeddings.npy.
    """
    root = Path(config.DATA_DIR)
    folders = sorted(p for p in root.iterdir() if (p / "meta.json").exists()) if root.exists() else []
    if not folders:
        print(f"Không thấy tài liệu cũ nào trong {root.resolve()}.")
        return
    with SessionLocal() as db:
        for folder in folders:
            doc_id = folder.name
            if db.get(Document, doc_id) is not None:
                print(f"- {doc_id}: đã có trong database, bỏ qua")
                continue
            meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
            vectors = np.load(folder / "embeddings.npy")
            pdf = folder / "source.pdf"
            sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else None
            if sha and db.scalar(select(Document).where(Document.file_sha256 == sha)):
                print(f"- {doc_id}: trùng nội dung với một tài liệu đã nhập, bỏ qua")
                continue
            doc = Document(
                id=doc_id,
                title=meta["title"],
                filename=f"{meta['title']}.pdf",
                file_sha256=sha,
                num_pages=locate.page_count(pdf) if pdf.exists() else 0,
                num_chunks=len(meta["chunks"]),
                embed_model=config.EMBED_MODEL,
            )
            doc.chunks = [
                Chunk(position=i, chunk_key=c["id"], text=c["text"], header=c["header"],
                      page_start=c["page_start"], page_end=c["page_end"], embedding=vectors[i])
                for i, c in enumerate(meta["chunks"])
            ]
            db.add(doc)
            db.commit()
            note = "" if pdf.exists() else "  (không có PDF gốc: không xem được trang nguồn)"
            print(f"+ {doc_id}: “{meta['title']}”, {len(meta['chunks'])} đoạn{note}")
    print("Xong.")


def create_api_key(args) -> None:
    name = args.name.strip().lower()
    if not USERNAME_RE.match(name):
        sys.exit("Tên 3-50 ký tự, chỉ gồm a-z, 0-9, dấu chấm, gạch dưới, gạch ngang.")
    key = "dsk_" + secrets.token_urlsafe(32)  # 256 bit ngẫu nhiên
    with SessionLocal() as db:
        if db.scalar(select(ApiClient).where(ApiClient.name == name)):
            sys.exit(f"Đã có client '{name}'. Thu hồi trước: python -m app.cli revoke-api-key {name}")
        db.add(ApiClient(name=name, key_prefix=key[:12], key_hash=hash_key(key)))
        db.commit()
    print(f"Đã tạo API key cho '{name}'. Key chỉ hiện MỘT LẦN, hãy lưu lại ngay:\n\n    {key}\n")
    print("Hệ thống ngoài gửi kèm header:  X-API-Key: <key>")


def list_api_keys(_args) -> None:
    with SessionLocal() as db:
        clients = db.scalars(select(ApiClient).order_by(ApiClient.id)).all()
        if not clients:
            print("Chưa có API key nào.")
        for c in clients:
            n = db.scalar(select(func.count(Document.id)).where(Document.api_client_id == c.id))
            used = c.last_used_at.strftime("%d/%m/%Y %H:%M") if c.last_used_at else "chưa dùng"
            state = "" if c.is_active else "  [đã thu hồi]"
            print(f"{c.id:>3}  {c.name:<25} {c.key_prefix}…  {n} tài liệu  lần cuối: {used}{state}")


def revoke_api_key(args) -> None:
    with SessionLocal() as db:
        c = db.scalar(select(ApiClient).where(ApiClient.name == args.name.lower()))
        if c is None:
            sys.exit(f"Không có client '{args.name}'.")
        c.is_active = False
        db.commit()
    print(f"Đã thu hồi key của '{c.name}'. Tài liệu của client này vẫn giữ trong database.")


def reindex(args) -> None:
    """Embed lại các đoạn đã lưu bằng EMBED_MODEL hiện tại (không cần đọc lại PDF)."""
    with SessionLocal() as db:
        q = select(Document)
        if args.doc:
            q = q.where(Document.id == args.doc)
        elif not args.force:
            q = q.where(Document.embed_model != config.EMBED_MODEL)  # chỉ những tài liệu đang lệch model
        docs = db.scalars(q.order_by(Document.created_at)).all()
        if not docs:
            print(f"Không có tài liệu nào cần index lại (đều đang dùng {config.EMBED_MODEL}).")
            return
        print(f"Index lại {len(docs)} tài liệu bằng {config.EMBED_MODEL}...")
        for doc in docs:
            rows = db.scalars(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.position)).all()
            texts = [
                chunker.Chunk(id=r.chunk_key, text=r.text, header=r.header, page_start=r.page_start,
                              page_end=r.page_end).text_for_search()
                for r in rows
            ]
            vectors = embedder.embed_documents(texts)
            for r, v in zip(rows, vectors):
                r.embedding = v
            old = doc.embed_model
            doc.embed_model = config.EMBED_MODEL
            db.commit()
            print(f"  ✓ {doc.title} ({len(rows)} đoạn, {old} -> {config.EMBED_MODEL})")
    print("Xong. Khởi động lại backend để bỏ cache cũ trong RAM.")


def reparse(args) -> None:
    """Đọc lại PDF gốc + cắt đoạn lại + embed lại. Giữ nguyên tài liệu và các cuộc trò chuyện."""
    from . import pipeline

    with SessionLocal() as db:
        q = select(Document)
        if args.doc:
            q = q.where(Document.id == args.doc)
        docs = db.scalars(q.order_by(Document.created_at)).all()
    if not docs:
        print("Không có tài liệu nào.")
        return
    print(f"Đọc lại {len(docs)} tài liệu...")
    for doc in docs:
        try:
            index = pipeline.reparse_document(doc.id, doc.title)
            print(f"  ✓ {doc.title}: {doc.num_chunks} -> {len(index.chunks)} đoạn")
        except ValueError as e:
            print(f"  ✗ {doc.title}: {e}")
    print("Xong. Khởi động lại backend để bỏ cache cũ trong RAM.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Quản trị DocShelf")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-user", help="Tạo tài khoản")
    p.add_argument("username")
    p.add_argument("--role", choices=["admin", "user"], default="user")
    p.add_argument("--name", help="Họ tên hiển thị")
    p.set_defaults(func=create_user)

    p = sub.add_parser("set-password", help="Đổi mật khẩu")
    p.add_argument("username")
    p.set_defaults(func=set_password)

    p = sub.add_parser("set-active", help="Khóa / mở khóa tài khoản")
    p.add_argument("username")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--on", dest="on", action="store_true")
    g.add_argument("--off", dest="on", action="store_false")
    p.set_defaults(func=set_active)

    sub.add_parser("list-users", help="Liệt kê tài khoản").set_defaults(func=list_users)
    sub.add_parser("import-legacy", help="Chuyển tài liệu cũ trong data/ vào database").set_defaults(
        func=import_legacy
    )

    p = sub.add_parser("create-api-key", help="Cấp API key cho hệ thống ngoài")
    p.add_argument("name", help="Tên hệ thống, vd he-thong-dao-tao")
    p.set_defaults(func=create_api_key)
    sub.add_parser("list-api-keys", help="Liệt kê API key").set_defaults(func=list_api_keys)
    p = sub.add_parser("revoke-api-key", help="Thu hồi API key")
    p.add_argument("name")
    p.set_defaults(func=revoke_api_key)

    p = sub.add_parser("reindex", help="Embed lại tài liệu (sau khi đổi EMBED_MODEL)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="Mọi tài liệu đang lệch model")
    g.add_argument("--doc", help="Một tài liệu theo doc_id")
    p.add_argument("--force", action="store_true", help="Cùng --all: embed lại cả tài liệu đã đúng model")
    p.set_defaults(func=reindex)

    p = sub.add_parser("reparse", help="Đọc lại PDF gốc bằng bộ cắt đoạn mới (sau khi nâng cấp code)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="Mọi tài liệu")
    g.add_argument("--doc", help="Một tài liệu theo doc_id")
    p.set_defaults(func=reparse)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

"""Đăng nhập + phân quyền.

Luồng:
  1. POST /api/auth/login  (username, password)
     -> kiểm tra mật khẩu bằng bcrypt
     -> tạo JWT (chuỗi ký số chứa user id + hạn dùng)
     -> gửi JWT về trong cookie httpOnly (JavaScript trên trang không đọc được -> khó bị đánh cắp)
        và trong JSON (cho script/benchmark gọi API bằng header Authorization).
  2. Mọi request sau: trình duyệt tự gửi kèm cookie. get_current_user đọc cookie (hoặc header),
     kiểm tra chữ ký + hạn dùng, rồi nạp user từ DB.
  3. require_admin: như trên nhưng chỉ cho role "admin".

Vì sao dùng cookie thay vì lưu token trong localStorage: thẻ <img src="/api/.../image"> để hiện trang PDF
không gửi được header Authorization, nhưng cookie thì trình duyệt tự gửi.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import User

COOKIE_NAME = "docshelf_token"
ALGORITHM = "HS256"

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------- mật khẩu
def hash_password(password: str) -> str:
    # bcrypt tự sinh "muối" ngẫu nhiên: cùng mật khẩu nhưng mỗi lần băm ra chuỗi khác nhau
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


# ---------------------------------------------------------------- token
def _secret() -> str:
    if len(config.JWT_SECRET) < 32:
        raise RuntimeError(
            "Chưa đặt JWT_SECRET (>= 32 ký tự) trong backend/.env. "
            "Tạo bằng: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    return config.JWT_SECRET


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),  # "subject": token này thuộc về user nào
        "role": user.role,
        "iat": now,           # thời điểm tạo
        "exp": now + timedelta(minutes=config.JWT_EXPIRE_MINUTES),  # hết hạn -> phải đăng nhập lại
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def _read_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(COOKIE_NAME)


# ---------------------------------------------------------------- dependency cho các API khác
def get_current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    token = _read_token(request)
    if not token:
        raise HTTPException(401, "Bạn chưa đăng nhập.")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn, hãy đăng nhập lại.")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Phiên đăng nhập không hợp lệ, hãy đăng nhập lại.")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(401, "Tài khoản không tồn tại hoặc đã bị khóa.")
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Chỉ quản trị viên được làm thao tác này.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]


def user_info(user: User) -> dict:
    return {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}


# ---------------------------------------------------------------- API
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


@router.post("/login")
def login(req: LoginRequest, response: Response, db: Annotated[Session, Depends(get_db)]):
    user = db.scalar(select(User).where(User.username == req.username.strip().lower()))
    # Cùng một thông báo cho "sai tên" và "sai mật khẩu": không để lộ tên đăng nhập nào tồn tại
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu.")
    if not user.is_active:
        raise HTTPException(403, "Tài khoản đã bị khóa.")
    token = create_token(user)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=config.JWT_EXPIRE_MINUTES * 60,
        httponly=True,                 # JavaScript không đọc được cookie này
        samesite="lax",                # trang web khác không gửi kèm cookie khi POST sang đây
        secure=config.COOKIE_SECURE,   # True: chỉ gửi qua HTTPS
        path="/",
    )
    return {"user": user_info(user), "access_token": token}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: CurrentUser):
    return user_info(user)

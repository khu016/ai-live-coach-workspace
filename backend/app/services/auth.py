"""邀请测试版账号与服务端会话。"""

import hashlib
import secrets
from datetime import timedelta

from fastapi import Depends, HTTPException, Request, WebSocket
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db import SessionLocal, get_db
from ..models import AuthSession, User, now


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_nickname(value: str) -> str:
    nickname = " ".join(value.strip().split())
    if not nickname:
        raise HTTPException(status_code=400, detail="请输入昵称")
    return nickname[:40]


def login_with_invite(db: Session, invite_code: str, nickname: str) -> tuple[User, str]:
    code = invite_code.strip()
    if not settings.invite_codes:
        raise HTTPException(status_code=503, detail="邀请登录尚未配置")
    if code not in settings.invite_codes:
        raise HTTPException(status_code=401, detail="邀请码无效")

    code_hash = _hash(code)
    user = db.query(User).filter_by(invite_code_hash=code_hash).first()
    clean_name = normalize_nickname(nickname)
    if user is None:
        user = User(nickname=clean_name, invite_code_hash=code_hash)
        db.add(user)
        db.flush()
    elif user.nickname != clean_name:
        user.nickname = clean_name

    raw_token = secrets.token_urlsafe(32)
    session = AuthSession(
        user_id=user.id,
        token_hash=_hash(raw_token),
        expires_at=now() + timedelta(days=settings.session_ttl_days),
    )
    db.add(session)
    db.commit()
    db.refresh(user)
    return user, raw_token


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = (
        db.query(AuthSession)
        .filter_by(token_hash=_hash(token), revoked_at=None)
        .first()
    )
    if session is None or session.expires_at <= now():
        return None
    return db.get(User, session.user_id)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = user_for_token(db, request.cookies.get(settings.session_cookie_name))
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def websocket_user(websocket: WebSocket) -> User | None:
    db = SessionLocal()
    try:
        return user_for_token(db, websocket.cookies.get(settings.session_cookie_name))
    finally:
        db.close()


def revoke_token(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.query(AuthSession).filter_by(token_hash=_hash(token)).first()
    if session is not None and session.revoked_at is None:
        session.revoked_at = now()
        db.commit()


def user_dict(user: User) -> dict:
    return {"id": user.id, "nickname": user.nickname}

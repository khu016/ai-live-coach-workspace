from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db import get_db
from ..models import User
from ..schemas import InviteLoginIn
from ..services.auth import current_user, login_with_invite, revoke_token, user_dict

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/invite")
def invite_login(payload: InviteLoginIn, response: Response, db: Session = Depends(get_db)):
    user, token = login_with_invite(db, payload.invite_code, payload.nickname)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"user": user_dict(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"user": user_dict(user)}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    revoke_token(db, request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"logged_out": True}

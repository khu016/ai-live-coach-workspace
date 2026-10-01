from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db import get_db
from ..models import AdminSession, User
from ..schemas import AdminLoginIn, AnalyticsEventIn
from ..services.analytics import (
    analytics_summary,
    create_admin_session,
    current_admin,
    record_event,
    revoke_admin_session,
)
from ..services.auth import current_user

router = APIRouter(tags=["analytics"])


@router.post("/analytics/events")
def create_event(
    payload: AnalyticsEventIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    event = record_event(
        db,
        payload.event_name,
        user_id=user.id,
        route=payload.route,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        session_id=payload.session_id,
        properties=payload.properties,
    )
    return {"accepted": True, "event_id": event.id}


@router.post("/admin/login")
def admin_login(payload: AdminLoginIn, response: Response, db: Session = Depends(get_db)):
    token = create_admin_session(db, payload.access_code)
    response.set_cookie(
        key=settings.admin_session_cookie_name,
        value=token,
        max_age=settings.admin_session_ttl_hours * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )
    return {"authenticated": True}


@router.get("/admin/me")
def admin_me(_: AdminSession = Depends(current_admin)):
    return {"authenticated": True}


@router.post("/admin/logout")
def admin_logout(request: Request, response: Response, db: Session = Depends(get_db)):
    revoke_admin_session(db, request.cookies.get(settings.admin_session_cookie_name))
    response.delete_cookie(settings.admin_session_cookie_name, path="/")
    return {"logged_out": True}


@router.get("/admin/analytics/summary")
def summary(
    days: int = Query(default=7),
    db: Session = Depends(get_db),
    _: AdminSession = Depends(current_admin),
):
    return analytics_summary(db, days)

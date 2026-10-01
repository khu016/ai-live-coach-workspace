"""NIVI 第一方埋点、管理员会话与汇总指标。"""

import hashlib
import hmac
import secrets
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db import get_db
from ..models import (
    AdminSession,
    AnalyticsEvent,
    BulletEvent,
    Recording,
    Training,
    User,
    now,
)

ALLOWED_EVENTS = {
    "page_view",
    "login_success",
    "login_failed",
    "training_created",
    "training_started",
    "training_completed",
    "report_viewed",
    "retrain_started",
    "tutorial_viewed",
    "tutorial_completed",
    "asr_started",
    "asr_failed",
}

ALLOWED_PROPERTY_KEYS = {
    "practice_mode",
    "live_type",
    "media_kind",
    "status",
    "error_code",
    "source",
    "tutorial_id",
    "duration_sec",
}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sanitize_properties(properties: dict | None) -> dict:
    clean = {}
    for key, value in (properties or {}).items():
        if key not in ALLOWED_PROPERTY_KEYS:
            continue
        if value is None or isinstance(value, (str, int, float, bool)):
            clean[key] = value if not isinstance(value, str) else value[:160]
    return clean


def record_event(
    db: Session,
    event_name: str,
    *,
    user_id: int | None = None,
    route: str | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    session_id: str | None = None,
    properties: dict | None = None,
    commit: bool = True,
) -> AnalyticsEvent:
    if event_name not in ALLOWED_EVENTS:
        raise HTTPException(status_code=400, detail="不支持的埋点事件")
    event = AnalyticsEvent(
        user_id=user_id,
        event_name=event_name,
        route=(route or "")[:240] or None,
        entity_type=(entity_type or "")[:32] or None,
        entity_id=(str(entity_id)[:64] if entity_id is not None else None),
        session_id=(session_id or "")[:64] or None,
        properties=sanitize_properties(properties),
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event


def create_admin_session(db: Session, access_code: str) -> str:
    configured = settings.admin_access_code
    if not configured:
        raise HTTPException(status_code=503, detail="管理员看板尚未配置")
    if not hmac.compare_digest(access_code.strip(), configured):
        raise HTTPException(status_code=401, detail="管理员口令错误")
    raw_token = secrets.token_urlsafe(32)
    db.add(
        AdminSession(
            token_hash=_hash(raw_token),
            expires_at=now() + timedelta(hours=settings.admin_session_ttl_hours),
        )
    )
    db.commit()
    return raw_token


def current_admin(request: Request, db: Session = Depends(get_db)) -> AdminSession:
    token = request.cookies.get(settings.admin_session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="请先验证管理员身份")
    session = (
        db.query(AdminSession)
        .filter_by(token_hash=_hash(token), revoked_at=None)
        .first()
    )
    if session is None or session.expires_at <= now():
        raise HTTPException(status_code=401, detail="管理员会话已失效")
    return session


def revoke_admin_session(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.query(AdminSession).filter_by(token_hash=_hash(token)).first()
    if session is not None and session.revoked_at is None:
        session.revoked_at = now()
        db.commit()


def _day_key(value: datetime) -> str:
    return value.strftime("%m-%d")


def analytics_summary(db: Session, days: int = 7) -> dict:
    days = 30 if days == 30 else 7
    end = now()
    start = end - timedelta(days=days)
    events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.created_at >= start, AnalyticsEvent.created_at <= end)
        .order_by(AnalyticsEvent.created_at.asc())
        .all()
    )
    trainings = db.query(Training).filter(Training.created_at >= start).all()
    completed = [t for t in trainings if t.finished_at and t.status == "feedback_ready"]
    training_ids = [t.id for t in completed]
    durations = []
    if training_ids:
        durations = [
            row[0] or 0.0
            for row in db.query(Recording.duration_sec)
            .filter(Recording.training_id.in_(training_ids))
            .all()
        ]

    event_counts = defaultdict(int)
    active_user_ids = set()
    for event in events:
        event_counts[event.event_name] += 1
        if event.user_id is not None:
            active_user_ids.add(event.user_id)
    active_user_ids.update(t.user_id for t in trainings)

    daily = []
    for offset in range(days - 1, -1, -1):
        day = (end - timedelta(days=offset)).date()
        day_events = [e for e in events if e.created_at.date() == day]
        day_trainings = [t for t in trainings if t.created_at.date() == day]
        daily.append(
            {
                "date": day.isoformat(),
                "label": day.strftime("%m/%d"),
                "active_users": len({e.user_id for e in day_events if e.user_id}),
                "page_views": sum(e.event_name == "page_view" for e in day_events),
                "trainings": len(day_trainings),
            }
        )

    def users_for(name: str) -> set[int]:
        return {e.user_id for e in events if e.event_name == name and e.user_id}

    created_users = {t.user_id for t in trainings}
    completed_users = {t.user_id for t in completed}
    total_users = db.query(User).count()
    new_users = db.query(User).filter(User.created_at >= start).count()
    dynamic_bullets = 0
    if training_ids:
        dynamic_bullets = (
            db.query(BulletEvent)
            .filter(BulletEvent.training_id.in_(training_ids))
            .filter(BulletEvent.kind == "dynamic")
            .count()
        )

    recent_events = [
        {
            "id": e.id,
            "event_name": e.event_name,
            "user_id": e.user_id,
            "route": e.route,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "properties": e.properties or {},
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in reversed(events[-30:])
    ]
    return {
        "range_days": days,
        "generated_at": end.isoformat(),
        "metrics": {
            "total_users": total_users,
            "new_users": new_users,
            "active_users": len(active_user_ids),
            "page_views": event_counts["page_view"],
            "training_created": len(trainings),
            "training_completed": len(completed),
            "completion_rate": round(len(completed) / len(trainings), 4) if trainings else None,
            "practice_minutes": round(sum(durations) / 60, 1),
            "tutorial_views": event_counts["tutorial_viewed"],
            "tutorial_completed": event_counts["tutorial_completed"],
            "report_views": event_counts["report_viewed"],
            "retrain_count": event_counts["retrain_started"],
            "asr_started": event_counts["asr_started"],
            "asr_failed": event_counts["asr_failed"],
            "dynamic_bullets": dynamic_bullets,
        },
        "funnel": [
            {"key": "login", "label": "登录用户", "users": len(users_for("login_success"))},
            {"key": "created", "label": "创建练习", "users": len(created_users)},
            {"key": "completed", "label": "完成练习", "users": len(completed_users)},
            {"key": "report", "label": "查看报告", "users": len(users_for("report_viewed"))},
            {"key": "retrain", "label": "发起重练", "users": len(users_for("retrain_started"))},
        ],
        "daily": daily,
        "recent_events": recent_events,
    }

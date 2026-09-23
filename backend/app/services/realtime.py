"""实时转写会话的落库与消息封装。

稳定转写片段（kind="final"）落库为 ``TranscriptSegment``；临时片段只回推，
不落库。动态弹幕落库为 ``BulletEvent``（带证据链字段）。落库用独立会话，
避免与 WebSocket 主协程共享 SQLAlchemy Session。
"""

from ..db import SessionLocal
from ..models import BulletEvent, TranscriptSegment

# PCM 16kHz/16bit 单声道 = 32000 字节/秒，用于由已收音频字节数推算音频时间轴
PCM_BYTES_PER_SEC = 32000


def save_segment(training_id: int, event) -> int:
    """把稳定转写事件落库，返回片段 id。"""
    db = SessionLocal()
    try:
        seg = TranscriptSegment(
            training_id=training_id,
            source="realtime",
            start_sec=event.start_sec,
            end_sec=event.end_sec,
            text=event.text,
            seq=event.seq,
        )
        db.add(seg)
        db.commit()
        return seg.id
    finally:
        db.close()


def link_segment_to_pending_bullets(
    training_id: int, segment_id: int, seg_start_sec: float
) -> None:
    """把稳定转写片段关联到当时待回应且展示窗口内的弹幕（PRD 4.4）。

    无法可靠关联时不计为已回应；这里只做确定性时间窗口关联，
    写入 ``response_segment_ids``，供真实统计计算回应及时率与平均回应时间。
    """
    if seg_start_sec is None:
        return
    from ..core.config import settings

    db = SessionLocal()
    try:
        bullets = (
            db.query(BulletEvent)
            .filter(
                BulletEvent.training_id == training_id,
                BulletEvent.requires_response.is_(True),
                BulletEvent.display_at.isnot(None),
            )
            .all()
        )
        window = settings.response_window_sec
        changed = False
        for b in bullets:
            delta = seg_start_sec - b.display_at
            if 0 <= delta <= window:
                ids = list(b.response_segment_ids or [])
                if segment_id not in ids:
                    ids.append(segment_id)
                    b.response_segment_ids = ids
                    changed = True
        if changed:
            db.commit()
    finally:
        db.close()


def save_bullet(training_id: int, draft) -> dict:
    """把弹幕落库，返回可直接推给浏览器的消息字典。"""
    db = SessionLocal()
    try:
        b = BulletEvent(
            training_id=training_id,
            kind="dynamic",
            text=draft.text,
            at_sec=draft.at_sec,
            source=_source_for(draft),
            scenario_id=draft.scenario_id,
            trigger_type=draft.trigger_type,
            trigger_segment_id=draft.trigger_segment_id,
            trigger_reason=draft.trigger_reason,
            status=draft.status,
            bullet_category=getattr(draft, "bullet_category", None),
            requires_response=getattr(draft, "requires_response", None),
            scorable=getattr(draft, "scorable", None),
            difficulty=getattr(draft, "difficulty", None),
            display_at=draft.at_sec,
            meta=getattr(draft, "meta", None),
        )
        db.add(b)
        db.commit()
        # 互动回应：回填 engagement_call 的 bullet_ids 与 shown_at
        meta = getattr(draft, "meta", None) or {}
        call_id = meta.get("engagement_call_id")
        if call_id is not None:
            try:
                from .engagement import record_engagement_bullet

                record_engagement_bullet(call_id, b.id)
            except Exception:  # noqa: BLE001
                pass
        return bullet_to_message(b)
    finally:
        db.close()


def _source_for(draft) -> str:
    """弹幕来源：优先用分类（更有信息量），兜底用状态。"""
    cat = getattr(draft, "bullet_category", None)
    if cat:
        return cat
    return "fallback" if getattr(draft, "status", None) == "fallback" else "dynamic"


def event_to_message(event) -> dict:
    return {
        "type": "transcript",
        "kind": event.kind,
        "text": event.text,
        "start_sec": event.start_sec,
        "end_sec": event.end_sec,
        "seq": event.seq,
    }


def bullet_to_message(b) -> dict:
    return {
        "type": "bullet",
        "text": b.text,
        "at_sec": b.display_at if b.display_at is not None else b.at_sec,
        "kind": b.kind,
        "scenario_id": b.scenario_id,
        "trigger_type": b.trigger_type,
        "trigger_reason": b.trigger_reason,
        "status": b.status,
        "bullet_category": b.bullet_category,
        "requires_response": b.requires_response,
        "scorable": b.scorable,
        "difficulty": b.difficulty,
    }

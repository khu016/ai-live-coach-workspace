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


def save_bullet(training_id: int, draft) -> dict:
    """把动态弹幕落库，返回可直接推给浏览器的消息字典。"""
    db = SessionLocal()
    try:
        b = BulletEvent(
            training_id=training_id,
            kind="dynamic",
            text=draft.text,
            at_sec=draft.at_sec,
            source=_source_for(draft.status),
            scenario_id=draft.scenario_id,
            trigger_type=draft.trigger_type,
            trigger_segment_id=draft.trigger_segment_id,
            trigger_reason=draft.trigger_reason,
            status=draft.status,
        )
        db.add(b)
        db.commit()
        return bullet_to_message(b)
    finally:
        db.close()


def _source_for(status: str) -> str:
    if status == "fallback":
        return "fallback"
    return "dynamic"


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
        "at_sec": b.at_sec,
        "kind": b.kind,
        "scenario_id": b.scenario_id,
        "trigger_type": b.trigger_type,
        "trigger_reason": b.trigger_reason,
        "status": b.status,
    }

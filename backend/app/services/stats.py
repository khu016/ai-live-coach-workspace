"""真实训练统计（首页与成长数据）。

从持久化训练、录像、转写、弹幕事件计算，不使用模拟数字补位。
时间范围按用户时区自然周（默认 Asia/Shanghai，周一为一周开始）。

指标口径（PRD 4.4）：
- 本周训练次数：当前自然周内 status=feedback_ready 的训练数。
- 本周训练时长：当前自然周已保存媒体的 duration_sec 之和。
- 需回应弹幕数：requires_response=true 且 scorable=true 且已展示的弹幕数。
- 已回应数：上述弹幕中已关联至少一个有效稳定转写回应片段的数量。
- 回应及时率：已在回应窗口内关联回应片段的弹幕数 ÷ 需回应弹幕数。
- 平均回应时间：弹幕 display_at 到首个有效回应片段开始时间的平均秒数。
- 较上周变化：当前周与上一自然周均有足够样本时计算。
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ..core.config import settings
from ..db import SessionLocal
from ..models import BulletEvent, Recording, TranscriptSegment, Training

TZ = ZoneInfo("Asia/Shanghai")
MIN_SAMPLE = 3  # 需回应弹幕少于 3 条时显示"数据不足"


def _week_bounds_utc_naive(offset_weeks: int = 0):
    """返回某自然周（周一 00:00 起，Asia/Shanghai）对应的 UTC naive 边界。"""
    now = datetime.now(TZ)
    monday = (now - timedelta(days=now.weekday())).date()
    start_local = datetime(monday.year, monday.month, monday.day, 0, 0, 0, tzinfo=TZ)
    start_local += timedelta(weeks=offset_weeks)
    end_local = start_local + timedelta(days=7)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _training_ids_in_range(start_utc, end_utc):
    db = SessionLocal()
    try:
        rows = (
            db.query(Training.id)
            .filter(Training.status == "feedback_ready")
            .filter(Training.finished_at >= start_utc)
            .filter(Training.finished_at < end_utc)
            .all()
        )
        return [r[0] for r in rows]
    finally:
        db.close()


def _week_stats(start_utc, end_utc):
    db = SessionLocal()
    try:
        ids = [
            r[0]
            for r in db.query(Training.id)
            .filter(Training.status == "feedback_ready")
            .filter(Training.finished_at >= start_utc)
            .filter(Training.finished_at < end_utc)
            .all()
        ]
        training_count = len(ids)

        total_duration = 0.0
        if ids:
            dur_rows = (
                db.query(Recording.duration_sec)
                .filter(Recording.training_id.in_(ids))
                .all()
            )
            total_duration = sum(
                (r[0] or 0.0) for r in dur_rows
            )

        bullets = []
        seg_map = {}
        if ids:
            bullet_rows = (
                db.query(BulletEvent)
                .filter(BulletEvent.training_id.in_(ids))
                .filter(BulletEvent.requires_response.is_(True))
                .filter(BulletEvent.scorable.is_(True))
                .all()
            )
            bullets = bullet_rows
            seg_rows = (
                db.query(TranscriptSegment)
                .filter(TranscriptSegment.training_id.in_(ids))
                .all()
            )
            for s in seg_rows:
                seg_map[s.id] = s

        required = len(bullets)
        responded = 0
        timely = 0
        resp_times = []
        window = settings.response_window_sec
        for b in bullets:
            seg_ids = [i for i in (b.response_segment_ids or []) if i in seg_map]
            if not seg_ids:
                continue
            responded += 1
            starts = [
                seg_map[i].start_sec
                for i in seg_ids
                if seg_map[i].start_sec is not None
            ]
            if not starts:
                continue
            first_start = min(starts)
            if b.display_at is not None:
                delta = first_start - b.display_at
                if 0 <= delta <= window:
                    timely += 1
                resp_times.append(delta)

        sample_sufficient = required >= MIN_SAMPLE
        response_rate = (timely / required) if (required and sample_sufficient) else None
        avg_response = (
            (sum(resp_times) / len(resp_times)) if resp_times else None
        )
        return {
            "training_count": training_count,
            "total_duration_sec": round(total_duration, 1),
            "required_response_bullets": required,
            "responded_bullets": responded,
            "timely_responded_bullets": timely,
            "response_rate": response_rate,
            "avg_response_sec": (round(avg_response, 2) if avg_response is not None else None),
            "sample_sufficient": sample_sufficient,
            "sample_count": required,
        }
    finally:
        db.close()


def compute_week_stats():
    start, end = _week_bounds_utc_naive(0)
    prev_start, prev_end = _week_bounds_utc_naive(-1)
    current = _week_stats(start, end)
    previous = _week_stats(prev_start, prev_end)

    change = {}
    if current["sample_sufficient"] and previous["sample_sufficient"]:
        if previous["training_count"] > 0:
            change["training_count_delta"] = (
                current["training_count"] - previous["training_count"]
            )
        if previous["response_rate"] is not None and current["response_rate"] is not None:
            change["response_rate_delta"] = round(
                current["response_rate"] - previous["response_rate"], 4
            )

    return {
        "timezone": str(TZ),
        "week": current,
        "previous_week": previous,
        "change": change,
    }


def recent_trainings(limit: int = 10):
    """最近完成的训练（真实记录，供首页"最近练习"与成长记录）。"""
    db = SessionLocal()
    try:
        rows = (
            db.query(Training)
            .filter(Training.status == "feedback_ready")
            .order_by(Training.finished_at.desc())
            .limit(limit)
            .all()
        )
        return rows
    finally:
        db.close()


def list_recordings():
    """真实媒体记录列表（含媒体是否存在/类型/时长/大小）。"""
    db = SessionLocal()
    try:
        rows = (
            db.query(Recording, Training)
            .join(Training, Recording.training_id == Training.id)
            .order_by(Recording.created_at.desc())
            .all()
        )
        result = []
        for rec, tr in rows:
            result.append(
                {
                    "recording_id": rec.id,
                    "training_id": rec.training_id,
                    "goal": tr.goal,
                    "live_type": tr.live_type,
                    "practice_mode": tr.practice_mode or "full",
                    "media_kind": rec.media_kind or "video",
                    "mime_type": rec.mime_type,
                    "duration_sec": rec.duration_sec,
                    "size_bytes": rec.size_bytes,
                    "exists": _file_exists(rec.file_path),
                    "created_at": (
                        rec.created_at.isoformat() if rec.created_at else None
                    ),
                }
            )
        return result
    finally:
        db.close()


def _file_exists(path):
    if not path:
        return False
    from pathlib import Path

    return Path(path).exists()

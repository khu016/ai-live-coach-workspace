"""真实统计（首页/成长数据）测试（PRD 4.4 / F22）。"""

from app.db import SessionLocal
from app.models import BulletEvent, Recording, TranscriptSegment, Training, now
from app.services.stats import compute_week_stats


def _add_training(db, **kw):
    t = Training(
        live_type=kw.get("live_type", "带货"),
        goal=kw.get("goal", "练习互动"),
        status="feedback_ready",
        finished_at=kw.get("finished_at", now()),
        practice_mode=kw.get("practice_mode", "full"),
        media_kind=kw.get("media_kind", "video"),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_empty_stats_returns_zero(client):
    """数据库无训练时，首页显示 0 且样本不足。"""
    stats = compute_week_stats()
    assert stats["week"]["training_count"] == 0
    assert stats["week"]["sample_sufficient"] is False
    assert stats["week"]["sample_count"] == 0
    assert stats["week"]["response_rate"] is None


def test_stats_after_training_changes(client):
    """完成训练后，本周训练次数与时长随真实记录变化。"""
    db = SessionLocal()
    t = _add_training(db)
    db.add(Recording(training_id=t.id, file_path="/tmp/x.webm", duration_sec=120.0, size_bytes=1000))
    db.commit()
    db.close()

    stats = compute_week_stats()
    assert stats["week"]["training_count"] >= 1
    assert stats["week"]["total_duration_sec"] >= 120.0


def test_insufficient_sample_shows_insufficient(client):
    """需回应弹幕少于 3 条时，显示样本不足且不输出百分比。"""
    db = SessionLocal()
    t = _add_training(db)
    # 2 条需回应弹幕（少于 3 条）
    for i in range(2):
        db.add(
            BulletEvent(
                training_id=t.id,
                kind="dynamic",
                text=f"问题{i}",
                requires_response=True,
                scorable=True,
                display_at=float(i * 10),
                bullet_category="related",
            )
        )
    db.commit()
    db.close()

    stats = compute_week_stats()
    week = stats["week"]
    assert week["sample_count"] == 2
    assert week["sample_sufficient"] is False
    assert week["response_rate"] is None


def test_stats_response_metrics(client):
    """需回应弹幕 ≥3 条时，计算回应及时率与平均回应时间。"""
    db = SessionLocal()
    t = _add_training(db)
    # 3 条需回应弹幕，前 2 条有关联回应片段
    for i in range(3):
        db.add(
            BulletEvent(
                training_id=t.id,
                kind="dynamic",
                text=f"问题{i}",
                requires_response=True,
                scorable=True,
                display_at=float(i * 10),
                bullet_category="related",
                response_segment_ids=[1000 + i] if i < 2 else [],
            )
        )
    # 关联的回应片段（start_sec 在弹幕 display_at 之后 20 秒窗口内）
    db.add(TranscriptSegment(training_id=t.id, id=1000, source="realtime", start_sec=12.0, end_sec=15.0, text="回答1"))
    db.add(TranscriptSegment(training_id=t.id, id=1001, source="realtime", start_sec=22.0, end_sec=25.0, text="回答2"))
    db.commit()
    db.close()

    stats = compute_week_stats()
    week = stats["week"]
    assert week["sample_count"] == 3
    assert week["sample_sufficient"] is True
    assert week["responded_bullets"] == 2
    assert week["timely_responded_bullets"] == 2
    assert week["response_rate"] == 2 / 3
    assert week["avg_response_sec"] is not None
    # 第一条弹幕 display_at=0，回应 12s；第二条 display_at=10，回应 22s → 平均 12s
    assert abs(week["avg_response_sec"] - 12.0) < 0.01

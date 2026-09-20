import time

from app.db import SessionLocal
from app.models import BulletEvent, Feedback, TranscriptSegment, Training
from app.schemas import FeedbackOut, Issue
from app.services import feedback as fb_mod
from app.services.pipeline import run_pipeline


def _wait_status(tid, targets, timeout=4.0):
    deadline = time.time() + timeout
    db = SessionLocal()
    try:
        while True:
            t = db.get(Training, tid)
            if t.status in targets or time.time() > deadline:
                return t.status
            db.expire_all()
            time.sleep(0.05)
    finally:
        db.close()


def _create_training_with_segment(client, text="大家好，欢迎来到直播间。"):
    r = client.post(
        "/api/v1/trainings",
        json={"live_type": "带货", "goal": "练习弹幕应答"},
    )
    tid = r.json()["training"]["id"]
    db = SessionLocal()
    db.add(
        TranscriptSegment(
            training_id=tid,
            source="realtime",
            start_sec=0.0,
            end_sec=2.0,
            text=text,
            seq=0,
        )
    )
    db.commit()
    db.close()
    return tid


def test_pipeline_completes(client, monkeypatch):
    tid = _create_training_with_segment(client)
    captured = {}

    def fake_feedback(t, segments, bullets=None, rules=None):
        captured["segments"] = segments
        captured["bullets"] = bullets
        captured["rules"] = rules
        return FeedbackOut(
            issues=[
                Issue(
                    dimension="直播应对",
                    start_sec=0,
                    end_sec=5,
                    evidence="价格非常实惠",
                    scenario_id="EC-REG-010",
                    rule_ids=["R-REL-001"],
                )
            ],
            top_issue_ids=[0],
        )

    monkeypatch.setattr(fb_mod, "generate_feedback", fake_feedback)
    run_pipeline(tid)
    assert _wait_status(tid, {"feedback_ready", "failed"}) == "feedback_ready"
    db = SessionLocal()
    fb = db.query(Feedback).filter_by(training_id=tid).first()
    assert fb is not None
    assert fb.top_issue_ids == [0]
    assert fb.issues[0]["scenario_id"] == "EC-REG-010"
    assert fb.issues[0]["rule_ids"] == ["R-REL-001"]
    db.close()


def test_pipeline_passes_segments_bullets_and_rules(client, monkeypatch):
    """反馈流程接收确定转写片段、弹幕事件（含触发依据）与规则卡。"""
    tid = _create_training_with_segment(client)
    db = SessionLocal()
    db.add(
        BulletEvent(
            training_id=tid,
            kind="dynamic",
            text="现在下单实际是多少钱？",
            at_sec=8.0,
            source="dynamic",
            scenario_id="EC-REG-010",
            trigger_type="追问",
            trigger_reason="主播未提价格",
            trigger_segment_id=1,
            status="shown",
            meta={
                "viewer_intent": "当前价格",
                "must_cover": ["给出具体价格"],
                "failure_signals": ["只报最低价不提条件"],
                "source_refs": ["SRC-BC4RII-001"],
            },
        )
    )
    db.commit()
    db.close()

    captured = {}

    def fake_feedback(t, segments, bullets=None, rules=None):
        captured["segments"] = segments
        captured["bullets"] = [
            (b.scenario_id, b.trigger_type, b.trigger_reason, dict(b.meta or {}))
            for b in bullets
        ]
        captured["rules"] = [(r["rule_id"], r["category"]) for r in rules]
        return FeedbackOut(issues=[], top_issue_ids=[])

    monkeypatch.setattr(fb_mod, "generate_feedback", fake_feedback)
    run_pipeline(tid)
    assert _wait_status(tid, {"feedback_ready", "failed"}) == "feedback_ready"
    assert captured["segments"], "应传入确定转写片段"
    assert captured["segments"][0]["text"] == "大家好，欢迎来到直播间。"
    assert captured["bullets"], "应传入弹幕事件"
    assert captured["bullets"][0][0] == "EC-REG-010"
    assert captured["bullets"][0][1] == "追问"
    assert captured["bullets"][0][2] == "主播未提价格"
    assert captured["bullets"][0][3]["must_cover"]
    assert captured["rules"], "应传入规则卡"
    assert any(rid == "R-REL-001" for rid, _ in captured["rules"])


def test_pipeline_failure_marks_failed(client, monkeypatch):
    tid = _create_training_with_segment(client)

    def boom(*a, **k):
        raise RuntimeError("feedback down")

    monkeypatch.setattr(fb_mod, "generate_feedback", boom)
    run_pipeline(tid)
    assert _wait_status(tid, {"failed"}) == "failed"

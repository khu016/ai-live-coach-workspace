import time

from app.api import trainings as t_mod
from app.db import SessionLocal
from app.models import BulletEvent, Feedback, Recording, Training
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


def test_pipeline_completes(client, monkeypatch):
    tid = _create_training_with_recording(client)
    captured = {}

    def fake_feedback(t, tr, bullets=None, rules=None):
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


def test_pipeline_passes_bullets_and_rules(client, monkeypatch):
    """反馈流程确实接收弹幕事件（含 scenario_id）与规则卡。"""
    tid = _create_training_with_recording(client)
    db = SessionLocal()
    db.add(
        BulletEvent(
            training_id=tid,
            kind="fixed_question",
            text="现在下单实际是多少钱？",
            at_sec=8.0,
            source="client",
            scenario_id="EC-REG-010",
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

    def fake_feedback(t, tr, bullets=None, rules=None):
        # 会话尚未关闭，这里先把需要的字段取成普通值，避免返回后实例过期
        captured["bullets"] = [
            (b.scenario_id, dict(b.meta or {})) for b in bullets
        ]
        captured["rules"] = [(r["rule_id"], r["category"]) for r in rules]
        return FeedbackOut(issues=[], top_issue_ids=[])

    monkeypatch.setattr(fb_mod, "generate_feedback", fake_feedback)
    run_pipeline(tid)
    assert _wait_status(tid, {"feedback_ready", "failed"}) == "feedback_ready"
    assert captured["bullets"], "应传入弹幕事件"
    assert captured["bullets"][0][0] == "EC-REG-010"
    assert captured["bullets"][0][1]["must_cover"]
    assert captured["rules"], "应传入规则卡"
    assert any(rid == "R-REL-001" for rid, _ in captured["rules"])


def test_pipeline_failure_marks_failed(client, monkeypatch):
    tid = _create_training_with_recording(client)

    def boom(*a, **k):
        raise RuntimeError("asr down")

    monkeypatch.setattr("app.services.asr.get_asr", lambda: type("X", (), {"transcribe": boom})())
    run_pipeline(tid)
    assert _wait_status(tid, {"failed"}) == "failed"


def _create_training_with_recording(client):
    r = client.post(
        "/api/v1/trainings",
        json={"live_type": "带货", "goal": "练习弹幕应答"},
    )
    tid = r.json()["training"]["id"]
    db = SessionLocal()
    db.add(
        Recording(training_id=tid, file_path="/tmp/nonexistent.webm", size_bytes=10)
    )
    db.commit()
    db.close()
    return tid

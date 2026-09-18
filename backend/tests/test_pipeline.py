import time

from app.api import trainings as t_mod
from app.db import SessionLocal
from app.models import Feedback, Recording, Training
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
    monkeypatch.setattr(
        fb_mod,
        "generate_feedback",
        lambda t, tr: FeedbackOut(
            issues=[
                Issue(
                    dimension="直播应对",
                    start_sec=0,
                    end_sec=5,
                    evidence="价格非常实惠",
                )
            ],
            top_issue_ids=[0],
        ),
    )
    run_pipeline(tid)
    assert _wait_status(tid, {"feedback_ready", "failed"}) == "feedback_ready"
    db = SessionLocal()
    fb = db.query(Feedback).filter_by(training_id=tid).first()
    assert fb is not None
    assert fb.top_issue_ids == [0]
    db.close()


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

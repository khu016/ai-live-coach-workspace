import json

from app.api import trainings as t_mod
from app.db import SessionLocal
from app.models import BulletEvent, Feedback, Recording, Training

WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 64


def _create(client, **overrides):
    payload = {
        "live_type": "带货",
        "goal": "练习弹幕应答",
        "topic": None,
        "product_info": None,
        "script": None,
    }
    payload.update(overrides)
    return client.post("/api/v1/trainings", json=payload)


def test_create_valid(client):
    r = _create(client)
    assert r.status_code == 200
    data = r.json()
    assert data["training"]["status"] == "created"
    kinds = [b["kind"] for b in data["script"]]
    assert "fixed_question" in kinds
    assert len(data["script"]) > 0


def test_create_without_topic_ok(client):
    r = _create(client)
    assert r.status_code == 200


def test_create_invalid_type(client):
    r = _create(client, live_type="游戏")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "BAD_REQUEST"


def test_create_empty_goal(client):
    r = _create(client, goal="")
    assert r.status_code == 422


def test_get_not_found(client):
    assert client.get("/api/v1/trainings/999").status_code == 404


def test_finish_valid(client, monkeypatch):
    monkeypatch.setattr(t_mod, "run_pipeline", lambda tid: None)
    r = _create(client)
    tid = r.json()["training"]["id"]
    bullets = json.dumps([{"at_sec": 8, "kind": "fixed_question", "text": "卖点？"}])
    resp = client.post(
        f"/api/v1/trainings/{tid}/finish",
        data={"bullets": bullets, "duration_sec": "10"},
        files={"file": ("recording.webm", WEBM, "video/webm")},
    )
    assert resp.status_code == 200
    assert resp.json()["training"]["status"] == "saved"
    db = SessionLocal()
    assert db.query(Recording).filter_by(training_id=tid).count() == 1
    db.close()


def test_finish_stores_scenario_meta(client, monkeypatch):
    monkeypatch.setattr(t_mod, "run_pipeline", lambda tid: None)
    tid = _create(client).json()["training"]["id"]
    bullets = json.dumps(
        [
            {
                "at_sec": 8,
                "kind": "fixed_question",
                "text": "现在下单实际是多少钱？",
                "scenario_id": "EC-REG-010",
            }
        ]
    )
    resp = client.post(
        f"/api/v1/trainings/{tid}/finish",
        data={"bullets": bullets, "duration_sec": "10"},
        files={"file": ("recording.webm", WEBM, "video/webm")},
    )
    assert resp.status_code == 200
    db = SessionLocal()
    ev = db.query(BulletEvent).filter_by(training_id=tid).first()
    assert ev.scenario_id == "EC-REG-010"
    # 服务端以内容库为准回填场景元数据，而不是盲信客户端
    assert ev.meta["viewer_intent"] == "当前价格"
    assert "明确当前可核实价格" in ev.meta["must_cover"]
    db.close()


def test_finish_bad_format(client, monkeypatch):
    monkeypatch.setattr(t_mod, "run_pipeline", lambda tid: None)
    tid = _create(client).json()["training"]["id"]
    resp = client.post(
        f"/api/v1/trainings/{tid}/finish",
        data={"bullets": "[]"},
        files={"file": ("evil.txt", b"not a video", "text/plain")},
    )
    assert resp.status_code == 400


def test_finish_oversize(client, monkeypatch):
    monkeypatch.setattr(t_mod, "run_pipeline", lambda tid: None)
    monkeypatch.setattr(t_mod.settings, "recording_max_mb", 0.000001)
    tid = _create(client).json()["training"]["id"]
    resp = client.post(
        f"/api/v1/trainings/{tid}/finish",
        data={"bullets": "[]"},
        files={"file": ("recording.webm", WEBM, "video/webm")},
    )
    assert resp.status_code == 400


def test_finish_bad_bullets(client, monkeypatch):
    monkeypatch.setattr(t_mod, "run_pipeline", lambda tid: None)
    tid = _create(client).json()["training"]["id"]
    resp = client.post(
        f"/api/v1/trainings/{tid}/finish",
        data={"bullets": "not-json"},
        files={"file": ("recording.webm", WEBM, "video/webm")},
    )
    assert resp.status_code == 400


def test_retrain_not_ready(client):
    tid = _create(client).json()["training"]["id"]
    r = client.post(f"/api/v1/trainings/{tid}/retrain")
    assert r.status_code == 409


def test_retrain_ok(client):
    tid = _create(client).json()["training"]["id"]
    db = SessionLocal()
    t = db.get(Training, tid)
    t.status = "feedback_ready"
    db.add(Feedback(training_id=tid, issues=[], top_issue_ids=[]))
    db.commit()
    db.close()

    r = client.post(f"/api/v1/trainings/{tid}/retrain")
    assert r.status_code == 200
    assert r.json()["training"]["prev_training_id"] == tid


def test_compare_no_previous(client):
    tid = _create(client).json()["training"]["id"]
    r = client.get(f"/api/v1/trainings/{tid}/compare")
    assert r.status_code == 409


def test_compare_ok(client):
    first = _create(client).json()["training"]["id"]
    db = SessionLocal()
    db.get(Training, first).status = "feedback_ready"
    db.add(Feedback(training_id=first, issues=[], top_issue_ids=[]))
    second = Training(
        live_type="带货",
        goal="练习弹幕应答",
        status="feedback_ready",
        prev_training_id=first,
    )
    db.add(second)
    db.commit()
    db.refresh(second)
    second_id = second.id
    db.add(Feedback(training_id=second_id, issues=[], top_issue_ids=[]))
    db.commit()
    db.close()

    r = client.get(f"/api/v1/trainings/{second_id}/compare")
    assert r.status_code == 200
    assert r.json()["previous"]["training"]["id"] == first

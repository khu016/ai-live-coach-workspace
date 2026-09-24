from app.db import SessionLocal
from app.models import Feedback, Training


def test_tutorial_catalog_and_detail(client):
    response = client.get("/api/v1/tutorials")
    assert response.status_code == 200
    body = response.json()
    assert len(body["tutorials"]) == 9
    assert body["progress"] == {
        "completed_ids": [],
        "completed_count": 0,
        "total": 9,
    }

    detail = client.get("/api/v1/tutorials/opening-30s")
    assert detail.status_code == 200
    assert detail.json()["tutorial"]["practiceTopic"] == "开场留人"
    assert detail.json()["completed"] is False


def test_frontend_deep_link_uses_same_backend_entry(client):
    response = client.get("/tutorials/opening-30s")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text


def test_tutorial_progress_is_persisted(client):
    completed = client.put(
        "/api/v1/tutorials/opening-30s/progress",
        json={"completed": True},
    )
    assert completed.status_code == 200
    assert completed.json()["summary"]["completed_ids"] == ["opening-30s"]

    detail = client.get("/api/v1/tutorials/opening-30s")
    assert detail.json()["completed"] is True

    uncompleted = client.put(
        "/api/v1/tutorials/opening-30s/progress",
        json={"completed": False},
    )
    assert uncompleted.status_code == 200
    assert uncompleted.json()["summary"]["completed_count"] == 0


def test_tutorial_not_found(client):
    assert client.get("/api/v1/tutorials/not-a-tutorial").status_code == 404
    assert client.put(
        "/api/v1/tutorials/not-a-tutorial/progress",
        json={"completed": True},
    ).status_code == 404


def test_report_recommendations_follow_feedback_evidence(client):
    db = SessionLocal()
    try:
        training = Training(live_type="带货", goal="练习弹幕应答", status="feedback_ready")
        db.add(training)
        db.commit()
        db.refresh(training)
        db.add(Feedback(
            training_id=training.id,
            issues=[{
                "dimension": "直播应对",
                "problem": "面对价格质疑时给出了绝对承诺",
                "suggestion": "先确认顾虑并说明事实边界",
                "retrain_target": "刁难弹幕应答",
                "evidence": "肯定是最低价",
                "rule_ids": ["R-TRU-001"],
            }],
            top_issue_ids=[0],
        ))
        db.commit()
        training_id = training.id
    finally:
        db.close()

    response = client.get(f"/api/v1/tutorials/recommendations/{training_id}")
    assert response.status_code == 200
    assert response.json()["tutorials"][0]["id"] == "tough-comments"

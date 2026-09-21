"""必考场景轮换、持久化与重练继承的测试。"""

from app.db import SessionLocal
from app.models import Feedback, Training
from app.services.content_library import MUST_COVER_SCENARIOS, select_must_cover


def test_select_must_cover_returns_one_or_two():
    for lt in ("ecommerce", "entertainment", "knowledge"):
        pool = MUST_COVER_SCENARIOS[lt]
        for seed in range(12):
            ids = select_must_cover(lt, seed)
            assert 1 <= len(ids) <= 2
            # 全部来自本直播类型的必考池
            assert all(sid in pool for sid in ids)
            # 同一次无重复
            assert len(ids) == len(set(ids))


def test_select_must_cover_rotates():
    combos = [tuple(select_must_cover("ecommerce", s)) for s in range(8)]
    assert len(set(combos)) > 1


def test_select_must_cover_deterministic():
    assert select_must_cover("ecommerce", 5) == select_must_cover("ecommerce", 5)


def test_select_must_cover_never_crosses_live_type():
    for lt in ("entertainment", "knowledge"):
        pool = set(MUST_COVER_SCENARIOS[lt])
        for seed in range(6):
            for sid in select_must_cover(lt, seed):
                assert sid in pool


def test_create_persists_selected_must_cover(client):
    r = client.post(
        "/api/v1/trainings", json={"live_type": "带货", "goal": "练习弹幕应答"}
    )
    assert r.status_code == 200
    data = r.json()
    sel = data["training"]["selected_must_cover_scenario_ids"]
    assert 1 <= len(sel) <= 2
    assert all(sid in MUST_COVER_SCENARIOS["ecommerce"] for sid in sel)
    # 持久化：数据库里能读到，不是只存内存
    db = SessionLocal()
    t = db.get(Training, data["training"]["id"])
    assert t.selected_must_cover_scenario_ids == sel
    db.close()


def test_consecutive_trainings_rotate(client):
    combos = []
    for _ in range(5):
        r = client.post(
            "/api/v1/trainings", json={"live_type": "带货", "goal": "练习弹幕应答"}
        )
        combos.append(tuple(r.json()["training"]["selected_must_cover_scenario_ids"]))
    assert len(set(combos)) > 1


def test_no_duplicate_scenario_within_training(client):
    r = client.post(
        "/api/v1/trainings", json={"live_type": "知识内容", "goal": "练习答疑"}
    )
    sel = r.json()["training"]["selected_must_cover_scenario_ids"]
    assert len(sel) == len(set(sel))


def test_retrain_inherits_selected_must_cover(client):
    r = client.post(
        "/api/v1/trainings", json={"live_type": "娱乐互动", "goal": "练习开场"}
    )
    assert r.status_code == 200
    tid = r.json()["training"]["id"]
    sel = r.json()["training"]["selected_must_cover_scenario_ids"]

    db = SessionLocal()
    t = db.get(Training, tid)
    t.status = "feedback_ready"
    db.add(Feedback(training_id=tid, issues=[], top_issue_ids=[]))
    db.commit()
    db.close()

    r2 = client.post(f"/api/v1/trainings/{tid}/retrain")
    assert r2.status_code == 200
    assert r2.json()["training"]["selected_must_cover_scenario_ids"] == sel
    assert r2.json()["training"]["prev_training_id"] == tid

import json
from pathlib import Path

import pytest

from app.services import content_library
from app.services.content_library import ContentLibraryError

MANIFEST_PATH = content_library.DEFAULT_DATA_DIR / "manifest.json"


def _manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_load_counts():
    lib = content_library.reload_library()
    m = _manifest()
    # 优先读 manifest，避免每次扩充内容都因旧常量失败
    assert len(lib.scenarios) == m["scene_count"]
    assert len(lib.rules) == m["rule_count"]
    assert len(lib.ambient) == m["ambient_bullet_count"]
    # 最低数量护栏
    assert len(lib.scenarios) >= 84
    assert len(lib.ambient) >= 90


def test_live_type_filter():
    lib = content_library.get_library()
    dist = _manifest()["scene_distribution_by_live_type"]
    for lt in ("ecommerce", "entertainment", "knowledge"):
        res = lib.select_scenarios(lt)
        assert len(res) == dist[lt]
        assert all(s["live_type"] == lt for s in res)


def test_sample_type_and_difficulty_filter():
    lib = content_library.get_library()
    res = lib.select_scenarios("ecommerce", sample_type="adversarial")
    assert res and all(s["sample_type"] == "adversarial" for s in res)
    res2 = lib.select_scenarios("knowledge", difficulty=3)
    assert res2 and all(s["difficulty"] == 3 for s in res2)


def test_tags_filter():
    lib = content_library.get_library()
    res = lib.select_scenarios("ecommerce", tags=["服饰"])
    assert res
    assert all("服饰" in (s.get("tags") or []) for s in res)


def test_select_must_cover_within_pool():
    lib = content_library.get_library()
    pool = content_library.MUST_COVER_SCENARIOS["ecommerce"]
    for seed in range(8):
        ids = content_library.select_must_cover("ecommerce", seed)
        assert 1 <= len(ids) <= 2
        assert all(sid in pool for sid in ids)


def test_select_scenarios_prepends_given_must():
    lib = content_library.get_library()
    res = lib.select_scenarios("ecommerce", must_scenario_ids=["EC-BND-001"])
    assert res[0]["scenario_id"] == "EC-BND-001"


def test_select_scenarios_no_must_by_default():
    lib = content_library.get_library()
    dist = _manifest()["scene_distribution_by_live_type"]
    res = lib.select_scenarios("ecommerce")
    # 未传必考 ID 时不前置必考，按文件顺序返回全部场景
    assert len(res) == dist["ecommerce"]
    assert res[0]["scenario_id"] == "EC-REG-001"


def test_rules_by_live_type_and_rule_id():
    lib = content_library.get_library()
    rules = lib.rules_for_live_type("ecommerce")
    assert rules
    assert all("ecommerce" in r["live_types"] for r in rules)
    assert lib.get_rule("R-REL-001")["rule_id"] == "R-REL-001"


def test_create_ecommerce_only_ecommerce_scenarios(client):
    r = client.post(
        "/api/v1/trainings", json={"live_type": "带货", "goal": "练习弹幕应答"}
    )
    assert r.status_code == 200
    script = r.json()["script"]
    lib = content_library.get_library()
    ids = [b["scenario_id"] for b in script]
    assert ids
    for sid in ids:
        assert lib.scenarios_by_id[sid]["live_type"] == "ecommerce"


def test_no_duplicate_scenario_in_one_training(client):
    r = client.post(
        "/api/v1/trainings", json={"live_type": "带货", "goal": "练习弹幕应答"}
    )
    script = r.json()["script"]
    ids = [b["scenario_id"] for b in script]
    assert len(ids) == len(set(ids))


def test_script_carries_scenario_meta(client):
    r = client.post(
        "/api/v1/trainings", json={"live_type": "知识内容", "goal": "练习知识答疑"}
    )
    assert r.status_code == 200
    b = r.json()["script"][0]
    for field in (
        "scenario_id",
        "viewer_intent",
        "sample_type",
        "difficulty",
        "must_cover",
        "failure_signals",
        "source_refs",
    ):
        assert field in b
    assert b["source_label"] == "依据真实直播问题类型归纳的训练场景"


def test_missing_file_raises(monkeypatch):
    monkeypatch.setattr(
        content_library,
        "SCENARIOS_FILE",
        content_library.DEFAULT_DATA_DIR / "no_such_file.jsonl",
    )
    with pytest.raises(ContentLibraryError) as exc:
        content_library.reload_library()
    assert "不存在" in str(exc.value)


def test_malformed_line_raises(monkeypatch, tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not-json\n", encoding="utf-8")
    monkeypatch.setattr(content_library, "SCENARIOS_FILE", bad)
    with pytest.raises(ContentLibraryError) as exc:
        content_library.reload_library()
    assert "不是合法 JSON" in str(exc.value)

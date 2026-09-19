import pytest

from app.services import content_library
from app.services.content_library import ContentLibraryError


def test_load_counts():
    lib = content_library.reload_library()
    assert len(lib.scenarios) == 60
    assert len(lib.rules) == 20


def test_live_type_filter():
    lib = content_library.get_library()
    for lt, expected in [
        ("ecommerce", 30),
        ("entertainment", 15),
        ("knowledge", 15),
    ]:
        res = lib.select_scenarios(lt)
        assert len(res) == expected
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


def test_must_cover_scenarios_first():
    lib = content_library.get_library()
    res = lib.select_scenarios("ecommerce")
    assert res[0]["scenario_id"] == content_library.MUST_COVER_SCENARIOS["ecommerce"][0]


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

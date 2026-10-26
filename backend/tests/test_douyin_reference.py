from types import SimpleNamespace

from app.schemas import FeedbackOut, Issue
from app.services import content_library, feedback
from app.services.prompts import feedback_user_prompt


RID = "R-DY-EC-EFFECT-001"
SEGMENTS = [{"start": 1, "end": 4, "text": "你用了三天肯定见效。"}]


def training():
    return SimpleNamespace(live_type="带货", goal="商品讲解", topic=None,
                           product_info=None, script=None)


def issue(**kwargs):
    fields = dict(dimension="内容质量", start_sec=1, end_sec=4,
                  evidence=SEGMENTS[0]["text"], rule_ids=[RID],
                  source_refs=["fake-source"], problem="模型错误地断言违规")
    fields.update(kwargs)
    return Issue(**fields)


def apply(items, notes=None):
    lib = content_library.get_library()
    fb = FeedbackOut(issues=items, top_issue_ids=[0], reference_notes=notes or [])
    return feedback._apply_reference_policy(fb, lib, lib.rules_for_live_type("ecommerce"),
                                          SEGMENTS, training())


def test_reference_cards_only_for_commerce_and_full_prompt_boundaries():
    lib = content_library.reload_library()
    cards = [r for r in lib.rules_for_live_type("ecommerce") if r.get("platform")]
    assert len(cards) == 14
    assert all(not lib.rule_allows_issue(r) for r in cards)
    assert not any(r.get("platform") for r in lib.rules_for_live_type("knowledge"))
    prompt = feedback_user_prompt(training(), SEGMENTS, rules=cards)
    assert "证据" in prompt and "否定" in prompt and "current_effectiveness" in prompt


def test_model_cannot_promote_reference_to_confirmed_issue():
    fb = apply([issue()])
    assert fb.issues == [] and fb.top_issue_ids == []
    note = fb.reference_notes[0]
    assert note.assessment_status == "needs_verification"
    assert "违规" not in note.problem
    assert note.rule_versions[RID] == "0.1.1-reference"
    assert "fake-source" not in note.source_refs
    assert note.source_details[0]["url"].startswith("https://school.jinritemai.com/")


def test_unquoted_or_wrong_time_evidence_is_dropped():
    assert not apply([issue(evidence="你用了肯定百分百有效")]).reference_notes
    assert not apply([issue(start_sec=10, end_sec=12)]).reference_notes


def test_disabled_reference_not_accepted(monkeypatch):
    lib = content_library.get_library()
    rule = lib.get_rule(RID)
    monkeypatch.setitem(rule, "enabled_for_reference", False)
    assert apply([issue()]).reference_notes == []


def test_same_claim_is_merged_and_priority_is_remapped():
    other = issue(rule_ids=["R-REL-001"], evidence="正常问题", problem="另一个问题")
    fb = apply([issue(), other, issue(rule_ids=["R-DY-EC-EFFECT-002"])])
    assert len(fb.reference_notes) == 1
    assert len(fb.reference_notes[0].rule_ids) == 2
    assert fb.issues == [other] and fb.top_issue_ids == []


def test_notes_parse_and_legacy_output_remains_compatible():
    fb = feedback.parse_feedback('{"issues": [], "top_issue_ids": []}')
    assert fb.reference_notes == []


def test_legacy_rules_cannot_treat_missing_material_as_false_and_merge_with_platform():
    fb = apply([issue(rule_ids=["R-COM-001"]), issue()])
    assert not fb.issues and len(fb.reference_notes) == 1
    assert set(fb.reference_notes[0].rule_ids) == {"R-COM-001", RID}


def test_inapplicable_reference_status_is_not_changed_to_problem():
    fb = apply([], [issue(assessment_status="not_applicable")])
    assert not fb.issues and fb.reference_notes[0].assessment_status == "not_applicable"


def test_commerce_material_requirement_does_not_apply_to_knowledge():
    lib = content_library.get_library()
    t = training()
    t.live_type = "知识内容"
    original = issue(rule_ids=["R-TRU-001"])
    fb = FeedbackOut(issues=[original], top_issue_ids=[0])
    result = feedback._apply_reference_policy(fb, lib, lib.rules_for_live_type("knowledge"), SEGMENTS, t)
    assert result.issues == [original] and not result.reference_notes


def test_generation_sends_rules_and_returns_reference(monkeypatch):
    import json
    captured = []
    def fake_chat(messages):
        captured.extend(messages)
        return json.dumps({"issues": [issue().model_dump()], "top_issue_ids": [0]})
    monkeypatch.setattr(feedback, "call_chat", fake_chat)
    fb = feedback.generate_feedback(training(), SEGMENTS)
    assert RID in captured[1]["content"]
    assert not fb.issues and len(fb.reference_notes) == 1


def test_notes_persist_and_are_returned_without_becoming_issues(client, monkeypatch):
    import time
    from app.db import SessionLocal
    from app.models import Feedback, Training
    from app.services.pipeline import run_pipeline
    note = issue(assessment_status="needs_verification")
    monkeypatch.setattr(feedback, "generate_feedback", lambda *a, **kw:
                        FeedbackOut(issues=[], top_issue_ids=[], reference_notes=[note]))
    tid = client.post("/api/v1/trainings", json={"live_type": "带货", "goal": "练习"}).json()["training"]["id"]
    run_pipeline(tid)
    for _ in range(100):
        response = client.get(f"/api/v1/trainings/{tid}/feedback").json()
        if response["status"] in {"feedback_ready", "failed"}:
            break
        time.sleep(0.02)
    assert response["status"] == "feedback_ready"
    assert response["feedback"]["issues"] == []
    assert response["feedback"]["reference_notes"][0]["assessment_status"] == "needs_verification"


def test_old_database_migration_preserves_feedback_and_is_idempotent(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from app import db
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE feedbacks (id INTEGER PRIMARY KEY, issues JSON)")
        connection.exec_driver_sql("INSERT INTO feedbacks VALUES (1, '[]')")
    monkeypatch.setattr(db, "engine", engine)
    db.run_migrations()
    db.run_migrations()
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT id, issues, reference_notes FROM feedbacks").one() == (1, '[]', '[]')
    engine.dispose()

"""反馈语义边界回归：问句不当承诺，直播类型不串模板。"""

from types import SimpleNamespace

from app.schemas import FeedbackOut, Issue
from app.services.feedback import _filter_question_as_claim
from app.services.prompts import feedback_user_prompt


def _training(live_type):
    return SimpleNamespace(
        live_type=live_type,
        goal="练习表达",
        topic=None,
        product_info=None,
    )


def test_knowledge_prompt_does_not_inject_missing_product_data():
    prompt = feedback_user_prompt(_training("知识内容"), [], [], [])
    assert "商品资料：未提供" not in prompt


def test_ecommerce_prompt_keeps_product_fact_boundary():
    prompt = feedback_user_prompt(_training("带货"), [], [], [])
    assert "商品资料：未提供" in prompt
    assert "当前资料无法确认" in prompt


def test_pure_preference_question_not_treated_as_unverified_claim():
    fb = FeedbackOut(
        issues=[
            Issue(
                dimension="内容质量",
                start_sec=0,
                end_sec=5,
                evidence="大家最关心价格、成分还是适合什么肤质？",
                problem="商品资料不足，属于未经核实的承诺",
                suggestion="不要编造商品事实",
                retrain_target="商品介绍",
            )
        ],
        top_issue_ids=[0],
    )
    out = _filter_question_as_claim(fb)
    assert out.issues == []


def test_rhetorical_absolute_claim_is_not_filtered():
    fb = FeedbackOut(
        issues=[
            Issue(
                dimension="内容质量",
                start_sec=0,
                end_sec=5,
                evidence="这不就是全网最低价吗？",
                problem="未经核实的价格承诺",
                suggestion="提供依据",
                retrain_target="商品介绍",
            )
        ],
        top_issue_ids=[0],
    )
    out = _filter_question_as_claim(fb)
    assert len(out.issues) == 1

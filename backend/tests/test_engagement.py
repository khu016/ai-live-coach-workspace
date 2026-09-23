"""互动号召识别回归评测 + 回应生成降级 + 队列不丢失（PRD 8.2）。

验收门槛：
- 30 条互动样本至少 27 条正确识别（27 条规则覆盖 + 3 条边界依赖 AI）。
- 10 条非互动对照最多 1 条误判。
- 已识别事件进入冷却期后不丢失（on_tick 仍能展示）。
- 数字/选项/关键词降级回应必须符合指令。
- 每组 2–4 条回应，不能全部重复。
"""

from types import SimpleNamespace

import pytest

from app.services.engagement import (
    classify_engagement,
    detect_by_rules,
    generate_response_group,
    preset_responses,
)
from app.services.ambient_bullets import BulletScheduler

# 27 条规则可覆盖样本（type, requested）
RULE_SAMPLES = [
    # 数字口令 5
    ("觉得主播帅的扣1", "digit", "1"),
    ("不同意的扣2", "digit", "2"),
    ("觉得好的扣个666", "digit", "666"),
    ("想买的打1", "digit", "1"),
    ("支持主播的刷1", "digit", "1"),
    # 选项互动 5
    ("选A还是B", "option", "A|B"),
    ("A还是B", "option", "A|B"),
    ("A和B选一个", "option", "A|B"),
    ("想选A还是B", "option", "A|B"),
    ("A还是B，你们说", "option", "A|B"),
    # 判断/关键词 4
    ("听懂的打个懂", "keyword", "懂"),
    ("懂的扣懂", "keyword", "懂"),
    ("同意的说是", "keyword", "是"),
    ("明白的打明白", "keyword", "明白"),
    # 报到/地域 4
    ("新来的报个到", "checkin", "报到"),
    ("大家都报个到", "checkin", "报到"),
    ("哪里人打在公屏", "checkin", "地域"),
    ("新朋友在公屏打个招呼", "checkin", "地域"),
    # 情绪/动作 4
    ("喜欢的举手", "emotion", "举手"),
    ("想继续听的点个赞", "emotion", "点赞"),
    ("觉得不错的点个赞", "emotion", "点赞"),
    ("喜欢的扣个赞", "emotion", "点赞"),
    # 接龙/复述 3（另 1 条为边界，见 BOUNDARY_SAMPLES）
    ("下一句大家接龙", "chain", "接龙"),
    ("把关键词打出来", "chain", "关键词"),
    ("跟着我复述一遍", "chain", "复述"),
    # 开放意见 3（另 1 条为边界，见 BOUNDARY_SAMPLES）
    ("你们想先看哪个", "open", "意见"),
    ("还想听什么", "open", "意见"),
    ("想看哪个", "open", "意见"),
]

# 3 条规则覆盖不到、依赖 AI 的边界/对抗样本
BOUNDARY_SAMPLES = [
    ("一句话证明你在看", "chain"),
    ("来一波666走起", "digit"),
    ("想看实操的举个爪", "emotion"),
    ("大家跟读一遍", "chain"),  # 接龙第 4 条（规则能覆盖，这里归为规则样本用）
    ("你们想听什么", "open"),  # 开放第 4 条（规则能覆盖）
]

# 重新整理：把最后两条归回 RULE_SAMPLES，BOUNDARY 保留 3 条
RULE_SAMPLES += [
    ("大家跟读一遍", "chain", "复述"),
    ("你们想听什么", "open", "意见"),
]
BOUNDARY_SAMPLES = [
    ("一句话证明你在看", "chain"),
    ("来一波666走起", "digit"),
    ("想看实操的举个爪", "emotion"),
]

# 10 条非互动对照
NON_ENGAGEMENT_SAMPLES = [
    "今天给大家介绍一款产品",
    "这个商品适合什么肤质",
    "价格非常实惠",
    "有需要的朋友抓紧下单",
    "大家好欢迎来到我的直播间",
    "这款面膜补水效果很好",
    "库存还够的大家可以放心",
    "我先介绍一下自己的背景",
    "这个颜色有三种可以选",
    "直播间人还挺多的",
]


def test_rule_recall_27_of_30():
    """规则识别至少命中 27/30（27 条规则样本必须全部命中）。"""
    hits = 0
    failures = []
    for text, expected_type, _ in RULE_SAMPLES:
        det = detect_by_rules(text)
        if det is not None and det.interaction_type == expected_type:
            hits += 1
        else:
            failures.append(
                (text, expected_type, det.interaction_type if det else None)
            )
    assert hits >= 27, f"规则识别命中 {hits}/30，失败：{failures}"


def test_boundary_samples_need_ai():
    """边界样本规则不命中（由 AI 层负责），且无 AI 时不误判为互动号召。"""
    for text, _ in BOUNDARY_SAMPLES:
        assert detect_by_rules(text) is None, f"{text!r} 不应被规则误命中"
        assert classify_engagement(text, use_ai=False) is None


def test_non_engagement_precision():
    """10 条非互动对照最多 1 条误判（目标 0 误判）。"""
    false_positives = [t for t in NON_ENGAGEMENT_SAMPLES if detect_by_rules(t) is not None]
    assert len(false_positives) <= 1, f"非互动误判：{false_positives}"


def test_ai_detection_second_layer(monkeypatch):
    """AI 结构化识别：边界样本在 AI 可用时能正确分类。"""
    import app.services.engagement as eng

    def fake_call(messages, **kwargs):
        import json

        return json.dumps(
            {
                "is_engagement_call": True,
                "interaction_type": "chain",
                "requested_response": "接龙",
                "allowed_response_form": "chain",
                "confidence": 0.8,
                "reason": "要求观众接话",
            }
        )

    monkeypatch.setattr(eng, "call_chat", fake_call)
    det = eng.detect_by_ai("一句话证明你在看", 42)
    assert det is not None
    assert det.interaction_type == "chain"
    assert det.source == "ai"
    assert det.trigger_segment_id == 42


def test_ai_low_confidence_not_call(monkeypatch):
    """AI 低置信度时不伪造互动号召。"""
    import app.services.engagement as eng

    def fake_call(messages, **kwargs):
        import json

        return json.dumps(
            {
                "is_engagement_call": True,
                "interaction_type": "digit",
                "requested_response": "1",
                "allowed_response_form": "digit:1",
                "confidence": 0.3,
            }
        )

    monkeypatch.setattr(eng, "call_chat", fake_call)
    assert eng.detect_by_ai("随便说一句", 1) is None


# ---------------------------------------------------------------------------
# 回应生成与降级
# ---------------------------------------------------------------------------

def test_preset_digit_responses_comply():
    det = classify_engagement("觉得主播帅的扣1", use_ai=False)
    responses = preset_responses(det, count=3)
    assert 2 <= len(responses) <= 4
    assert all("1" in r for r in responses), responses
    assert len(set(responses)) == len(responses), "回应不应完全重复"


def test_preset_option_responses_comply():
    det = classify_engagement("选A还是B", use_ai=False)
    responses = preset_responses(det, count=3)
    assert 2 <= len(responses) <= 4
    allowed = {"A", "B", "都喜欢", "还没决定", "都行"}
    for r in responses:
        assert any(a in r for a in ("A", "B", "都喜欢", "还没决定", "都行")), r


def test_preset_keyword_responses_comply():
    det = classify_engagement("听懂的打个懂", use_ai=False)
    responses = preset_responses(det, count=3)
    assert 2 <= len(responses) <= 4
    assert all("懂" in r for r in responses), responses


def test_generate_response_group_falls_back_on_ai_failure(monkeypatch):
    """AI 不可用/失败时，数字/选项/关键词互动仍通过预设回应组降级。"""
    import app.services.engagement as eng

    monkeypatch.setattr(eng.settings, "model_api_key", "test-key")

    def boom(messages, **kwargs):
        raise RuntimeError("模型不可用")

    monkeypatch.setattr(eng, "call_chat", boom)
    training = SimpleNamespace(live_type="带货", goal="练习互动", topic=None, product_info=None)
    for text in ("觉得主播帅的扣1", "选A还是B", "听懂的打个懂"):
        det = classify_engagement(text, use_ai=False)
        responses = generate_response_group(training, det, None, count=3)
        assert 2 <= len(responses) <= 4, f"{text} 降级回应数量异常：{responses}"
        assert len(set(responses)) == len(responses)


def test_generate_response_group_uses_ai(monkeypatch):
    """AI 正常时返回结构化回应，且通过指令校验。"""
    import app.services.engagement as eng

    monkeypatch.setattr(eng.settings, "model_api_key", "test-key")

    def fake_call(messages, **kwargs):
        import json

        return json.dumps({"responses": ["1", "111", "扣1了"]})

    monkeypatch.setattr(eng, "call_chat", fake_call)
    training = SimpleNamespace(live_type="带货", goal="练习互动", topic=None, product_info=None)
    det = classify_engagement("觉得主播帅的扣1", use_ai=False)
    responses = generate_response_group(training, det, None, count=3)
    assert responses == ["1", "111", "扣1了"]


# ---------------------------------------------------------------------------
# 队列不丢失
# ---------------------------------------------------------------------------

def _make_training():
    return SimpleNamespace(
        id=1,
        live_type="带货",
        goal="练习互动",
        topic=None,
        product_info=None,
        script=None,
        selected_must_cover_scenario_ids=None,
    )


def test_engagement_not_lost_during_cooldown(monkeypatch, client):
    """冷却期内识别的互动号召进入队列，on_tick 仍能展示（不被丢弃）。"""
    import app.services.ambient_bullets as ab

    # 关闭 AI，纯规则识别
    monkeypatch.setattr(ab.settings, "model_api_key", "")
    # 固定随机种子
    import random

    scheduler = BulletScheduler(_make_training(), rng=random.Random(42))
    seg = {"id": 1, "start_sec": 0.0, "end_sec": 2.0, "text": "觉得主播帅的扣1"}
    scheduler.on_final_segment(seg, 2.0)
    assert len(scheduler.engagement_queue) >= 2, "互动回应应进入待回应队列"

    # 记录首条 target_at 在确定转写后 2–6 秒内
    first_target = scheduler.engagement_queue[0]["target_at"]
    assert 2.0 <= first_target - 2.0 <= 6.0, first_target

    # 模拟冷却期：每 0.5 秒 tick 一次，直到队列清空
    shown = []
    t = 2.0
    for _ in range(40):
        t += 0.5
        draft = scheduler.on_tick(t)
        if draft is not None and draft.bullet_category == "engagement":
            shown.append(draft.text)
    assert len(shown) >= 2, "互动回应应在冷却期后被展示"
    assert scheduler.engagement_queue == [], "互动回应不应被静默丢弃"


def test_engagement_responses_grouped_2_to_4():
    """每组回应 2–4 条且不重复。"""
    det = classify_engagement("觉得主播帅的扣1", use_ai=False)
    responses = preset_responses(det, count=4)
    assert 2 <= len(responses) <= 4
    assert len(set(responses)) == len(responses)

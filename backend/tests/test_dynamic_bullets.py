"""动态弹幕触发引擎的单元测试（mock LLM，不连外网）。"""

from types import SimpleNamespace

from app.services.dynamic_bullets import (
    DynamicBulletEngine,
    decide_bullet,
    is_duplicate,
    link_response,
)

MUST_IDS = ["EC-REG-001", "EC-COM-001", "EC-BND-001", "EC-ADV-002"]


def make_training(live_type="带货", goal="练习弹幕应答"):
    return SimpleNamespace(
        live_type=live_type, goal=goal, topic=None, product_info=None, script=None
    )


def seg(i, text="大家好，欢迎来到直播间。", start=0.0, end=2.0):
    return {"id": i, "text": text, "start_sec": start, "end_sec": end}


# ---- 纯判定函数 ----


def test_decide_cold_start_when_no_segment():
    d = decide_bullet(
        {"last_bullet_at": None, "last_segment_end": None,
         "pending_must_cover": [], "has_new_segment": False},
        now_sec=10, min_interval_sec=5, cold_start_sec=15,
    )
    assert d["source"] == "cold_start"


def test_decide_cold_start_when_silent_long():
    d = decide_bullet(
        {"last_bullet_at": None, "last_segment_end": 0.0,
         "pending_must_cover": [], "has_new_segment": False},
        now_sec=20, min_interval_sec=5, cold_start_sec=15,
    )
    assert d["source"] == "cold_start"


def test_decide_must_cover_priority():
    d = decide_bullet(
        {"last_bullet_at": None, "last_segment_end": 2.0,
         "pending_must_cover": ["EC-REG-001"], "has_new_segment": True},
        now_sec=2.0, min_interval_sec=5, cold_start_sec=15,
    )
    assert d["source"] == "must_cover"
    assert d["scenario_id"] == "EC-REG-001"


def test_decide_llm_on_new_segment():
    d = decide_bullet(
        {"last_bullet_at": None, "last_segment_end": 2.0,
         "pending_must_cover": [], "has_new_segment": True},
        now_sec=2.0, min_interval_sec=5, cold_start_sec=15,
    )
    assert d["source"] == "llm"


def test_decide_none_within_min_interval():
    d = decide_bullet(
        {"last_bullet_at": 2.0, "last_segment_end": 3.0,
         "pending_must_cover": [], "has_new_segment": True},
        now_sec=5.0, min_interval_sec=5, cold_start_sec=15,
    )
    assert d is None  # 5 - 2 = 3 < 5


def test_decide_none_no_new_segment_no_cold():
    d = decide_bullet(
        {"last_bullet_at": None, "last_segment_end": 3.0,
         "pending_must_cover": [], "has_new_segment": False},
        now_sec=4.0, min_interval_sec=5, cold_start_sec=15,
    )
    assert d is None


def test_is_duplicate():
    hist = [{"text": "多少钱？"}]
    assert is_duplicate("多少钱？", hist)
    assert is_duplicate(" 多少钱？ ", hist)
    assert not is_duplicate("怎么发货？", hist)
    assert is_duplicate("", hist)


# ---- 引擎 ----


def test_engine_must_cover_first():
    engine = DynamicBulletEngine(make_training())
    draft = engine.on_final_segment(seg(1), now_sec=2.0)
    assert draft is not None
    assert draft.trigger_type == "预设必考"
    assert draft.scenario_id in MUST_IDS


def test_engine_llm_generates(monkeypatch):
    engine = DynamicBulletEngine(
        make_training(), triggered_scenario_ids=MUST_IDS
    )
    monkeypatch.setattr(
        "app.services.dynamic_bullets.call_chat",
        lambda messages, timeout=30, max_retries=2: '{"trigger_type":"追问","text":"多少钱？","reason":"主播没提价格"}',
    )
    draft = engine.on_final_segment(seg(7, start=0.0, end=3.0), now_sec=3.0)
    assert draft.status == "shown"
    assert draft.trigger_type == "追问"
    assert draft.text == "多少钱？"
    assert draft.trigger_segment_id == 7


def test_engine_llm_failure_falls_back(monkeypatch):
    engine = DynamicBulletEngine(
        make_training(), triggered_scenario_ids=MUST_IDS
    )

    def boom(messages, timeout=30, max_retries=2):
        raise RuntimeError("超时")

    monkeypatch.setattr("app.services.dynamic_bullets.call_chat", boom)
    draft = engine.on_final_segment(seg(1), now_sec=2.0)
    assert draft.status == "fallback"
    assert draft.text


def test_engine_min_interval_suppresses(monkeypatch):
    engine = DynamicBulletEngine(
        make_training(), triggered_scenario_ids=MUST_IDS
    )
    monkeypatch.setattr(
        "app.services.dynamic_bullets.call_chat",
        lambda messages, timeout=30, max_retries=2: '{"trigger_type":"普通互动","text":"来了来了","reason":"问候"}',
    )
    first = engine.on_final_segment(seg(1, end=2.0), now_sec=2.0)
    assert first is not None
    second = engine.on_final_segment(seg(2, start=2.0, end=4.0), now_sec=4.0)
    assert second is None  # 4 - 2 = 2 < 5s 最小间隔


def test_engine_never_two_consecutive_must_cover(monkeypatch):
    """必考弹幕不能连续出现：第一条必考后，下一条应进入 LLM 动态弹幕分支。"""
    engine = DynamicBulletEngine(make_training())
    monkeypatch.setattr(
        "app.services.dynamic_bullets.call_chat",
        lambda messages, timeout=30, max_retries=2: '{"trigger_type":"普通互动","text":"来了来了","reason":"问候"}',
    )
    first = engine.on_final_segment(seg(1, end=2.0), now_sec=2.0)
    assert first is not None
    assert first.trigger_type == "预设必考"
    second = engine.on_final_segment(seg(2, start=7.0, end=8.0), now_sec=8.0)
    assert second is not None
    assert second.trigger_type != "预设必考"
    assert second.trigger_type == "普通互动"


def test_engine_must_cover_resumes_after_llm(monkeypatch):
    """必考弹幕之后进入 LLM 分支，再下一条可继续剩余必考。"""
    engine = DynamicBulletEngine(make_training())
    monkeypatch.setattr(
        "app.services.dynamic_bullets.call_chat",
        lambda messages, timeout=30, max_retries=2: '{"trigger_type":"普通互动","text":"来了来了","reason":"问候"}',
    )
    first = engine.on_final_segment(seg(1, end=2.0), now_sec=2.0)
    assert first.trigger_type == "预设必考"
    second = engine.on_final_segment(seg(2, start=7.0, end=8.0), now_sec=8.0)
    assert second.trigger_type == "普通互动"
    third = engine.on_final_segment(seg(3, start=14.0, end=15.0), now_sec=15.0)
    assert third.trigger_type == "预设必考"


def test_engine_fallback_not_consecutive_must_cover(monkeypatch):
    """LLM 失败时降级：上一条是必考时，不得再用必考兜底（避免连续必考）。"""
    engine = DynamicBulletEngine(make_training())
    first = engine.on_final_segment(seg(1, end=2.0), now_sec=2.0)
    assert first.trigger_type == "预设必考"

    def boom(messages, timeout=30, max_retries=2):
        raise RuntimeError("超时")

    monkeypatch.setattr("app.services.dynamic_bullets.call_chat", boom)
    second = engine.on_final_segment(seg(2, start=7.0, end=8.0), now_sec=8.0)
    assert second.status == "fallback"
    assert second.trigger_type != "预设必考"


def test_engine_cold_start_on_tick():
    engine = DynamicBulletEngine(
        make_training(), triggered_scenario_ids=MUST_IDS
    )
    engine.last_segment_end = 0.0
    draft = engine.on_tick(now_sec=20.0)
    assert draft is not None
    assert draft.trigger_type == "冷场激活"


def test_engine_on_tick_no_trigger_before_cold_start():
    engine = DynamicBulletEngine(
        make_training(), triggered_scenario_ids=MUST_IDS
    )
    # 练习刚开始 5 秒，未冷场、无新片段 → 不触发（必考场景不靠定时器触发）
    assert engine.on_tick(now_sec=5.0) is None


def test_engine_cold_start_once_per_silence():
    """同一段连续沉默期间冷场弹幕最多一次。"""
    engine = DynamicBulletEngine(make_training())
    engine.last_segment_end = 0.0
    d1 = engine.on_tick(now_sec=20.0)
    assert d1 is not None
    assert d1.trigger_type == "冷场激活"
    # 同一段沉默继续，不再重复触发
    assert engine.on_tick(now_sec=24.0) is None
    assert engine.on_tick(now_sec=28.0) is None
    assert engine.on_tick(now_sec=32.0) is None


def test_engine_cold_start_again_after_respeaking():
    """主播恢复说话后再次沉默，可触发新的冷场弹幕。"""
    engine = DynamicBulletEngine(make_training())
    engine.last_segment_end = 0.0
    assert engine.on_tick(now_sec=20.0) is not None  # 第一次冷场
    # 主播重新说话
    engine.on_final_segment(seg(1, start=20.0, end=22.0), now_sec=22.0)
    # 再次沉默超过 15 秒 → 新的冷场
    d = engine.on_tick(now_sec=40.0)
    assert d is not None
    assert d.trigger_type == "冷场激活"


def test_engine_llm_duplicate_rejected(monkeypatch):
    engine = DynamicBulletEngine(
        make_training(), triggered_scenario_ids=MUST_IDS
    )
    monkeypatch.setattr(
        "app.services.dynamic_bullets.call_chat",
        lambda messages, timeout=30, max_retries=2: '{"trigger_type":"普通互动","text":"来了来了","reason":"问候"}',
    )
    first = engine.on_final_segment(seg(1, end=2.0), now_sec=2.0)
    assert first.status == "shown"
    # 第二条在最小间隔之外（8-2=6≥5），但 LLM 返回重复内容 → 降级
    second = engine.on_final_segment(seg(2, start=7.0, end=8.0), now_sec=8.0)
    assert second.status == "fallback"


# ---- 回应链接 ----


def test_link_response():
    bullet = SimpleNamespace(at_sec=10.0)
    segments = [
        {"id": 1, "start_sec": 5.0},
        {"id": 2, "start_sec": 12.0},
        {"id": 3, "start_sec": 50.0},
    ]
    assert link_response(bullet, segments) == [2]


def test_link_response_empty_when_no_at_sec():
    bullet = SimpleNamespace(at_sec=None)
    assert link_response(bullet, [{"id": 1, "start_sec": 5.0}]) == []

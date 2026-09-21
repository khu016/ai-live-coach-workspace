"""环境弹幕加载、统一弹幕调度与评分过滤的测试。"""

import random
from collections import Counter
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.db import SessionLocal
from app.models import BulletEvent
from app.schemas import FeedbackOut, Issue
from app.services import content_library, feedback as fb_mod
from app.services.ambient_bullets import AmbientBulletEngine, BulletScheduler
from app.services.content_library import ContentLibraryError
from app.services.dynamic_bullets import BulletDraft
from app.services.realtime import save_bullet


def make_training(live_type="带货", goal="练习弹幕应答"):
    return SimpleNamespace(
        live_type=live_type,
        goal=goal,
        topic=None,
        product_info=None,
        script=None,
        id=1,
        selected_must_cover_scenario_ids=None,
    )


def seg(i=1, text="大家好，欢迎来到直播间。", start=0.0, end=2.0):
    return {"id": i, "text": text, "start_sec": start, "end_sec": end}


# ---- 内容库加载 ----


def test_ambient_loaded_count():
    lib = content_library.reload_library()
    assert len(lib.ambient) == 90


def test_ambient_category_distribution():
    lib = content_library.get_library()
    c = Counter(b["bullet_category"] for b in lib.ambient)
    assert c == {"unrelated": 30, "passerby": 30, "room_noise": 30}


def test_ambient_live_type_distribution():
    lib = content_library.get_library()
    for lt in ("ecommerce", "entertainment", "knowledge"):
        assert len(lib.ambient_for_live_type(lt)) == 30


def test_ambient_defaults_not_required_not_scorable():
    lib = content_library.get_library()
    for b in lib.ambient:
        assert b["requires_response"] is False
        assert b["scorable"] is False
        assert b["difficulty"] == 0


def test_ambient_missing_file_raises(monkeypatch):
    monkeypatch.setattr(
        content_library,
        "AMBIENT_BULLETS_FILE",
        content_library.DEFAULT_DATA_DIR / "no_such_ambient.jsonl",
    )
    with pytest.raises(ContentLibraryError):
        content_library.reload_library()


# ---- 环境弹幕引擎 ----


def test_ambient_appears_without_transcript():
    sched = BulletScheduler(make_training(), rng=random.Random(1))
    # 首条环境弹幕在 8–12 秒内出现（不依赖转写）
    d = None
    for sec in range(0, 13):
        d = sched.on_tick(float(sec))
        if d is not None:
            break
    assert d is not None
    assert d.bullet_category in ("unrelated", "passerby", "room_noise")
    assert d.scorable is False
    assert d.requires_response is False


def test_first_ambient_within_8_to_12_seconds():
    sched = BulletScheduler(make_training(), rng=random.Random(2))
    # 8 秒前不应出现环境弹幕
    for sec in range(0, 8):
        assert sched.on_tick(float(sec)) is None
    # 12 秒内至少出现一条环境弹幕
    d = None
    for sec in range(8, 13):
        d = sched.on_tick(float(sec))
        if d is not None:
            break
    assert d is not None
    assert d.bullet_category in ("unrelated", "passerby", "room_noise")


def test_no_duplicate_ambient_in_session():
    amb = AmbientBulletEngine(make_training(), rng=random.Random(2))
    for _ in range(30):
        assert amb.pick_ambient() is not None
    assert len(amb.emitted_ambient_ids) == 30
    # 发完后无重复可发
    assert amb.pick_ambient() is None


def test_no_long_consecutive_same_category():
    amb = AmbientBulletEngine(make_training(), rng=random.Random(3))
    cats = []
    for _ in range(20):
        d = amb.pick_ambient(avoid_category=cats[-1] if cats else None)
        assert d is not None
        cats.append(d.bullet_category)
    for i in range(1, len(cats)):
        assert cats[i] != cats[i - 1]


# ---- 统一调度 ----


def test_global_interval_within_config():
    sched = BulletScheduler(make_training(), rng=random.Random(4))
    first_at = None
    for sec in range(0, 13):
        if sched.on_tick(float(sec)) is not None:
            first_at = float(sec)
            break
    assert first_at is not None
    second_at = None
    for sec in range(int(first_at) + 1, 30):
        if sched.on_tick(float(sec)) is not None:
            second_at = float(sec)
            break
    assert second_at is not None
    gap = second_at - first_at
    assert settings.bullet_interval_min_sec <= gap <= settings.bullet_interval_max_sec


def test_no_double_fire_speech_and_ambient():
    sched = BulletScheduler(make_training(), rng=random.Random(5))
    d1 = sched.on_final_segment(seg(), 2.0)
    assert d1 is not None
    # 同一时刻环境定时不应再发一条
    assert sched.on_tick(2.0) is None
    # 最小间隔之内也不应发
    assert sched.on_tick(4.5) is None


def test_adversarial_spacing():
    sched = BulletScheduler(make_training(), rng=random.Random(6))
    sched.next_adversarial_at = 0.0
    d = sched.on_tick(1.0)
    assert d is not None
    assert d.bullet_category == "adversarial"
    assert d.scorable is True
    assert d.requires_response is True
    gap = sched.next_adversarial_at - 1.0
    assert settings.bullet_adversarial_min_sec <= gap <= settings.bullet_adversarial_max_sec


def test_adversarial_first_appears_and_not_starved():
    sched = BulletScheduler(make_training(), rng=random.Random(12))
    seen_at = None
    for sec in range(0, 26):
        d = sched.on_tick(float(sec))
        if d is not None and d.bullet_category == "adversarial":
            seen_at = float(sec)
            break
    assert seen_at is not None, "刁难弹幕应在 25 秒内出现（不被冷场/环境挤占）"
    assert seen_at >= 14, "首条刁难不应过早出现"
    gap = sched.next_adversarial_at - seen_at
    assert settings.bullet_adversarial_min_sec <= gap <= settings.bullet_adversarial_max_sec


def test_burst_max_configured_and_bounded():
    assert settings.bullet_burst_max == 3
    sched = BulletScheduler(make_training(), rng=random.Random(7))
    assert sched.burst_remaining == 0
    d = sched.on_final_segment(seg(), 2.0)
    assert d is not None
    assert sched.burst_remaining == settings.bullet_burst_max - 1
    # 关键弹幕后，最小间隔处能快速跟出弹幕（burst 生效）
    d2 = sched.on_tick(5.0)
    assert d2 is not None
    assert sched.burst_remaining == settings.bullet_burst_max - 2
    # 全程 burst_remaining 不越界
    for sec in range(6, 40):
        sched.on_tick(float(sec))
        assert 0 <= sched.burst_remaining <= settings.bullet_burst_max - 1


# ---- 弹幕属性落库 ----


def test_save_bullet_persists_attributes(client):
    draft = BulletDraft(
        text="你们那边今天下雨了吗？",
        trigger_type="无关",
        trigger_reason="环境弹幕",
        bullet_category="unrelated",
        requires_response=False,
        scorable=False,
        difficulty=0,
        at_sec=3.0,
    )
    msg = save_bullet(1, draft)
    assert msg["bullet_category"] == "unrelated"
    assert msg["scorable"] is False
    assert msg["requires_response"] is False
    db = SessionLocal()
    b = db.query(BulletEvent).filter_by(training_id=1).first()
    assert b.bullet_category == "unrelated"
    assert b.scorable is False
    assert b.requires_response is False
    assert b.display_at == 3.0
    # source 也应有信息量（不再是笼统的 dynamic）
    assert b.source == "unrelated"
    db.close()


def test_all_three_ambient_categories_generated():
    amb = AmbientBulletEngine(make_training(), rng=random.Random(11))
    cats = set()
    for _ in range(30):
        d = amb.pick_ambient()
        if d is None:
            break
        cats.add(d.bullet_category)
    assert cats == {"unrelated", "passerby", "room_noise"}


# ---- 评分过滤 ----


def test_feedback_filters_non_scorable_bullet():
    lib = content_library.get_library()
    fb = FeedbackOut(
        issues=[
            Issue(
                dimension="直播应对",
                start_sec=0,
                end_sec=5,
                evidence="主播没有回应",
                trigger_bullet="你们那边今天下雨了吗？",
                problem="漏答观众提问",
                suggestion="",
                retrain_target="弹幕应答",
            ),
            Issue(
                dimension="直播应对",
                start_sec=0,
                end_sec=5,
                evidence="价格非常实惠",
                trigger_bullet="现在下单实际是多少钱？",
                scenario_id="EC-REG-010",
                rule_ids=["R-REL-001"],
                problem="未回应价格追问",
                suggestion="",
                retrain_target="弹幕应答",
            ),
        ],
        top_issue_ids=[0, 1],
    )
    bullets = [
        SimpleNamespace(
            text="你们那边今天下雨了吗？", scorable=False, requires_response=False
        ),
        SimpleNamespace(
            text="现在下单实际是多少钱？", scorable=True, requires_response=True
        ),
    ]
    out = fb_mod._filter_non_scorable_evidence(fb, bullets, lib)
    assert len(out.issues) == 1
    assert out.issues[0].trigger_bullet == "现在下单实际是多少钱？"
    assert out.top_issue_ids == [0]


def test_feedback_drops_adversarial_without_rule_or_evidence():
    lib = content_library.get_library()
    adv_id = "EC-ADV-004"
    fb = FeedbackOut(
        issues=[
            Issue(
                dimension="直播应对",
                start_sec=0,
                end_sec=5,
                evidence="",  # 无可观察证据
                trigger_bullet="你先保证用了肯定有效，我就下单。",
                scenario_id=adv_id,
                rule_ids=[],
                problem="未回应刁难",
                suggestion="",
                retrain_target="高压互动",
            ),
        ],
        top_issue_ids=[0],
    )
    bullets = [
        SimpleNamespace(
            text="你先保证用了肯定有效，我就下单。",
            scorable=True,
            requires_response=True,
        )
    ]
    out = fb_mod._filter_non_scorable_evidence(fb, bullets, lib)
    assert len(out.issues) == 0

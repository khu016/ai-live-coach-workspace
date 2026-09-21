"""环境弹幕与统一弹幕调度。

- 环境弹幕（无关/路人/直播间噪声）来自内容库 ``ambient_bullets.jsonl``，不依赖
  实时转写，由定时器独立产生；同一场练习不重复显示同一条。
- 刁难弹幕来自场景卡的 ``adversarial`` 样本，首条约 15–20 秒出现，之后每 20–40
  秒一条，不被其他弹幕无限延后。
- ``BulletScheduler`` 统一协调语音驱动弹幕（必考/相关/冷场）与环境/刁难弹幕，
  共享一个展示时钟，避免环境定时与语音触发同时各发一条。

调度节奏：
- 全局展示间隔 3–6 秒（最小 3 秒），所有类别共享。
- 环境弹幕独立节奏：首条 8–12 秒，之后每 3–6 秒一条，不被语音弹幕重置延后。
- 刁难弹幕独立节奏：首条 15–20 秒，之后每 20–40 秒一条，优先于冷场/环境。
- 冷场弹幕每次连续沉默最多一次（由 DynamicBulletEngine 内部去重）。

随机数可注入（固定种子），保证自动化测试可复现。
"""

import random
from typing import List, Optional

from ..core.config import settings
from . import content_library
from .dynamic_bullets import BulletDraft, DynamicBulletEngine

# 环境弹幕分类 → 对外触发类型标签
AMBIENT_TRIGGER_LABEL = {
    "unrelated": "无关",
    "passerby": "路人",
    "room_noise": "噪声",
}


class AmbientBulletEngine:
    """环境弹幕（无关/路人/噪声）与刁难弹幕的独立调度（不依赖转写）。"""

    def __init__(self, training, rng=None):
        self.training = training
        self.lib = content_library.get_library()
        self.rng = rng or random.Random()
        self.live_type_en = content_library.LIVE_TYPE_TO_EN.get(training.live_type)
        self.emitted_ambient_ids: set = set()
        self.emitted_adversarial_ids: set = set()
        self._last_ambient_category: Optional[str] = None

    def _ambient_pool(self) -> List[dict]:
        return [
            b
            for b in self.lib.ambient_for_live_type(self.live_type_en)
            if b["bullet_id"] not in self.emitted_ambient_ids
        ]

    def _adversarial_pool(self) -> List[dict]:
        return [
            s
            for s in self.lib.adversarial_scenarios(self.live_type_en)
            if s["scenario_id"] not in self.emitted_adversarial_ids
        ]

    def pick_ambient(
        self, avoid_category: Optional[str] = None
    ) -> Optional[BulletDraft]:
        """随机选一条未展示过的环境弹幕（可选避开某分类，避免同类连续）。"""
        pool = self._ambient_pool()
        if avoid_category:
            filtered = [b for b in pool if b["bullet_category"] != avoid_category]
            if filtered:
                pool = filtered
        if not pool:
            return None
        b = self.rng.choice(pool)
        self.emitted_ambient_ids.add(b["bullet_id"])
        self._last_ambient_category = b["bullet_category"]
        return BulletDraft(
            text=b["text"],
            trigger_type=AMBIENT_TRIGGER_LABEL.get(b["bullet_category"], "环境"),
            trigger_reason="环境弹幕（无关/路人/噪声，不要求回应）",
            status="shown",
            bullet_category=b["bullet_category"],
            requires_response=bool(b.get("requires_response", False)),
            scorable=bool(b.get("scorable", False)),
            difficulty=int(b.get("difficulty", 0)),
            meta={
                "source_refs": b.get("source_refs") or [],
                "tags": b.get("tags") or [],
            },
        )

    def pick_adversarial(self) -> Optional[BulletDraft]:
        """随机选一条未展示过的刁难场景（带场景 ID 与规则依据，可评分）。"""
        pool = self._adversarial_pool()
        if not pool:
            return None
        s = self.rng.choice(pool)
        self.emitted_adversarial_ids.add(s["scenario_id"])
        return BulletDraft(
            text=s["reference_utterance"],
            trigger_type="刁难",
            trigger_reason=f"刁难场景 {s['scenario_id']}",
            scenario_id=s["scenario_id"],
            status="shown",
            bullet_category="adversarial",
            requires_response=True,
            scorable=True,
            difficulty=int(s.get("difficulty", 0)),
            meta={
                "viewer_intent": s.get("viewer_intent"),
                "must_cover": s.get("must_cover") or [],
                "failure_signals": s.get("failure_signals") or [],
                "source_refs": s.get("source_refs") or [],
                "sample_type": "adversarial",
            },
        )


class BulletScheduler:
    """统一弹幕调度：语音驱动弹幕（必考/相关/冷场）+ 环境/刁难弹幕。"""

    def __init__(self, training, rng=None):
        self.training = training
        self.rng = rng or random.Random()
        self.dynamic = DynamicBulletEngine(
            training,
            selected_must_cover_ids=getattr(
                training, "selected_must_cover_scenario_ids", None
            ),
        )
        self.ambient = AmbientBulletEngine(training, rng=self.rng)
        # 共享展示时钟：语音触发与环境定时都用它，避免重复发射
        self.last_display_at: Optional[float] = None
        # 环境弹幕独立节奏：首条 8–12 秒，之后每 3–6 秒；不被语音弹幕重置延后
        self.next_ambient_at: float = self.rng.uniform(
            settings.bullet_ambient_first_min_sec,
            settings.bullet_ambient_first_max_sec,
        )
        self.last_ambient_at: Optional[float] = None
        # 刁难弹幕独立节奏：首条 15–20 秒，之后每 20–40 秒
        self.next_adversarial_at: float = self.rng.uniform(
            settings.bullet_adversarial_first_min_sec,
            settings.bullet_adversarial_first_max_sec,
        )
        # 关键发言后的短弹幕组合剩余条数
        self.burst_remaining = 0

    # ---- 内部工具 ----

    def _can_display(self, now_sec: float) -> bool:
        return (
            self.last_display_at is None
            or (now_sec - self.last_display_at) >= settings.bullet_interval_min_sec
        )

    def _random_interval(self) -> float:
        return self.rng.uniform(
            settings.bullet_interval_min_sec, settings.bullet_interval_max_sec
        )

    def _ambient_due(self, now_sec: float) -> bool:
        return now_sec >= self.next_ambient_at

    def _adversarial_due(self, now_sec: float) -> bool:
        return now_sec >= self.next_adversarial_at

    def _mark(self, draft: BulletDraft, now_sec: float) -> None:
        self.last_display_at = now_sec
        # 同步语音引擎时钟，保证语音触发与环境定时不重复发射
        self.dynamic.last_bullet_at = now_sec
        cat = draft.bullet_category
        if cat in ("related", "must_cover"):
            # 相关/必考优先：仅允许短弹幕组合，不重置环境弹幕节奏（防挤占）
            self.burst_remaining = settings.bullet_burst_max - 1
        elif cat == "adversarial":
            self.next_adversarial_at = now_sec + self.rng.uniform(
                settings.bullet_adversarial_min_sec,
                settings.bullet_adversarial_max_sec,
            )
        elif cat in ("unrelated", "passerby", "room_noise"):
            self.last_ambient_at = now_sec
            self.next_ambient_at = now_sec + self._random_interval()
        # cold_start / fallback：不改变环境与刁难节奏

    # ---- 对外接口 ----

    def on_final_segment(self, segment: dict, now_sec: float) -> Optional[BulletDraft]:
        """主播稳定转写到达：优先触发必考/相关弹幕（相关优先于环境）。"""
        draft = self.dynamic.on_final_segment(segment, now_sec)
        if draft is None:
            return None
        self._mark(draft, now_sec)
        return draft

    def on_tick(self, now_sec: float) -> Optional[BulletDraft]:
        """定时回调：刁难 > 冷场激活 > 环境弹幕（刁难优先，防饿死）。"""
        if not self._can_display(now_sec):
            return None
        # 刁难弹幕优先，避免被冷场/环境持续挤占
        if self._adversarial_due(now_sec):
            draft = self.ambient.pick_adversarial()
            if draft is not None:
                self._mark(draft, now_sec)
                return draft
        # 冷场激活（同一沉默期最多一次，由 DynamicBulletEngine 内部去重）
        draft = self.dynamic.on_tick(now_sec)
        if draft is not None:
            self._mark(draft, now_sec)
            return draft
        # 环境弹幕：按独立节奏（burst 期间可提前到最小间隔）
        if self.burst_remaining > 0 or self._ambient_due(now_sec):
            draft = self.ambient.pick_ambient(
                avoid_category=self.ambient._last_ambient_category
            )
            if draft is not None:
                self.burst_remaining = max(0, self.burst_remaining - 1)
                self._mark(draft, now_sec)
                return draft
        return None

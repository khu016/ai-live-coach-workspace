"""动态弹幕触发引擎。

稳定转写片段 →（确定性判定是否触发）→ 追问/质疑/普通互动/话题承接/冷场激活/预设必考
→ LLM 生成（带触发依据）→ 超时/非法 → 预设弹幕降级。

确定性规则负责「何时触发 + 用哪类来源」，模型只负责「当前这条弹幕怎么写」，
不把是否触发、频率控制交给模型自主决定（对齐核心规则卡第 5 条）。
"""

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from ..core.config import settings
from . import content_library
from .llm import call_chat
from .prompts import DYNAMIC_BULLET_SYSTEM, dynamic_bullet_user_prompt

TRIGGER_TYPES = ("追问", "质疑", "普通互动", "话题承接", "冷场激活", "预设必考")
RECENT_SEGMENTS_LIMIT = 5

# 冷场激活弹幕：自然口吻轮换，模拟真实观众催主播继续
COLD_START_LINES = (
    "主播人呢？",
    "然后呢？继续呀",
    "卡了吗？",
    "刚说的那个再讲讲",
    "别停啊，正听着呢",
)


@dataclass
class BulletDraft:
    text: str
    trigger_type: str
    trigger_segment_id: Optional[int] = None
    trigger_reason: str = ""
    scenario_id: Optional[str] = None
    status: str = "shown"
    at_sec: Optional[float] = None
    # 弹幕属性（评分与展示过滤用）
    bullet_category: Optional[str] = None  # related/must_cover/adversarial/unrelated/passerby/room_noise/cold_start
    requires_response: bool = False
    scorable: bool = False
    difficulty: int = 0
    meta: Optional[dict] = None


def decide_bullet(
    state: dict,
    now_sec: float,
    min_interval_sec: Optional[float] = None,
    cold_start_sec: Optional[float] = None,
) -> Optional[dict]:
    """确定性判定是否生成弹幕，以及用哪类来源。

    返回 None（不触发）或 ``{"source": "cold_start"|"must_cover"|"llm", "scenario_id": ...}``。

    必考与动态穿插：只有上一条不是必考弹幕时才允许触发下一条必考（一场练习
    最多连续 1 条必考），否则交给 LLM 生成动态弹幕。
    """
    min_interval = (
        min_interval_sec if min_interval_sec is not None else settings.bullet_min_interval_sec
    )
    cold_start = (
        cold_start_sec if cold_start_sec is not None else settings.bullet_cold_start_sec
    )
    last_bullet = state.get("last_bullet_at")
    if last_bullet is not None and (now_sec - last_bullet) < min_interval:
        return None
    last_seg = state.get("last_segment_end")
    if last_seg is None or (now_sec - last_seg) > cold_start:
        return {"source": "cold_start", "scenario_id": None}
    # 无新片段时不触发必考/LLM（定时器只负责冷场）
    if not state.get("has_new_segment"):
        return None
    pending = state.get("pending_must_cover") or []
    last_was_must = bool(state.get("last_was_must_cover"))
    if pending and not last_was_must:
        return {"source": "must_cover", "scenario_id": pending[0]}
    if state.get("has_new_segment"):
        return {"source": "llm", "scenario_id": None}
    return None


def is_duplicate(text: str, history: List[dict]) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    for b in history:
        if (b.get("text") or "").strip() == t:
            return True
    return False


class DynamicBulletEngine:
    """一场练习的动态弹幕触发引擎（进程内状态，随 WebSocket 会话存续）。"""

    def __init__(
        self,
        training,
        selected_must_cover_ids=None,
        history_bullets=None,
        triggered_scenario_ids=None,
    ):
        self.training = training
        self.lib = content_library.get_library()
        self.recent_segments: List[dict] = []
        self.history_bullets: List[dict] = list(history_bullets or [])
        self.triggered_scenario_ids = set(triggered_scenario_ids or [])
        # 本场选定的必考场景（1–2 个）；未显式传入时按练习 ID 确定性轮换选出。
        self.selected_must_cover_ids = (
            list(selected_must_cover_ids) if selected_must_cover_ids is not None else None
        )
        self.last_bullet_at: Optional[float] = None
        # 以练习开始（0 秒）为基准，冷场按距最后发言的时长判定
        self.last_segment_end: float = 0.0
        self._cold_start_count = 0
        self._last_was_must_cover = False
        # 同一段连续沉默期间冷场弹幕最多一次；主播重新说话后重置
        self._cold_start_emitted = False

    @property
    def live_type_en(self):
        return content_library.LIVE_TYPE_TO_EN.get(self.training.live_type)

    def _pending_must_cover(self) -> List[str]:
        if self.selected_must_cover_ids is None:
            live_type_en = self.live_type_en or ""
            seed = getattr(self.training, "id", 0) or 0
            self.selected_must_cover_ids = content_library.select_must_cover(
                live_type_en, seed
            )
        return [
            sid for sid in self.selected_must_cover_ids
            if sid not in self.triggered_scenario_ids
        ]

    def _state(self, now_sec, has_new_segment):
        return {
            "last_bullet_at": self.last_bullet_at,
            "last_segment_end": self.last_segment_end,
            "pending_must_cover": self._pending_must_cover(),
            "has_new_segment": has_new_segment,
            "last_was_must_cover": self._last_was_must_cover,
        }

    def on_final_segment(self, segment: dict, now_sec: float) -> Optional[BulletDraft]:
        """新稳定片段到达时调用。segment 需含 id/start_sec/end_sec/text。"""
        self.recent_segments.append(segment)
        self.recent_segments = self.recent_segments[-RECENT_SEGMENTS_LIMIT:]
        self.last_segment_end = segment.get("end_sec") or now_sec
        # 主播重新说话：进入新的沉默区间前，重置冷场已触发标记
        self._cold_start_emitted = False
        decision = decide_bullet(self._state(now_sec, True), now_sec)
        if decision is None:
            return None
        draft = self._generate(decision["source"], decision["scenario_id"], now_sec)
        self._record(draft, now_sec)
        return draft

    def on_tick(self, now_sec: float) -> Optional[BulletDraft]:
        """定时回调（冷场检测）。无新片段时不走 LLM，只在冷场时触发。

        同一段连续沉默期间冷场弹幕最多出现一次；主播重新说话后再进入新的
        沉默区间，才能再次触发冷场弹幕。
        """
        decision = decide_bullet(self._state(now_sec, False), now_sec)
        if decision is None:
            return None
        if decision["source"] == "cold_start":
            if self._cold_start_emitted:
                return None
            self._cold_start_emitted = True
        draft = self._generate(decision["source"], decision["scenario_id"], now_sec)
        self._record(draft, now_sec)
        return draft

    def _generate(self, source: str, scenario_id: Optional[str], now_sec: float) -> BulletDraft:
        if source == "cold_start":
            return self._preset_cold_start(now_sec)
        if source == "must_cover":
            return self._preset_must_cover(scenario_id, now_sec)
        return self._llm_generate(now_sec)

    def _preset_cold_start(self, now_sec: float) -> BulletDraft:
        text = COLD_START_LINES[self._cold_start_count % len(COLD_START_LINES)]
        self._cold_start_count += 1
        return BulletDraft(
            text=text,
            trigger_type="冷场激活",
            trigger_reason=f"距上次发言超过 {settings.bullet_cold_start_sec} 秒",
            status="shown",
            at_sec=now_sec,
            bullet_category="cold_start",
            requires_response=False,
            scorable=False,
        )

    def _preset_must_cover(self, scenario_id: Optional[str], now_sec: float) -> BulletDraft:
        sc = self.lib.scenarios_by_id.get(scenario_id) if scenario_id else None
        text = sc["reference_utterance"] if sc else "（预设关键问题）"
        meta = None
        if sc is not None:
            meta = {
                "viewer_intent": sc.get("viewer_intent"),
                "must_cover": sc.get("must_cover") or [],
                "failure_signals": sc.get("failure_signals") or [],
                "source_refs": sc.get("source_refs") or [],
                "sample_type": sc.get("sample_type"),
            }
        return BulletDraft(
            text=text,
            trigger_type="预设必考",
            trigger_reason=f"必考场景 {scenario_id}",
            scenario_id=scenario_id,
            status="shown",
            at_sec=now_sec,
            bullet_category="must_cover",
            requires_response=True,
            scorable=True,
            difficulty=int(sc.get("difficulty", 0)) if sc else 0,
            meta=meta,
        )

    def _llm_generate(self, now_sec: float) -> BulletDraft:
        trigger_segment = self.recent_segments[-1] if self.recent_segments else {}
        messages = [
            {"role": "system", "content": DYNAMIC_BULLET_SYSTEM},
            {
                "role": "user",
                "content": dynamic_bullet_user_prompt(
                    self.training, self.recent_segments, self.history_bullets
                ),
            },
        ]
        try:
            text = call_chat(
                messages,
                timeout=settings.bullet_generate_timeout_sec,
                max_retries=0,
            )
            data = _extract_json(text)
            trigger_type = str(data.get("trigger_type") or "").strip()
            if trigger_type not in TRIGGER_TYPES:
                raise ValueError(f"非法 trigger_type: {trigger_type!r}")
            bullet_text = str(data.get("text") or "").strip()
            if not bullet_text or len(bullet_text) > 80:
                raise ValueError("弹幕内容为空或过长")
            if is_duplicate(bullet_text, self.history_bullets):
                raise ValueError("弹幕与历史重复")
            return BulletDraft(
                text=bullet_text,
                trigger_type=trigger_type,
                trigger_segment_id=trigger_segment.get("id"),
                trigger_reason=str(data.get("reason") or ""),
                status="shown",
                at_sec=now_sec,
                bullet_category="related",
                requires_response=True,
                scorable=True,
            )
        except Exception:  # noqa: BLE001
            return self._fallback(now_sec, trigger_segment.get("id"))

    def _fallback(self, now_sec: float, trigger_segment_id=None) -> BulletDraft:
        pending = self._pending_must_cover()
        # 上一条不是必考且还有未触发的必考场景时，用必考场景兜底；否则用通用
        # 追问兜底，避免连续出现两条必考弹幕（一场最多连续 1 条必考）。
        if pending and not self._last_was_must_cover:
            return self._preset_must_cover(pending[0], now_sec)
        return BulletDraft(
            text="嗯，这个话题挺有意思，能再展开讲讲吗？",
            trigger_type="追问",
            trigger_segment_id=trigger_segment_id,
            trigger_reason="动态弹幕生成失败，使用预设弹幕降级",
            status="fallback",
            at_sec=now_sec,
            bullet_category="fallback",
            requires_response=False,
            scorable=False,
        )

    def _record(self, draft: BulletDraft, now_sec: float) -> None:
        self.last_bullet_at = now_sec
        self.history_bullets.append({"text": draft.text, "trigger_type": draft.trigger_type})
        if draft.scenario_id:
            self.triggered_scenario_ids.add(draft.scenario_id)
        self._last_was_must_cover = draft.trigger_type == "预设必考"


def _extract_json(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            raise ValueError("无法解析模型输出为 JSON")
        data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("模型输出不是 JSON 对象")
    return data


def link_response(bullet, segments: List[dict], window_sec: float = 30.0) -> List[int]:
    """把弹幕与主播回应片段关联（确定性规则）。

    弹幕展示后、window_sec 内出现的稳定片段视为回应，返回片段 id 列表。
    """
    if bullet.at_sec is None:
        return []
    ids = []
    for seg in segments:
        start = seg.get("start_sec")
        if start is None or start < bullet.at_sec:
            continue
        if start - bullet.at_sec <= window_sec:
            ids.append(seg.get("id"))
    return ids

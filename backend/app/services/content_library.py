"""内容库读取服务。

在 ``backend/app/data/content_library/`` 下加载场景卡、规则卡与环境弹幕，
用普通内存索引做筛选，不引入向量数据库 / RAG。

- 场景卡：``scenario_cards.jsonl``（84 张）
- 规则卡：``teaching_rules.jsonl``（20 张）
- 环境弹幕：``ambient_bullets.jsonl``（90 张：无关/路人/直播间噪声各 30）
- 来源登记：``source_registry.json``
- 版本信息：``manifest.json``

训练场景（含必考、刁难）与环境弹幕分别管理，不互相混用。

数据文件随后端发布，运行时只依赖后端包内路径（可用 ``CONTENT_LIBRARY_DIR``
环境变量覆盖，便于测试与部署）；文件缺失或格式错误时抛出 ``ContentLibraryError``，
绝不静默回退到空数据。
"""

import json
import os
import random
from pathlib import Path
from threading import Lock
from typing import Iterable, List, Optional

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "content_library"

SCENARIOS_FILE = Path(os.getenv("CONTENT_LIBRARY_DIR", str(DEFAULT_DATA_DIR))) / "scenario_cards.jsonl"
RULES_FILE = Path(os.getenv("CONTENT_LIBRARY_DIR", str(DEFAULT_DATA_DIR))) / "teaching_rules.jsonl"
AMBIENT_BULLETS_FILE = Path(os.getenv("CONTENT_LIBRARY_DIR", str(DEFAULT_DATA_DIR))) / "ambient_bullets.jsonl"

LIVE_TYPES = ("ecommerce", "entertainment", "knowledge")

# 中文直播类型（对外 API）→ 内容库英文标识
LIVE_TYPE_TO_EN = {
    "带货": "ecommerce",
    "娱乐互动": "entertainment",
    "知识内容": "knowledge",
}
EN_TO_LIVE_TYPE = {v: k for k, v in LIVE_TYPE_TO_EN.items()}

SCENARIO_REQUIRED_FIELDS = (
    "scenario_id",
    "live_type",
    "sample_type",
    "difficulty",
    "viewer_intent",
    "reference_utterance",
    "must_cover",
    "failure_signals",
    "source_refs",
)
RULE_REQUIRED_FIELDS = (
    "rule_id",
    "category",
    "live_types",
    "observable_behavior",
    "pass_condition",
    "source_refs",
)

# 环境弹幕分类（均为不要求回应、不参与评分的直播间气氛内容）
AMBIENT_CATEGORIES = ("unrelated", "passerby", "room_noise")
AMBIENT_REQUIRED_FIELDS = (
    "bullet_id",
    "bullet_category",
    "live_types",
    "text",
    "requires_response",
    "scorable",
    "difficulty",
    "source_refs",
)

# 预设必考场景池：每个直播类型的高价值 / 高风险场景（按 live_type 硬编码）。
# 这是「轮换候选池」，不是每场都要全部出现的清单；每场只从中确定性选出 1–2 个
# （见 select_must_cover），多场练习累计覆盖整个池。
MUST_COVER_SCENARIOS = {
    "ecommerce": ["EC-REG-001", "EC-COM-001", "EC-BND-001", "EC-ADV-002"],
    "entertainment": ["EN-REG-001", "EN-COM-001", "EN-BND-001"],
    "knowledge": ["KN-REG-001", "KN-BND-002", "KN-ADV-001"],
}

# 未审核内容统一用这个来源描述，绝不表述成"真实直播原句"。
SCENARIO_SOURCE_LABEL = "依据真实直播问题类型归纳的训练场景"


class ContentLibraryError(RuntimeError):
    """内容库文件缺失、格式错误或请求非法时的明确错误。"""


def _load_jsonl(path: Path, label: str, required: Iterable[str]) -> List[dict]:
    if not path.exists():
        raise ContentLibraryError(f"内容库文件缺失：{label} 文件 {path} 不存在")
    records = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ContentLibraryError(
                    f"内容库格式错误：{label} 文件 {path} 第 {lineno} 行不是合法 JSON：{e}"
                )
            if not isinstance(obj, dict):
                raise ContentLibraryError(
                    f"内容库格式错误：{label} 文件 {path} 第 {lineno} 行不是 JSON 对象"
                )
            missing = [f for f in required if f not in obj]
            if missing:
                raise ContentLibraryError(
                    f"内容库格式错误：{label} 文件 {path} 第 {lineno} 行缺少字段 {missing}"
                )
            records.append(obj)
    if not records:
        raise ContentLibraryError(f"内容库为空：{label} 文件 {path} 没有任何记录")
    return records


class ContentLibrary:
    def __init__(self) -> None:
        self.scenarios: List[dict] = []
        self.scenarios_by_id: dict = {}
        self.rules: List[dict] = []
        self.rules_by_id: dict = {}
        self.rules_by_live_type: dict = {}
        self.ambient: List[dict] = []
        self.ambient_by_id: dict = {}
        self.ambient_by_live_type: dict = {}

    def load(self) -> "ContentLibrary":
        scenarios = _load_jsonl(SCENARIOS_FILE, "场景卡", SCENARIO_REQUIRED_FIELDS)
        rules = _load_jsonl(RULES_FILE, "规则卡", RULE_REQUIRED_FIELDS)
        ambient = _load_jsonl(
            AMBIENT_BULLETS_FILE, "环境弹幕", AMBIENT_REQUIRED_FIELDS
        )
        for s in scenarios:
            if s["live_type"] not in LIVE_TYPES:
                raise ContentLibraryError(
                    f"内容库格式错误：场景 {s['scenario_id']} 的 live_type={s['live_type']!r} 非法"
                )
            sid = s["scenario_id"]
            if sid in self.scenarios_by_id:
                raise ContentLibraryError(f"内容库格式错误：场景 ID 重复 {sid!r}")
            self.scenarios_by_id[sid] = s
        for r in rules:
            rid = r["rule_id"]
            if rid in self.rules_by_id:
                raise ContentLibraryError(f"内容库格式错误：规则 ID 重复 {rid!r}")
            if not isinstance(r["live_types"], list):
                raise ContentLibraryError(
                    f"内容库格式错误：规则 {rid} 的 live_types 必须是数组"
                )
            self.rules_by_id[rid] = r
            for lt in r["live_types"]:
                self.rules_by_live_type.setdefault(lt, []).append(rid)
        for b in ambient:
            self._validate_ambient(b)
            bid = b["bullet_id"]
            if bid in self.ambient_by_id:
                raise ContentLibraryError(f"内容库格式错误：环境弹幕 ID 重复 {bid!r}")
            self.ambient_by_id[bid] = b
            for lt in b["live_types"]:
                self.ambient_by_live_type.setdefault(lt, []).append(b)
        self.scenarios = scenarios
        self.rules = rules
        self.ambient = ambient
        return self

    @staticmethod
    def _validate_ambient(b: dict) -> None:
        cat = b.get("bullet_category")
        if cat not in AMBIENT_CATEGORIES:
            raise ContentLibraryError(
                f"内容库格式错误：环境弹幕 {b.get('bullet_id')!r} 的 "
                f"bullet_category={cat!r} 非法，必须是 {AMBIENT_CATEGORIES} 之一"
            )
        lts = b.get("live_types")
        if not isinstance(lts, list) or not lts:
            raise ContentLibraryError(
                f"内容库格式错误：环境弹幕 {b.get('bullet_id')!r} 的 live_types 必须是非空数组"
            )
        for lt in lts:
            if lt not in LIVE_TYPES:
                raise ContentLibraryError(
                    f"内容库格式错误：环境弹幕 {b.get('bullet_id')!r} 的 live_type={lt!r} 非法"
                )

    def select_scenarios(
        self,
        live_type: str,
        goal: Optional[str] = None,
        tags: Optional[List[str]] = None,
        difficulty: Optional[object] = None,
        sample_type: Optional[str] = None,
        limit: Optional[int] = None,
        seed: Optional[int] = None,
        must_scenario_ids: Optional[List[str]] = None,
    ) -> List[dict]:
        """按条件筛选场景。

        - ``live_type``：必填，``ecommerce / entertainment / knowledge``。
        - ``goal``：训练目标（自由文本），仅做轻量相关性排序，不做语义检索。
        - ``tags``：场景标签列表，命中任一即保留。
        - ``difficulty``：难度（整数或整数列表）。
        - ``sample_type``：``regular / complex / boundary / adversarial``。
        - ``must_scenario_ids``：本场选定的预设必考场景 ID（1–2 个），会优先进入
          结果；不传则不前置任何必考场景。这些场景与普通场景一样受
          sample_type/difficulty/tags 过滤，但始终受 live_type 过滤。
        - 结果按 scenario_id 去重，同一次调用不会出现重复场景。
        """
        if live_type not in LIVE_TYPES:
            raise ContentLibraryError(
                f"未知直播类型 {live_type!r}，必须是 {LIVE_TYPES} 之一"
            )

        selected: List[dict] = []
        seen: set = set()

        def add(sid: str) -> None:
            sc = self.scenarios_by_id.get(sid)
            if sc is not None and sc["live_type"] == live_type and sid not in seen:
                seen.add(sid)
                selected.append(sc)

        def matches(sc: dict) -> bool:
            if sample_type and sc.get("sample_type") != sample_type:
                return False
            if difficulty is not None:
                want = {difficulty} if isinstance(difficulty, int) else set(difficulty)
                if sc.get("difficulty") not in want:
                    return False
            if tags:
                if not (set(tags) & set(sc.get("tags") or [])):
                    return False
            return True

        if must_scenario_ids:
            for sid in must_scenario_ids:
                sc = self.scenarios_by_id.get(sid)
                if sc is not None and sc["live_type"] == live_type and matches(sc):
                    add(sid)

        rest = [
            s
            for s in self.scenarios
            if s["live_type"] == live_type and s["scenario_id"] not in seen and matches(s)
        ]
        if goal:
            rest = _rank_by_goal(rest, goal)
        if seed is not None:
            random.Random(seed).shuffle(rest)

        for sc in rest:
            if limit is not None and len(selected) >= limit:
                break
            selected.append(sc)
        if limit is not None:
            selected = selected[:limit]
        return selected

    def get_rule(self, rule_id: str) -> dict:
        rule = self.rules_by_id.get(rule_id)
        if rule is None:
            raise ContentLibraryError(f"教学规则不存在：{rule_id!r}")
        return rule

    def rules_for_live_type(self, live_type: str) -> List[dict]:
        if live_type not in LIVE_TYPES:
            raise ContentLibraryError(f"未知直播类型 {live_type!r}")
        return [self.rules_by_id[rid] for rid in self.rules_by_live_type.get(live_type, [])]

    def ambient_for_live_type(
        self, live_type: str, category: Optional[str] = None
    ) -> List[dict]:
        """筛选环境弹幕（无关/路人/直播间噪声）。

        - ``live_type``：必填，``ecommerce / entertainment / knowledge``。
        - ``category``：可选 ``unrelated / passerby / room_noise``；不传返回全部。
        - 返回该直播类型下匹配的环境弹幕列表（不排序、不打乱，去重交给调用方）。
        """
        if live_type not in LIVE_TYPES:
            raise ContentLibraryError(f"未知直播类型 {live_type!r}")
        if category is not None and category not in AMBIENT_CATEGORIES:
            raise ContentLibraryError(
                f"未知环境弹幕分类 {category!r}，必须是 {AMBIENT_CATEGORIES} 之一"
            )
        return [
            b
            for b in self.ambient_by_live_type.get(live_type, [])
            if category is None or b["bullet_category"] == category
        ]

    def adversarial_scenarios(self, live_type: str) -> List[dict]:
        """返回指定直播类型的刁难场景（sample_type=adversarial）。"""
        if live_type not in LIVE_TYPES:
            raise ContentLibraryError(f"未知直播类型 {live_type!r}")
        return [
            s
            for s in self.scenarios
            if s["live_type"] == live_type and s["sample_type"] == "adversarial"
        ]

    @property
    def adversarial_scenario_ids(self) -> set:
        """全部刁难场景 ID（用于反馈评分过滤）。"""
        return {s["scenario_id"] for s in self.scenarios if s["sample_type"] == "adversarial"}


def _rank_by_goal(scenarios: List[dict], goal: str) -> List[dict]:
    """轻量目标相关性排序：标签 / 观众意图与目标文本重叠越多越靠前。"""
    g = (goal or "").strip()
    if not g:
        return scenarios

    def score(sc: dict) -> int:
        hay = " ".join(
            [
                str(sc.get("viewer_intent", "")),
                " ".join(sc.get("tags") or []),
                str(sc.get("trigger", "")),
            ]
        )
        n = 0
        for token in sc.get("tags") or []:
            if token and token in g:
                n += 2
        for token in str(sc.get("viewer_intent", "")).split():
            if token and token in g:
                n += 2
        # 逐字重叠兜底（中文短目标）
        n += sum(1 for ch in set(g) if ch in hay)
        return n

    return sorted(scenarios, key=score, reverse=True)


def select_must_cover(live_type: str, seed: int) -> List[str]:
    """从指定直播类型的必考场景池中确定性选出 1–2 个场景 ID。

    - 只在 ``live_type`` 自己的必考池内轮换，不跨直播类型。
    - 以 ``seed``（练习 ID）做确定性轮换，连续练习得到不同组合；
      同一 seed 结果可复现。
    - 返回 1 或 2 个场景 ID（每场至少 1 个必考、最多 2 个）。
    """
    pool = MUST_COVER_SCENARIOS.get(live_type, [])
    if not pool:
        return []
    n = len(pool)
    start = seed % n
    count = 2 if (seed // n) % 2 == 0 else 1
    return [pool[(start + i) % n] for i in range(count)]


_lock = Lock()
_instance: Optional[ContentLibrary] = None


def get_library() -> ContentLibrary:
    """返回已加载的内容库（进程内单例，首次调用时加载）。"""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = ContentLibrary().load()
    return _instance


def reload_library() -> ContentLibrary:
    """强制重新加载（测试或内容库更新后使用）。"""
    global _instance
    with _lock:
        _instance = ContentLibrary().load()
    return _instance

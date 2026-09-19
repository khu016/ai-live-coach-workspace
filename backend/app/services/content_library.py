"""内容库读取服务。

在 ``backend/app/data/content_library/`` 下加载场景卡与规则卡，
用普通内存索引做筛选，不引入向量数据库 / RAG。

- 场景卡：``scenario_cards.jsonl``（60 张）
- 规则卡：``teaching_rules.jsonl``（20 张）
- 来源登记：``source_registry.json``
- 版本信息：``manifest.json``

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

# 预设必考场景：每个直播类型固定包含的高价值 / 高风险场景（按 live_type 硬编码）。
# 这些场景会优先进入每次练习，保证训练覆盖"必须练到"的关键情形。
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

    def load(self) -> "ContentLibrary":
        scenarios = _load_jsonl(SCENARIOS_FILE, "场景卡", SCENARIO_REQUIRED_FIELDS)
        rules = _load_jsonl(RULES_FILE, "规则卡", RULE_REQUIRED_FIELDS)
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
        self.scenarios = scenarios
        self.rules = rules
        return self

    def select_scenarios(
        self,
        live_type: str,
        goal: Optional[str] = None,
        tags: Optional[List[str]] = None,
        difficulty: Optional[object] = None,
        sample_type: Optional[str] = None,
        limit: Optional[int] = None,
        seed: Optional[int] = None,
        include_must: bool = True,
    ) -> List[dict]:
        """按条件筛选场景。

        - ``live_type``：必填，``ecommerce / entertainment / knowledge``。
        - ``goal``：训练目标（自由文本），仅做轻量相关性排序，不做语义检索。
        - ``tags``：场景标签列表，命中任一即保留。
        - ``difficulty``：难度（整数或整数列表）。
        - ``sample_type``：``regular / complex / boundary / adversarial``。
        - ``include_must``：是否优先包含预设必考场景（默认 True；必考场景与普通
          场景一样受 sample_type/difficulty/tags 过滤，但始终受 live_type 过滤）。
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

        if include_must:
            for sid in MUST_COVER_SCENARIOS.get(live_type, []):
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

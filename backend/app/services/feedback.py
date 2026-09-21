import json
import re

from ..schemas import FeedbackOut, Issue
from . import content_library
from .llm import call_chat
from .prompts import FEEDBACK_SYSTEM, feedback_user_prompt

DIMENSIONS = ("表达表现", "直播应对", "内容质量")
DIMENSION_MAP = {
    "表达表现": "表达表现",
    "表达": "表达表现",
    "语言表达": "表达表现",
    "直播应对": "直播应对",
    "应对": "直播应对",
    "互动应对": "直播应对",
    "内容质量": "内容质量",
    "内容": "内容质量",
}


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str):
        return [v]
    return [str(v)]


def _normalize_issue(it) -> Issue:
    dim = it.get("dimension") or it.get("维度") or ""
    dim = DIMENSION_MAP.get(dim, dim)
    if dim not in DIMENSIONS:
        raise ValueError(f"未知维度: {dim!r}")
    return Issue(
        dimension=dim,
        start_sec=float(it.get("start_sec") or it.get("start") or 0),
        end_sec=float(it.get("end_sec") or it.get("end") or 0),
        evidence=str(it.get("evidence") or it.get("证据") or ""),
        problem=str(it.get("problem") or it.get("问题") or ""),
        suggestion=str(it.get("suggestion") or it.get("建议") or ""),
        retrain_target=str(
            it.get("retrain_target") or it.get("重练目标") or dim
        ),
        trigger_bullet=it.get("trigger_bullet") or it.get("触发弹幕"),
        scenario_id=it.get("scenario_id") or it.get("场景ID"),
        rule_ids=_as_list(it.get("rule_ids") or it.get("命中规则")),
        missed_points=_as_list(it.get("missed_points") or it.get("未覆盖要点")),
        source_refs=_as_list(it.get("source_refs") or it.get("内容来源")),
    )


def _extract_json(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for pattern in (r"\[.*\]", r"\{.*\}"):
        m = re.search(pattern, cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                continue
    raise ValueError("无法解析模型输出为 JSON")


def parse_feedback(text: str) -> FeedbackOut:
    """宽容解析模型输出：兼容 markdown 代码块、多等价格式；失败抛异常供重试。"""
    data = _extract_json(text)
    if isinstance(data, list):
        data = {"issues": data, "top_issue_ids": []}
    issues_raw = data.get("issues", [])
    issues = [_normalize_issue(it) for it in issues_raw]
    top = data.get("top_issue_ids", [])
    if not top:
        top = list(range(min(2, len(issues))))
    return FeedbackOut(issues=issues, top_issue_ids=[int(x) for x in top])


def _sanitize_refs(fb: FeedbackOut, lib) -> FeedbackOut:
    """回溯字段服务端校验：去掉模型自造的 scenario_id / rule_id。

    保证反馈能追溯到真实存在的场景卡与规则卡，模型幻觉的 ID 一律置空 / 剔除。
    """
    known_scenarios = lib.scenarios_by_id
    known_rules = lib.rules_by_id
    for issue in fb.issues:
        if issue.scenario_id and issue.scenario_id not in known_scenarios:
            issue.scenario_id = None
        issue.rule_ids = [r for r in issue.rule_ids if r in known_rules]
    return fb


def _bget(b, key, default=None):
    val = getattr(b, key, None)
    if val is None and hasattr(b, "get"):
        val = b.get(key)
    return default if val is None else val


def _filter_non_scorable_evidence(fb: FeedbackOut, bullets, lib) -> FeedbackOut:
    """服务端校验：非评分/非必回弹幕不能作为负面反馈证据（不只依赖模型遵守）。

    1. ``trigger_bullet`` 命中"可评分=否"或"需回应=否"的弹幕 → 剔除该条 issue。
    2. 引用刁难场景（sample_type=adversarial）但缺少规则依据或可观察证据 → 剔除。
    """
    non_evidence_texts = set()
    for b in bullets or []:
        text = (_bget(b, "text") or "").strip()
        scorable = _bget(b, "scorable", True)
        requires = _bget(b, "requires_response", True)
        if text and (scorable is False or requires is False):
            non_evidence_texts.add(text)
    adversarial_ids = lib.adversarial_scenario_ids
    kept = []
    for issue in fb.issues:
        tb = (issue.trigger_bullet or "").strip()
        if tb and tb in non_evidence_texts:
            continue
        if issue.scenario_id and issue.scenario_id in adversarial_ids:
            if not issue.rule_ids or not issue.evidence:
                continue
        kept.append(issue)
    fb.issues = kept
    fb.top_issue_ids = [i for i in fb.top_issue_ids if i < len(kept)]
    return fb


def generate_feedback(training, segments, bullets=None, rules=None) -> FeedbackOut:
    """生成练后反馈。

    - ``segments``：确定转写片段列表（dict：{start, end, text}，实时识别的稳定结果）。
    - ``bullets``：本次练习实际出现的弹幕事件（BulletEvent 或带 meta 的字典）。
    - ``rules``：相关教学规则卡；为空时按直播类型从内容库自动加载。
    """
    lib = content_library.get_library()
    if rules is None:
        live_type_en = content_library.LIVE_TYPE_TO_EN.get(training.live_type)
        rules = lib.rules_for_live_type(live_type_en) if live_type_en else []
    messages = [
        {"role": "system", "content": FEEDBACK_SYSTEM},
        {
            "role": "user",
            "content": feedback_user_prompt(training, segments, bullets, rules),
        },
    ]
    last_err = None
    for _ in range(3):
        text = call_chat(messages)
        try:
            fb = _sanitize_refs(parse_feedback(text), lib)
            return _filter_non_scorable_evidence(fb, bullets, lib)
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"反馈解析失败（已重试）: {last_err}")

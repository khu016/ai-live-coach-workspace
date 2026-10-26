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
        assessment_status=it.get("assessment_status", "supported_issue"),
        material_evidence=str(it.get("material_evidence") or ""),
        applicability_reason=str(it.get("applicability_reason") or ""),
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
    notes = [_normalize_issue(it) for it in data.get("reference_notes", [])]
    return FeedbackOut(issues=issues, top_issue_ids=[int(x) for x in top], reference_notes=notes)


def _retain_issues(fb, kept):
    """删除问题后按原下标重映射，不能把重点指向另一条问题。"""
    positions = {id(issue): i for i, issue in enumerate(kept)}
    fb.top_issue_ids = [positions[id(fb.issues[i])] for i in fb.top_issue_ids
                        if 0 <= i < len(fb.issues) and id(fb.issues[i]) in positions][:2]
    fb.issues = kept
    return fb


def _sanitize_refs(fb: FeedbackOut, lib) -> FeedbackOut:
    """回溯字段服务端校验：去掉模型自造的 scenario_id / rule_id。

    保证反馈能追溯到真实存在的场景卡与规则卡，模型幻觉的 ID 一律置空 / 剔除。
    """
    known_scenarios = lib.scenarios_by_id
    known_rules = lib.rules_by_id
    for issue in [*fb.issues, *fb.reference_notes]:
        if issue.scenario_id and issue.scenario_id not in known_scenarios:
            issue.scenario_id = None
        issue.rule_ids = [r for r in issue.rule_ids if r in known_rules]
        allowed_sources = set()
        for rid in issue.rule_ids:
            allowed_sources.update(known_rules[rid].get("source_refs", []))
        if issue.scenario_id:
            allowed_sources.update(known_scenarios[issue.scenario_id].get("source_refs", []))
        issue.source_refs = [sid for sid in issue.source_refs if sid in allowed_sources
                             and sid in lib.sources_by_id]
        issue.source_details = [lib.sources_by_id[sid] for sid in issue.source_refs]
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
        display_at = _bget(b, "display_at", _bget(b, "at_sec"))
        if text and (scorable is False or requires is False or display_at is None):
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
    return _retain_issues(fb, kept)


def _looks_like_question_only(text: str) -> bool:
    """判断证据是否只是收集偏好的问句，而非包含事实断言的反问。"""
    evidence = (text or "").strip()
    if not evidence:
        return False
    question_markers = ("？", "?", "吗", "还是", "最关心", "想听", "想看")
    risky_assertions = (
        "一定", "绝对", "保证", "百分百", "全网最低", "治好", "都能", "肯定有效"
    )
    return any(m in evidence for m in question_markers) and not any(
        m in evidence for m in risky_assertions
    )


def _filter_question_as_claim(fb: FeedbackOut) -> FeedbackOut:
    """服务端兜底：纯偏好问句不能被当作未核实商品承诺。"""
    claim_terms = ("承诺", "编造", "未经核实", "商品资料", "资料不足", "无法确认")
    kept = []
    for issue in fb.issues:
        combined = f"{issue.problem} {issue.suggestion}"
        if _looks_like_question_only(issue.evidence) and any(
            term in combined for term in claim_terms
        ):
            continue
        kept.append(issue)
    return _retain_issues(fb, kept)


def _apply_reference_policy(fb, lib, rules, segments, training):
    """平台候选规则只产生独立参考项；来源及证据边界服务端执行。"""
    allowed = {r["rule_id"]: r for r in rules
               if r.get("enabled_for_scoring", True) or r.get("enabled_for_reference", False)}
    notes = []
    kept = []
    seen = {}
    original_notes = {id(i) for i in fb.reference_notes}
    for issue in [*fb.issues, *fb.reference_notes]:
        original_ids = list(issue.rule_ids)
        issue.rule_ids = [rid for rid in original_ids if rid in allowed]
        if original_ids and not issue.rule_ids:
            continue
        platform_rules = [allowed[rid] for rid in issue.rule_ids if allowed[rid].get("platform")]
        legacy_fact_rules = {"R-COM-001", "R-COM-002", "R-TRU-001"}
        if (training.live_type == "带货" and legacy_fact_rules.intersection(issue.rule_ids)
                and issue.assessment_status == "supported_issue"):
            material = getattr(training, "product_info", None) or ""
            if not issue.material_evidence.strip() or issue.material_evidence not in material:
                issue.assessment_status = "needs_verification"
        if platform_rules:
            # 原话必须出现在所报时间范围相交的稳定转写中。
            quotes = [s.get("text", "") for s in segments
                      if s.get("start", 0) <= issue.end_sec and s.get("end", 0) >= issue.start_sec]
            if (not issue.evidence.strip() or issue.start_sec < 0
                    or issue.end_sec < issue.start_sec
                    or issue.evidence not in "".join(quotes)):
                continue
            if (issue.assessment_status == "supported_issue"
                    and any(not lib.rule_allows_issue(r) for r in platform_rules)):
                issue.assessment_status = "needs_verification"
            elif issue.assessment_status == "supported_issue":
                material = getattr(training, "product_info", None) or ""
                if (not issue.applicability_reason.strip() or not issue.material_evidence.strip()
                        or issue.material_evidence not in material):
                    issue.assessment_status = "needs_verification"
            issue.rule_versions = {r["rule_id"]: r["version"] for r in platform_rules}
            issue.source_refs = list(dict.fromkeys(
                sid for r in platform_rules for sid in r["source_refs"]))
            issue.source_details = [lib.sources_by_id[sid] for sid in issue.source_refs]
        is_note = id(issue) in original_notes or issue.assessment_status != "supported_issue"
        if is_note:
            if not issue.rule_ids:
                continue
            if issue.assessment_status == "supported_issue":
                issue.assessment_status = "needs_verification"
            # 待核实项目使用固定说明，避免保留模型输出的既定违规断言。
            if issue.assessment_status == "needs_verification":
                issue.problem = "宣传与承诺待核实：“" + issue.evidence + "”"
                issue.suggestion = "请核对适用规则现行版本及商品、活动或售后资料；当前参考项不作为已确认问题或扣分依据。"
                if platform_rules:
                    required = list(dict.fromkeys(item for r in platform_rules
                                                  for item in r.get("evidence_required", [])))
                    issue.suggestion = "请核对：" + "；".join(required) + "。相关规则现行版本仍需确认，本项不计入已确认问题。"
            target = notes
        else:
            target = kept
        if platform_rules or is_note:
            group = tuple(sorted({r.get("dedup_group", r["rule_id"]) for r in platform_rules}))
            key = (is_note, issue.start_sec, issue.end_sec, issue.evidence, () if is_note else group)
            if key in seen:
                previous = seen[key]
                previous.rule_ids = list(dict.fromkeys(previous.rule_ids + issue.rule_ids))
                previous.source_refs = list(dict.fromkeys(previous.source_refs + issue.source_refs))
                previous.rule_versions.update(issue.rule_versions)
                previous.source_details = [lib.sources_by_id[sid] for sid in previous.source_refs
                                           if sid in lib.sources_by_id]
                if platform_rules:
                    previous.suggestion = issue.suggestion
                continue
            seen[key] = issue
        target.append(issue)
    _retain_issues(fb, kept)
    fb.reference_notes = notes[:5]
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
            fb = _apply_reference_policy(parse_feedback(text), lib, rules, segments or [], training)
            fb = _sanitize_refs(fb, lib)
            fb = _filter_non_scorable_evidence(fb, bullets, lib)
            fb = _filter_question_as_claim(fb)
            return fb
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"反馈解析失败（已重试）: {last_err}")

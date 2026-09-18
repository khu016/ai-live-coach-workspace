import json
import re

from ..schemas import FeedbackOut, Issue
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


def generate_feedback(training, transcript) -> FeedbackOut:
    messages = [
        {"role": "system", "content": FEEDBACK_SYSTEM},
        {"role": "user", "content": feedback_user_prompt(training, transcript)},
    ]
    last_err = None
    for _ in range(3):
        text = call_chat(messages)
        try:
            return parse_feedback(text)
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"反馈解析失败（已重试）: {last_err}")

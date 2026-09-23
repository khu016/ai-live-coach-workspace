"""互动号召识别、回应生成与降级。

两层识别（PRD 4.5）：
1. 明确句式（扣数字、选项、固定关键词等）用确定性规则识别，保证低延迟与可测试。
2. 规则未覆盖的自然表达交给 AI 做结构化判断。

识别结果含：是否互动号召、互动类型、要求回复什么、允许的回复形式、置信度、触发转写 id。

回应生成：AI 输出结构化回应数组；模型超时/失败/非法时，用可验证的预设回应组降级
（数字口令必须含数字、选项只能从给定选项或"都喜欢/还没决定"、关键词必须含关键词）。

本模块只做识别与生成，不负责调度；调度队列在 ``ambient_bullets.BulletScheduler``。
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from ..core.config import settings
from .llm import call_chat
from .prompts import ENGAGEMENT_DETECT_SYSTEM, engagement_detect_user_prompt
from .prompts import ENGAGEMENT_RESPONSE_SYSTEM, engagement_response_user_prompt


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# 互动类型（内部 code，入库用）
DIGIT = "digit"          # 数字口令：扣1、扣666
OPTION = "option"        # 选项互动：选A还是B
KEYWORD = "keyword"      # 判断/关键词：听懂的打个懂
CHECKIN = "checkin"      # 报到/地域：新来的报到、哪里人打在公屏
EMOTION = "emotion"      # 情绪/动作：喜欢的举手、点个赞
CHAIN = "chain"          # 接龙/复述：下一句大家接、把关键词打出来
OPEN = "open"            # 开放意见：你们想先看哪个

INTERACTION_TYPES = (DIGIT, OPTION, KEYWORD, CHECKIN, EMOTION, CHAIN, OPEN)

# 互动类型英文 code → 中文标签（供测试/展示）
INTERACTION_LABELS = {
    DIGIT: "数字口令",
    OPTION: "选项互动",
    KEYWORD: "判断关键词",
    CHECKIN: "报到地域",
    EMOTION: "情绪动作",
    CHAIN: "接龙复述",
    OPEN: "开放意见",
}


@dataclass
class EngagementDetection:
    is_engagement_call: bool
    interaction_type: str = ""
    requested_response: str = ""
    allowed_response_form: str = ""
    confidence: float = 0.0
    source: str = "rule"
    trigger_segment_id: Optional[int] = None
    trigger_text: str = ""
    reason: str = ""


# ---------------------------------------------------------------------------
# 第一层：确定性规则识别
# ---------------------------------------------------------------------------

def _match_digit(text: str) -> Optional[EngagementDetection]:
    """数字口令：扣1 / 扣个1 / 扣666 / 打1 / 刷1 / 回1。"""
    patterns = (
        r"扣\s*(?:个|一波|个)?\s*(\d{1,5})",
        r"打\s*(\d{1,5})",
        r"刷\s*(\d{1,5})",
        r"回\s*(\d{1,5})",
    )
    for p in patterns:
        m = re.search(p, text)
        if m:
            digits = m.group(1)
            return EngagementDetection(
                is_engagement_call=True,
                interaction_type=DIGIT,
                requested_response=digits,
                allowed_response_form=f"digit:{digits}",
                confidence=0.95,
                trigger_text=text,
            )
    return None


def _match_option(text: str) -> Optional[EngagementDetection]:
    """选项互动：选A还是B / A还是B / A和B选一个。"""
    m = re.search(r"选?\s*([A-Za-z])\s*还是\s*([A-Za-z])", text)
    if not m:
        m = re.search(r"([A-Za-z])\s*和\s*([A-Za-z])\s*选", text)
    if m:
        a, b = m.group(1).upper(), m.group(2).upper()
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=OPTION,
            requested_response=f"{a}|{b}",
            allowed_response_form=f"option:{a}|{b}",
            confidence=0.92,
            trigger_text=text,
        )
    return None


def _match_keyword(text: str) -> Optional[EngagementDetection]:
    """判断/关键词：听懂的打个懂 / 懂的扣懂 / 同意的说是 / 明白的打明白。"""
    patterns = (
        r"(?:听懂|明白|懂|同意|想要|要|觉得)的?\s*(?:打个|扣|刷|回|说|打个)\s*([\u4e00-\u9fa5]{1,4})",
        r"(?:打个|扣个)\s*([\u4e00-\u9fa5]{1,4})",
    )
    for p in patterns:
        m = re.search(p, text)
        if m:
            kw = m.group(1)
            # 排除把"报到/点赞/接龙"等误判为关键词（交给更专门规则）
            if kw in ("报到", "赞", "点赞", "举", "举手", "接龙"):
                continue
            return EngagementDetection(
                is_engagement_call=True,
                interaction_type=KEYWORD,
                requested_response=kw,
                allowed_response_form=f"keyword:{kw}",
                confidence=0.9,
                trigger_text=text,
            )
    return None


def _match_checkin(text: str) -> Optional[EngagementDetection]:
    """报到/地域：新来的报到 / 报个到 / 哪里人打在公屏 / 打公屏。"""
    if re.search(r"报到", text) or re.search(r"报个到", text):
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=CHECKIN,
            requested_response="报到",
            allowed_response_form="checkin",
            confidence=0.9,
            trigger_text=text,
        )
    if re.search(r"哪里人|哪的人|打在公屏|公屏", text):
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=CHECKIN,
            requested_response="地域",
            allowed_response_form="checkin:location",
            confidence=0.85,
            trigger_text=text,
        )
    return None


def _match_emotion(text: str) -> Optional[EngagementDetection]:
    """情绪/动作：喜欢的举手 / 点个赞 / 点赞 / 想继续听的点个赞 / 比心。"""
    if re.search(r"举手", text):
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=EMOTION,
            requested_response="举手",
            allowed_response_form="emotion:举手",
            confidence=0.9,
            trigger_text=text,
        )
    if re.search(r"点赞|点个赞|赞一个|扣个赞", text):
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=EMOTION,
            requested_response="点赞",
            allowed_response_form="emotion:点赞",
            confidence=0.9,
            trigger_text=text,
        )
    if re.search(r"比心|扣个心", text):
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=EMOTION,
            requested_response="比心",
            allowed_response_form="emotion:比心",
            confidence=0.9,
            trigger_text=text,
        )
    return None


def _match_chain(text: str) -> Optional[EngagementDetection]:
    """接龙/复述：接龙 / 把关键词打出来 / 打出关键词 / 复述 / 跟读 / 跟着念。"""
    if re.search(r"接龙", text):
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=CHAIN,
            requested_response="接龙",
            allowed_response_form="chain",
            confidence=0.88,
            trigger_text=text,
        )
    if re.search(r"(?:把)?关键词打出来|打出关键词|打出来", text):
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=CHAIN,
            requested_response="关键词",
            allowed_response_form="chain:keyword",
            confidence=0.85,
            trigger_text=text,
        )
    if re.search(r"复述|跟读|跟着念|跟着说", text):
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=CHAIN,
            requested_response="复述",
            allowed_response_form="chain:repeat",
            confidence=0.85,
            trigger_text=text,
        )
    return None


def _match_open(text: str) -> Optional[EngagementDetection]:
    """开放意见：想先看哪个 / 想看哪个 / 还想听什么 / 你们想先看 / 想听什么。"""
    if re.search(r"想(?:先)?看(?:哪个|什么|哪)", text) or re.search(
        r"(?:还想|想)听(?:什么|哪个|哪)", text
    ) or re.search(r"你们想(?:先|要)?", text):
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=OPEN,
            requested_response="意见",
            allowed_response_form="open",
            confidence=0.8,
            trigger_text=text,
        )
    return None


_RULE_MATCHERS = (
    _match_digit,
    _match_option,
    _match_keyword,
    _match_checkin,
    _match_emotion,
    _match_chain,
    _match_open,
)


def detect_by_rules(text: str) -> Optional[EngagementDetection]:
    """确定性规则识别。返回首个命中的互动号召，未命中返回 None。"""
    t = (text or "").strip()
    if not t:
        return None
    for matcher in _RULE_MATCHERS:
        det = matcher(t)
        if det is not None:
            return det
    return None


# ---------------------------------------------------------------------------
# 第二层：AI 结构化识别
# ---------------------------------------------------------------------------

def _parse_json(text: str) -> dict:
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


def detect_by_ai(text: str, segment_id: Optional[int] = None) -> Optional[EngagementDetection]:
    """AI 结构化判断（规则未覆盖的自然表达）。失败返回 None（按普通弹幕处理）。"""
    messages = [
        {"role": "system", "content": ENGAGEMENT_DETECT_SYSTEM},
        {"role": "user", "content": engagement_detect_user_prompt(text)},
    ]
    try:
        raw = call_chat(messages, timeout=3.0, max_retries=0)
        data = _parse_json(raw)
        if not data.get("is_engagement_call"):
            return None
        itype = str(data.get("interaction_type") or "").strip()
        if itype not in INTERACTION_TYPES:
            return None
        requested = str(data.get("requested_response") or "").strip()
        if not requested:
            return None
        try:
            confidence = float(data.get("confidence") or 0.6)
        except (TypeError, ValueError):
            confidence = 0.6
        if confidence < 0.6:
            return None
        return EngagementDetection(
            is_engagement_call=True,
            interaction_type=itype,
            requested_response=requested,
            allowed_response_form=str(data.get("allowed_response_form") or ""),
            confidence=confidence,
            source="ai",
            trigger_segment_id=segment_id,
            trigger_text=text,
            reason=str(data.get("reason") or ""),
        )
    except Exception:  # noqa: BLE001
        return None


def classify_engagement(
    text: str,
    segment_id: Optional[int] = None,
    use_ai: bool = True,
) -> Optional[EngagementDetection]:
    """两层识别入口：先规则，规则未命中且允许 AI 时再走 AI。"""
    det = detect_by_rules(text)
    if det is not None:
        det.trigger_segment_id = segment_id
        return det
    if use_ai:
        return detect_by_ai(text, segment_id)
    return None


# ---------------------------------------------------------------------------
# 回应生成与降级
# ---------------------------------------------------------------------------

def preset_responses(det: EngagementDetection, count: int = 3) -> List[str]:
    """确定性预设回应组（DeepSeek 不可用时的降级）。数字/选项/关键词必须符合指令。"""
    count = max(2, min(4, count))
    itype = det.interaction_type
    requested = det.requested_response or ""

    if itype == DIGIT:
        d = re.search(r"\d{1,5}", requested)
        digit = d.group(0) if d else "1"
        pool = [digit, digit + digit, digit + "！", f"扣{digit}"]
    elif itype == OPTION:
        opts = [o for o in re.split(r"[|/]", requested) if o.strip()]
        opts = opts[:2] if opts else ["A", "B"]
        a, b = opts[0], (opts[1] if len(opts) > 1 else "B")
        pool = [a, f"选{a}", b, f"{a}吧"]
    elif itype == KEYWORD:
        kw = requested
        pool = [kw, kw + "了", kw + kw, "我" + kw]
    elif itype == CHECKIN:
        if "location" in (det.allowed_response_form or ""):
            pool = ["我在上海", "北京", "广州", "杭州"]
        else:
            pool = ["报到", "来了", "新来的报到", "报到！"]
    elif itype == EMOTION:
        action = requested or "点赞"
        pool = [action, "已" + action, action + "一个", "我" + action + "了"]
    elif itype == CHAIN:
        pool = ["接上", "跟上", "继续接", "来了"]
    elif itype == OPEN:
        pool = ["先讲产品", "想看实操", "都行", "先讲价格"]
    else:
        pool = ["好的", "收到", "支持", "来了"]

    # 去重并截取，保证有差异
    seen = set()
    out = []
    for item in pool:
        if item not in seen:
            seen.add(item)
            out.append(item)
        if len(out) >= count:
            break
    return out


def generate_responses_ai(
    training,
    det: EngagementDetection,
    history_bullets: Optional[List[dict]] = None,
    count: int = 3,
) -> List[str]:
    """AI 生成回应组（结构化数组）。失败时调用方降级到 preset_responses。"""
    messages = [
        {"role": "system", "content": ENGAGEMENT_RESPONSE_SYSTEM},
        {
            "role": "user",
            "content": engagement_response_user_prompt(
                training, det, history_bullets, count
            ),
        },
    ]
    raw = call_chat(messages, timeout=settings.bullet_generate_timeout_sec, max_retries=0)
    data = _parse_json(raw)
    items = data.get("responses")
    if not isinstance(items, list) or not items:
        raise ValueError("模型未返回回应数组")
    cleaned = []
    for it in items:
        s = str(it).strip()
        if not s or len(s) > 35:
            continue
        if s not in cleaned:
            cleaned.append(s)
    if not cleaned:
        raise ValueError("模型返回的回应全部为空或超长")
    return _validate_responses(det, cleaned[:count])


def _validate_responses(det: EngagementDetection, responses: List[str]) -> List[str]:
    """回应指令符合度校验：数字含数字、选项限给定项、关键词含关键词。

    不合格的回应会被剔除；全部不合格时抛异常触发降级。
    """
    itype = det.interaction_type
    kept = []
    if itype == DIGIT:
        d = re.search(r"\d{1,5}", det.requested_response or "")
        digit = d.group(0) if d else None
        for r in responses:
            if digit and digit in r:
                kept.append(r)
    elif itype == OPTION:
        opts = {o.strip() for o in re.split(r"[|/]", det.requested_response or "") if o.strip()}
        allowed = opts | {"都喜欢", "还没决定", "都行"}
        for r in responses:
            if any(o in r for o in opts) or any(a in r for a in ("都喜欢", "还没决定", "都行")):
                kept.append(r)
    elif itype == KEYWORD:
        kw = (det.requested_response or "").strip()
        for r in responses:
            if kw and kw in r:
                kept.append(r)
    else:
        kept = list(responses)
    if not kept:
        raise ValueError("所有回应均不符合指令，触发降级")
    return kept


def generate_response_group(
    training,
    det: EngagementDetection,
    history_bullets: Optional[List[dict]] = None,
    count: int = 3,
) -> List[str]:
    """生成回应组：优先 AI，失败/非法用预设降级（不静默消失）。

    无模型 Key 时直接走预设，避免无效网络/异常路径。
    """
    if not settings.model_api_key:
        return preset_responses(det, count)
    try:
        return generate_responses_ai(training, det, history_bullets, count)
    except Exception:  # noqa: BLE001
        return preset_responses(det, count)


# ---------------------------------------------------------------------------
# 持久化
# ---------------------------------------------------------------------------

def save_engagement_call(training_id: int, det: EngagementDetection, segment_id, responses: List[str]):
    """把互动号召事件落库（status=generated），返回事件对象。

    使用独立 Session，避免与 WebSocket 主协程共享。回应弹幕在展示后由
    ``record_engagement_bullet`` 回填 bullet_ids 与 shown_at。
    """
    from ..db import SessionLocal
    from ..models import EngagementCall

    db = SessionLocal()
    try:
        call = EngagementCall(
            training_id=training_id,
            trigger_segment_id=segment_id,
            trigger_text=det.trigger_text or "",
            interaction_type=det.interaction_type,
            requested_response=det.requested_response,
            allowed_response_form=det.allowed_response_form,
            confidence=det.confidence,
            source=det.source,
            status="generated",
            generated_at=_utcnow(),
            bullet_ids=[],
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call
    finally:
        db.close()


def record_engagement_bullet(call_id: int, bullet_id: int) -> None:
    """回应弹幕展示后回填事件状态（bullet_ids + shown_at）。"""
    from ..db import SessionLocal
    from ..models import EngagementCall

    db = SessionLocal()
    try:
        call = db.get(EngagementCall, call_id)
        if call is None:
            return
        ids = list(call.bullet_ids or [])
        if bullet_id not in ids:
            ids.append(bullet_id)
        call.bullet_ids = ids
        call.shown_at = _utcnow()
        call.status = "shown"
        db.commit()
    finally:
        db.close()


def mark_engagement_failed(call_id: int, reason: str) -> None:
    """互动号召生成/展示失败时记录失败原因（不静默丢失）。"""
    from ..db import SessionLocal
    from ..models import EngagementCall

    db = SessionLocal()
    try:
        call = db.get(EngagementCall, call_id)
        if call is None:
            return
        call.status = "failed"
        call.failure_reason = reason
        db.commit()
    finally:
        db.close()

"""教程内容、学习进度与训练后推荐。"""

import json
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from ..models import TutorialProgress, now
from .content_library import ContentLibraryError

TUTORIALS_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "content_library" / "tutorials.json"
)


def load_tutorials() -> list[dict]:
    if not TUTORIALS_FILE.exists():
        raise ContentLibraryError(f"教程内容文件不存在：{TUTORIALS_FILE}")
    try:
        value = json.loads(TUTORIALS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentLibraryError(f"教程内容无法读取：{exc}") from exc
    if not isinstance(value, list) or not value:
        raise ContentLibraryError("教程内容必须是非空数组")
    required = {
        "id", "title", "category", "durationMin", "level", "description",
        "tags", "objective", "whenToUse", "steps", "badExample", "goodExample",
        "mistakes", "checklist", "practiceTopic", "ruleRefs", "reviewStatus",
    }
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or required - item.keys():
            raise ContentLibraryError("教程内容存在缺失字段")
        if item["id"] in seen:
            raise ContentLibraryError(f"教程 ID 重复：{item['id']}")
        seen.add(item["id"])
    return value


def get_tutorial(tutorial_id: str) -> dict | None:
    return next((item for item in load_tutorials() if item["id"] == tutorial_id), None)


def progress_summary(db: Session, user_id: int = 1) -> dict:
    tutorials = load_tutorials()
    valid_ids = {item["id"] for item in tutorials}
    rows = db.query(TutorialProgress).filter_by(user_id=user_id, completed=True).all()
    completed_ids = [row.tutorial_id for row in rows if row.tutorial_id in valid_ids]
    return {
        "completed_ids": completed_ids,
        "completed_count": len(completed_ids),
        "total": len(tutorials),
    }


def set_completed(db: Session, tutorial_id: str, completed: bool, user_id: int = 1) -> dict:
    if get_tutorial(tutorial_id) is None:
        raise KeyError(tutorial_id)
    row = db.query(TutorialProgress).filter_by(user_id=user_id, tutorial_id=tutorial_id).first()
    timestamp = now()
    if row is None:
        row = TutorialProgress(
            user_id=user_id,
            tutorial_id=tutorial_id,
            started_at=timestamp,
        )
        db.add(row)
    row.completed = completed
    row.completed_at = timestamp if completed else None
    row.updated_at = timestamp
    db.commit()
    db.refresh(row)
    return {
        "tutorial_id": row.tutorial_id,
        "completed": row.completed,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


RULE_TO_TUTORIAL = {
    "R-TOP-001": "cold-start",
    "R-TIM-002": "bullet-priority",
    "R-TIM-003": "bullet-priority",
    "R-TIM-004": "tough-comments",
    "R-REL-003": "tough-comments",
    "R-TRU-001": "tough-comments",
    "R-COM-001": "tough-comments",
    "R-EXP-002": "pace-and-pause",
    "R-REL-002": "product-and-price",
    "R-COM-002": "product-and-price",
    "R-TOP-002": "entertainment-topic",
    "R-REL-005": "knowledge-structure",
    "R-TRU-003": "knowledge-structure",
}

KEYWORD_TO_TUTORIAL = (
    (("开场", "留人", "进入直播"), "opening-30s"),
    (("冷场", "没人", "空场"), "cold-start"),
    (("互动号召", "扣1", "扣 1", "观众回应"), "engagement-call"),
    (("质疑", "刁难", "承诺", "真实性", "争辩"), "tough-comments"),
    (("弹幕", "筛选", "优先回应", "漏回"), "bullet-priority"),
    (("节奏", "语速", "停顿", "流畅"), "pace-and-pause"),
    (("价格", "报价", "商品", "产品", "优惠"), "product-and-price"),
    (("话题", "接话", "转场", "娱乐"), "entertainment-topic"),
    (("知识", "结构", "结论", "解释", "内容"), "knowledge-structure"),
)


def _issue_candidates(issue: dict) -> Iterable[str]:
    text = " ".join(
        str(issue.get(field) or "")
        for field in ("dimension", "problem", "suggestion", "retrain_target", "evidence")
    )
    for keywords, tutorial_id in KEYWORD_TO_TUTORIAL:
        if any(keyword in text for keyword in keywords):
            yield tutorial_id
    for rule_id in issue.get("rule_ids") or []:
        mapped = RULE_TO_TUTORIAL.get(rule_id)
        if mapped:
            yield mapped


def recommend(issues: list[dict], training_goal: str = "", training_topic: str = "") -> list[dict]:
    tutorials = load_tutorials()
    by_id = {item["id"]: item for item in tutorials}
    selected: list[str] = []
    for issue in issues:
        for tutorial_id in _issue_candidates(issue):
            if tutorial_id not in selected:
                selected.append(tutorial_id)
            if len(selected) == 2:
                break
        if len(selected) == 2:
            break
    if not selected:
        fallback = {"开场留人": "opening-30s", "冷场处理": "cold-start", "弹幕应答": "bullet-priority"}
        combined = f"{training_goal} {training_topic}"
        selected = [next((value for key, value in fallback.items() if key in combined), "opening-30s")]
    return [by_id[tutorial_id] for tutorial_id in selected if tutorial_id in by_id]

from typing import List, Optional

from pydantic import BaseModel, Field

LIVE_TYPES = ("带货", "娱乐互动", "知识内容")


class TrainingCreate(BaseModel):
    live_type: str
    goal: str = Field(min_length=1, max_length=200)
    topic: Optional[str] = Field(default=None, max_length=1000)
    product_info: Optional[str] = Field(default=None, max_length=1000)
    script: Optional[str] = Field(default=None, max_length=1000)


class BulletIn(BaseModel):
    at_sec: Optional[float] = None
    kind: str = "dynamic"
    text: str = Field(min_length=1, max_length=500)


class Issue(BaseModel):
    dimension: str
    start_sec: float
    end_sec: float
    evidence: str
    problem: str = ""
    suggestion: str = ""
    retrain_target: str = ""


class FeedbackOut(BaseModel):
    issues: List[Issue]
    top_issue_ids: List[int]

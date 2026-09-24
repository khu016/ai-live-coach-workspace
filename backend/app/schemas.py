from typing import List, Optional

from pydantic import BaseModel, Field

LIVE_TYPES = ("带货", "娱乐互动", "知识内容")
PRACTICE_MODES = ("focus", "full")
MEDIA_KINDS = ("video", "audio", "none")


class TrainingCreate(BaseModel):
    live_type: str
    goal: str = Field(min_length=1, max_length=200)
    topic: Optional[str] = Field(default=None, max_length=1000)
    product_info: Optional[str] = Field(default=None, max_length=1000)
    script: Optional[str] = Field(default=None, max_length=1000)
    # 练习方式：focus（难点练习）/ full（完整模拟）
    practice_mode: str = Field(default="full")
    # 媒体模式：video（摄像头开启）/ audio（仅麦克风）/ none（无媒体）
    media_kind: str = Field(default="video")


class BulletIn(BaseModel):
    at_sec: Optional[float] = None
    kind: str = "dynamic"
    text: str = Field(min_length=1, max_length=500)
    # 内容库场景回溯字段（可选；前端把脚本原样带回，旧客户端不传也能用）
    scenario_id: Optional[str] = None
    viewer_intent: Optional[str] = None
    sample_type: Optional[str] = None
    difficulty: Optional[int] = None
    must_cover: Optional[List[str]] = None
    failure_signals: Optional[List[str]] = None
    source_refs: Optional[List[str]] = None


class Issue(BaseModel):
    dimension: str
    start_sec: float
    end_sec: float
    evidence: str
    problem: str = ""
    suggestion: str = ""
    retrain_target: str = ""
    # 内容依据回溯字段（可选，兼容旧模型输出）
    trigger_bullet: Optional[str] = None
    scenario_id: Optional[str] = None
    rule_ids: List[str] = Field(default_factory=list)
    missed_points: List[str] = Field(default_factory=list)
    source_refs: List[str] = Field(default_factory=list)


class FeedbackOut(BaseModel):
    issues: List[Issue]
    top_issue_ids: List[int]


class TutorialProgressUpdate(BaseModel):
    completed: bool

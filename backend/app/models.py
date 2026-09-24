import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, default=1)
    live_type = Column(String(32), nullable=False)
    goal = Column(String(200), nullable=False)
    topic = Column(String(1000), nullable=True)
    product_info = Column(Text, nullable=True)
    script = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="created")
    prev_training_id = Column(Integer, nullable=True)
    # 练习方式：focus（难点练习） / full（完整模拟）。难点练习与完整模拟
    # 共用同一训练链路，仅前端体验与时长不同。
    practice_mode = Column(String(32), nullable=True, default="full")
    # 本场媒体模式：video（摄像头开启）/ audio（仅麦克风）/ none（无媒体）。
    # 决定报告页回放器类型与是否渲染录像窗口。
    media_kind = Column(String(32), nullable=True, default="video")
    # 本场选定的必考场景 ID（1–2 个，来自本直播类型的必考池）。
    # 新建按练习 ID 确定性轮换；重练继承原练习。持久化到库，进程重启可恢复。
    selected_must_cover_scenario_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=now)
    finished_at = Column(DateTime, nullable=True)


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    duration_sec = Column(Float, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    # 媒体类型：video / audio，决定报告页回放器类型。
    media_kind = Column(String(32), nullable=True, default="video")
    # 真实 MIME 类型（如 video/webm、audio/webm），用于返回正确 Content-Type。
    mime_type = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=now)


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, nullable=False, index=True)
    segments = Column(JSON, nullable=False, default=list)
    full_text = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=now)


class TranscriptSegment(Base):
    """确定转写片段（稳定语句），实时识别的反馈证据与动态弹幕触发依据。"""

    __tablename__ = "transcript_segments"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, nullable=False, index=True)
    source = Column(String(32), nullable=False, default="realtime")
    start_sec = Column(Float, nullable=True)
    end_sec = Column(Float, nullable=True)
    text = Column(Text, nullable=False, default="")
    seq = Column(Integer, nullable=True)
    word_list = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=now)


class BulletEvent(Base):
    __tablename__ = "bullet_events"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    text = Column(String(500), nullable=False)
    at_sec = Column(Float, nullable=True)
    source = Column(String(32), nullable=False, default="fixed")
    # 内容库场景回溯字段（兼容扩展：旧数据两列均为 NULL，不破坏原有 API）
    scenario_id = Column(String(64), nullable=True, index=True)
    meta = Column(JSON, nullable=True)
    # 证据链字段（动态弹幕）：触发类型 / 触发转写片段 / 触发依据 / 状态 / 主播回应片段
    trigger_type = Column(String(32), nullable=True)
    trigger_segment_id = Column(Integer, nullable=True)
    trigger_reason = Column(String(500), nullable=True)
    status = Column(String(32), nullable=True)
    response_segment_ids = Column(JSON, nullable=True)
    # 弹幕属性（评分与展示过滤用）：分类 / 是否需要回应 / 是否参与评分 / 难度 / 展示时间
    bullet_category = Column(String(32), nullable=True)
    requires_response = Column(Boolean, nullable=True)
    scorable = Column(Boolean, nullable=True)
    difficulty = Column(Integer, nullable=True)
    display_at = Column(Float, nullable=True)
    created_at = Column(DateTime, default=now)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, nullable=False, index=True)
    issues = Column(JSON, nullable=False, default=list)
    top_issue_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=now)


class TutorialProgress(Base):
    """个人主播的教程学习进度。第一版固定使用 user_id=1。"""

    __tablename__ = "tutorial_progress"
    __table_args__ = (UniqueConstraint("user_id", "tutorial_id", name="uq_tutorial_progress_user"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    tutorial_id = Column(String(64), nullable=False, index=True)
    completed = Column(Boolean, nullable=False, default=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=now, onupdate=now)


class EngagementCall(Base):
    """互动号召事件（不可静默丢弃的待回应队列）。

    稳定转写 → 识别互动号召 → 创建 engagement_call 事件 → 进入待回应队列 →
    等待可展示时间槽 → 生成并展示回应组 → 持久化每条回应及最终状态。
    """

    __tablename__ = "engagement_calls"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, nullable=False, index=True)
    # 触发该号召的确定转写片段 id
    trigger_segment_id = Column(Integer, nullable=True, index=True)
    # 主播原话（触发文本）
    trigger_text = Column(Text, nullable=False, default="")
    # 互动类型：数字口令 / 选项互动 / 判断关键词 / 报到地域 / 情绪动作 / 接龙复述 / 开放意见
    interaction_type = Column(String(32), nullable=False)
    # 主播要求观众回复什么（如"1""A还是B""懂"）
    requested_response = Column(String(200), nullable=False, default="")
    # 允许的回复形式（如 "digit:1" "option:A|B" "keyword:懂"）
    allowed_response_form = Column(String(64), nullable=True)
    # 识别置信度
    confidence = Column(Float, nullable=True)
    # 识别来源：rule（确定性规则）/ ai（模型结构化判断）
    source = Column(String(16), nullable=False, default="rule")
    # 状态：queued / generated / shown / failed / merged
    status = Column(String(32), nullable=False, default="queued")
    queued_at = Column(DateTime, default=now)
    generated_at = Column(DateTime, nullable=True)
    shown_at = Column(DateTime, nullable=True)
    failure_reason = Column(String(500), nullable=True)
    # 该号召最终生成的弹幕 ID 列表
    bullet_ids = Column(JSON, nullable=True)
    # 相邻重复号召合并到的那条事件 id（避免刷屏）
    merged_from_call_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=now)

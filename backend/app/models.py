import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
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
    created_at = Column(DateTime, default=now)
    finished_at = Column(DateTime, nullable=True)


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    duration_sec = Column(Float, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=now)


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, nullable=False, index=True)
    segments = Column(JSON, nullable=False, default=list)
    full_text = Column(Text, nullable=False, default="")
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
    created_at = Column(DateTime, default=now)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, nullable=False, index=True)
    issues = Column(JSON, nullable=False, default=list)
    top_issue_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=now)

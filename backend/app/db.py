from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from .core.config import settings

DB_PATH = settings.data_dir / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    """兼容迁移：为已存在的旧表补齐新增列（幂等，不删除任何数据）。

    SQLite 的 ``create_all`` 只建缺失的表，不会给旧表加列；这里针对
    ``bullet_events`` 新增的 ``scenario_id`` / ``meta`` / 证据链字段，以及
    ``trainings`` 新增的 ``selected_must_cover_scenario_ids`` 做 ALTER TABLE。
    """
    insp = inspect(engine)
    with engine.begin() as conn:
        if insp.has_table("bullet_events"):
            cols = {c["name"] for c in insp.get_columns("bullet_events")}
            if "scenario_id" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE bullet_events ADD COLUMN scenario_id VARCHAR(64)"
                )
            if "meta" not in cols:
                conn.exec_driver_sql("ALTER TABLE bullet_events ADD COLUMN meta JSON")
            for col, ddl in (
                ("trigger_type", "VARCHAR(32)"),
                ("trigger_segment_id", "INTEGER"),
                ("trigger_reason", "VARCHAR(500)"),
                ("status", "VARCHAR(32)"),
                ("response_segment_ids", "JSON"),
                ("bullet_category", "VARCHAR(32)"),
                ("requires_response", "BOOLEAN"),
                ("scorable", "BOOLEAN"),
                ("difficulty", "INTEGER"),
                ("display_at", "FLOAT"),
            ):
                if col not in cols:
                    conn.exec_driver_sql(
                        f"ALTER TABLE bullet_events ADD COLUMN {col} {ddl}"
                    )
        if insp.has_table("trainings"):
            tcols = {c["name"] for c in insp.get_columns("trainings")}
            if "selected_must_cover_scenario_ids" not in tcols:
                conn.exec_driver_sql(
                    "ALTER TABLE trainings ADD COLUMN "
                    "selected_must_cover_scenario_ids JSON"
                )

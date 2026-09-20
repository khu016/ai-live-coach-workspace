import threading

from ..db import SessionLocal
from ..models import BulletEvent, Feedback, Transcript, TranscriptSegment, Training, now
from . import content_library, feedback


def reset_results(db, training_id):
    for model in (Transcript, Feedback):
        db.query(model).filter_by(training_id=training_id).delete()
    db.commit()


def run_pipeline(training_id: int) -> None:
    """练后反馈流水线（实时转写优先，无离线转写）。

    实时阶段已把确定转写落库为 ``transcript_segments``、弹幕落库为
    ``bullet_events``（含触发依据）。这里直接用它们生成反馈；转写缺失时不
    阻塞、不伪造，用已有稳定文本与录像完成反馈（证据链可能为空，提示如实）。
    """

    def _run():
        db = SessionLocal()
        try:
            t = db.get(Training, training_id)
            if t is None:
                return
            t.status = "analyzing"
            db.commit()

            segs = (
                db.query(TranscriptSegment)
                .filter_by(training_id=training_id)
                .order_by(TranscriptSegment.start_sec, TranscriptSegment.id)
                .all()
            )
            bullets = (
                db.query(BulletEvent)
                .filter_by(training_id=training_id)
                .order_by(BulletEvent.at_sec, BulletEvent.id)
                .all()
            )
            live_type_en = content_library.LIVE_TYPE_TO_EN.get(t.live_type)
            rules = (
                content_library.get_library().rules_for_live_type(live_type_en)
                if live_type_en
                else []
            )
            segments = [
                {"start": s.start_sec, "end": s.end_sec, "text": s.text}
                for s in segs
            ]
            fb = feedback.generate_feedback(t, segments, bullets, rules)
            db.add(
                Feedback(
                    training_id=training_id,
                    issues=[i.model_dump() for i in fb.issues],
                    top_issue_ids=fb.top_issue_ids,
                )
            )
            t.status = "feedback_ready"
            t.finished_at = now()
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            t = db.get(Training, training_id)
            if t is not None:
                t.status = "failed"
                db.commit()
        finally:
            db.close()

    threading.Thread(target=_run, daemon=True).start()

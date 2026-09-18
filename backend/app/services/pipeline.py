import threading

from ..db import SessionLocal
from ..models import Feedback, Recording, Training, Transcript, now
from . import asr, feedback


def reset_results(db, training_id):
    for model in (Transcript, Feedback):
        db.query(model).filter_by(training_id=training_id).delete()
    db.commit()


def run_pipeline(training_id: int) -> None:
    def _run():
        db = SessionLocal()
        try:
            t = db.get(Training, training_id)
            if t is None:
                return
            rec = db.query(Recording).filter_by(training_id=training_id).first()
            if rec is None:
                raise RuntimeError("录像不存在")

            t.status = "transcribing"
            db.commit()

            result = asr.get_asr().transcribe(rec.file_path)
            db.add(
                Transcript(
                    training_id=training_id,
                    segments=result.get("segments", []),
                    full_text=result.get("full_text", ""),
                )
            )
            db.commit()

            t.status = "analyzing"
            db.commit()

            transcript = (
                db.query(Transcript).filter_by(training_id=training_id).first()
            )
            fb = feedback.generate_feedback(t, transcript)
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

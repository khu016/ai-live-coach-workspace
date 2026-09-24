from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.errors import not_found
from ..db import get_db
from ..models import Feedback, Training
from ..schemas import TutorialProgressUpdate
from ..services import tutorials as tutorial_svc

router = APIRouter(prefix="/tutorials", tags=["tutorials"])


@router.get("")
def list_tutorials(db: Session = Depends(get_db)):
    return {
        "tutorials": tutorial_svc.load_tutorials(),
        "progress": tutorial_svc.progress_summary(db),
    }


@router.get("/progress")
def get_progress(db: Session = Depends(get_db)):
    return tutorial_svc.progress_summary(db)


@router.get("/recommendations/{training_id}")
def get_recommendations(training_id: int, db: Session = Depends(get_db)):
    training = db.get(Training, training_id)
    if training is None:
        raise not_found("练习不存在")
    feedback = db.query(Feedback).filter_by(training_id=training_id).first()
    issues = feedback.issues if feedback else []
    return {
        "tutorials": tutorial_svc.recommend(
            issues,
            training_goal=training.goal,
            training_topic=training.topic or "",
        )
    }


@router.get("/{tutorial_id}")
def get_tutorial(tutorial_id: str, db: Session = Depends(get_db)):
    tutorial = tutorial_svc.get_tutorial(tutorial_id)
    if tutorial is None:
        raise not_found("教程不存在")
    progress = tutorial_svc.progress_summary(db)
    return {"tutorial": tutorial, "completed": tutorial_id in progress["completed_ids"]}


@router.put("/{tutorial_id}/progress")
def update_progress(
    tutorial_id: str,
    payload: TutorialProgressUpdate,
    db: Session = Depends(get_db),
):
    try:
        progress = tutorial_svc.set_completed(db, tutorial_id, payload.completed)
    except KeyError:
        raise not_found("教程不存在")
    return {"progress": progress, "summary": tutorial_svc.progress_summary(db)}

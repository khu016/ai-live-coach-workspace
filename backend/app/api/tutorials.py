from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.errors import not_found
from ..db import get_db
from ..models import Feedback, Training, User
from ..schemas import TutorialProgressUpdate
from ..services import tutorials as tutorial_svc
from ..services.auth import current_user
from ..services.analytics import record_event

router = APIRouter(prefix="/tutorials", tags=["tutorials"])


@router.get("")
def list_tutorials(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return {
        "tutorials": tutorial_svc.load_tutorials(),
        "progress": tutorial_svc.progress_summary(db, user.id),
    }


@router.get("/progress")
def get_progress(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return tutorial_svc.progress_summary(db, user.id)


@router.get("/recommendations/{training_id}")
def get_recommendations(
    training_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    training = db.query(Training).filter_by(id=training_id, user_id=user.id).first()
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
def get_tutorial(
    tutorial_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    tutorial = tutorial_svc.get_tutorial(tutorial_id)
    if tutorial is None:
        raise not_found("教程不存在")
    progress = tutorial_svc.progress_summary(db, user.id)
    record_event(
        db,
        "tutorial_viewed",
        user_id=user.id,
        route=f"/tutorials/{tutorial_id}",
        entity_type="tutorial",
        entity_id=tutorial_id,
        properties={"tutorial_id": tutorial_id},
    )
    return {"tutorial": tutorial, "completed": tutorial_id in progress["completed_ids"]}


@router.put("/{tutorial_id}/progress")
def update_progress(
    tutorial_id: str,
    payload: TutorialProgressUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    try:
        progress = tutorial_svc.set_completed(db, tutorial_id, payload.completed, user.id)
    except KeyError:
        raise not_found("教程不存在")
    if payload.completed:
        record_event(
            db,
            "tutorial_completed",
            user_id=user.id,
            route=f"/tutorials/{tutorial_id}",
            entity_type="tutorial",
            entity_id=tutorial_id,
            properties={"tutorial_id": tutorial_id},
        )
    return {"progress": progress, "summary": tutorial_svc.progress_summary(db, user.id)}

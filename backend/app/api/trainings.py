import json
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import bad_request, conflict, not_found
from ..db import get_db
from ..models import BulletEvent, Feedback, Recording, Training, Transcript
from ..schemas import LIVE_TYPES, BulletIn, TrainingCreate
from ..services import bullets as bullets_svc, content_library
from ..services.pipeline import reset_results, run_pipeline

router = APIRouter()

_MEDIA = {".webm": "video/webm", ".mp4": "video/mp4"}


def _training_dict(t: Training) -> dict:
    return {
        "id": t.id,
        "live_type": t.live_type,
        "goal": t.goal,
        "topic": t.topic,
        "product_info": t.product_info,
        "script": t.script,
        "status": t.status,
        "prev_training_id": t.prev_training_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "finished_at": t.finished_at.isoformat() if t.finished_at else None,
    }


def _bullet_event(training_id: int, b: BulletIn, lib) -> BulletEvent:
    """把客户端带回的弹幕落库，并附着内容库场景元数据。

    场景元数据以内容库为准（服务端权威）；客户端只提供 scenario_id 用于回溯，
    未知 scenario_id 时按客户端附带字段降级，仍无法识别则不写 meta。
    """
    sc = lib.scenarios_by_id.get(b.scenario_id) if b.scenario_id else None
    if sc is not None:
        meta = {
            "viewer_intent": sc.get("viewer_intent"),
            "sample_type": sc.get("sample_type"),
            "difficulty": sc.get("difficulty"),
            "must_cover": sc.get("must_cover") or [],
            "failure_signals": sc.get("failure_signals") or [],
            "source_refs": sc.get("source_refs") or [],
        }
        scenario_id = sc["scenario_id"]
    elif b.scenario_id:
        meta = {
            "viewer_intent": b.viewer_intent,
            "sample_type": b.sample_type,
            "difficulty": b.difficulty,
            "must_cover": b.must_cover or [],
            "failure_signals": b.failure_signals or [],
            "source_refs": b.source_refs or [],
        }
        scenario_id = b.scenario_id
    else:
        meta = None
        scenario_id = None
    return BulletEvent(
        training_id=training_id,
        kind=b.kind,
        text=b.text,
        at_sec=b.at_sec,
        source="client",
        scenario_id=scenario_id,
        meta=meta,
    )


def _get_training(db: Session, training_id: int) -> Training:
    t = db.get(Training, training_id)
    if t is None:
        raise not_found("练习不存在")
    return t


def _validate_video(head: bytes, filename: str) -> Optional[str]:
    name = (filename or "").lower()
    if name.endswith(".webm") and head[:4] == b"\x1a\x45\xdf\xa3":
        return ".webm"
    if name.endswith(".mp4") and b"ftyp" in head[:16]:
        return ".mp4"
    return None


@router.post("/trainings")
def create_training(payload: TrainingCreate, db: Session = Depends(get_db)):
    if payload.live_type not in LIVE_TYPES:
        raise bad_request(f"live_type 必须是 {LIVE_TYPES} 之一")
    t = Training(
        live_type=payload.live_type,
        goal=payload.goal,
        topic=payload.topic,
        product_info=payload.product_info,
        script=payload.script,
        status="created",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    script = bullets_svc.build_script(t.live_type, t.goal, t.topic, seed=t.id)
    return {"training": _training_dict(t), "script": script}


@router.get("/trainings/{training_id}")
def get_training(training_id: int, db: Session = Depends(get_db)):
    return {"training": _training_dict(_get_training(db, training_id))}


@router.post("/trainings/{training_id}/finish")
async def finish_training(
    training_id: int,
    file: UploadFile = File(...),
    bullets: str = Form(...),
    duration_sec: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    t = _get_training(db, training_id)
    if t.status not in ("created", "recording"):
        raise conflict("当前状态不可结束练习")

    try:
        bullets_raw = json.loads(bullets)
        bullet_items = [BulletIn(**b) for b in bullets_raw]
    except Exception:  # noqa: BLE001
        raise bad_request("bullets 必须是 JSON 数组")

    content = await file.read()
    ext = _validate_video(content[:16], file.filename)
    if ext is None:
        raise bad_request("录像格式不支持（仅 webm/mp4）或文件损坏")
    size = len(content)
    if size > settings.recording_max_mb * 1024 * 1024:
        raise bad_request("录像文件过大")
    if duration_sec is not None and duration_sec > settings.practice_max_sec:
        raise bad_request("练习时长超限")

    path = (
        settings.data_dir
        / "recordings"
        / f"{training_id}_{uuid4().hex[:8]}{ext}"
    )
    path.write_bytes(content)

    db.add(
        Recording(
            training_id=training_id,
            file_path=str(path),
            duration_sec=duration_sec,
            size_bytes=size,
        )
    )
    lib = content_library.get_library()
    for b in bullet_items:
        db.add(
            _bullet_event(training_id, b, lib)
        )
    t.status = "saved"
    db.commit()
    db.refresh(t)

    run_pipeline(training_id)
    return {"training": _training_dict(t)}


@router.get("/trainings/{training_id}/feedback")
def get_feedback(training_id: int, db: Session = Depends(get_db)):
    t = _get_training(db, training_id)
    resp = {"status": t.status, "feedback": None}
    if t.status == "feedback_ready":
        fb = db.query(Feedback).filter_by(training_id=training_id).first()
        if fb is not None:
            resp["feedback"] = {
                "issues": fb.issues,
                "top_issue_ids": fb.top_issue_ids,
            }
    return resp


@router.get("/trainings/{training_id}/recording")
def get_recording(training_id: int, db: Session = Depends(get_db)):
    t = _get_training(db, training_id)
    rec = db.query(Recording).filter_by(training_id=training_id).first()
    if rec is None:
        raise not_found("录像不存在")
    import os

    media = _MEDIA.get(os.path.splitext(rec.file_path)[1].lower(), "video/webm")
    return FileResponse(rec.file_path, media_type=media)


@router.post("/trainings/{training_id}/retrain")
def retrain(training_id: int, db: Session = Depends(get_db)):
    t = _get_training(db, training_id)
    if t.status != "feedback_ready":
        raise conflict("仅在反馈就绪后可重练")
    new_t = Training(
        live_type=t.live_type,
        goal=t.goal,
        topic=t.topic,
        product_info=t.product_info,
        script=t.script,
        status="created",
        prev_training_id=t.id,
    )
    db.add(new_t)
    db.commit()
    db.refresh(new_t)
    script = bullets_svc.build_script(
        new_t.live_type, new_t.goal, new_t.topic, seed=new_t.id
    )
    return {"training": _training_dict(new_t), "script": script}


@router.get("/trainings/{training_id}/compare")
def compare(training_id: int, db: Session = Depends(get_db)):
    t = _get_training(db, training_id)
    prev = (
        db.get(Training, t.prev_training_id)
        if t.prev_training_id
        else None
    )
    if prev is None:
        raise conflict("无上一次练习可对比")

    def _side(tr: Training):
        fb = db.query(Feedback).filter_by(training_id=tr.id).first()
        return {
            "training": _training_dict(tr),
            "issues": fb.issues if fb else [],
            "top_issue_ids": fb.top_issue_ids if fb else [],
        }

    return {"current": _side(t), "previous": _side(prev)}


@router.post("/trainings/{training_id}/retry")
def retry(training_id: int, db: Session = Depends(get_db)):
    t = _get_training(db, training_id)
    if t.status != "failed":
        raise conflict("仅失败状态可重试")
    reset_results(db, training_id)
    run_pipeline(training_id)
    return {"training": _training_dict(t)}

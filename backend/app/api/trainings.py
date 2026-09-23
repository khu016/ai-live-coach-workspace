import json
import os
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import bad_request, conflict, not_found
from ..db import get_db
from ..models import BulletEvent, Feedback, Recording, Training, Transcript
from ..schemas import LIVE_TYPES, MEDIA_KINDS, PRACTICE_MODES, BulletIn, TrainingCreate
from ..services import bullets as bullets_svc, content_library, stats
from ..services.pipeline import reset_results, run_pipeline

router = APIRouter()

_MEDIA = {
    ".webm": "video/webm",
    ".mp4": "video/mp4",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".m4a": "audio/mp4",
}


def _media_type(rec: Recording) -> str:
    """优先用落库的 mime_type，否则按扩展名推断，audio 时返回音频 MIME。"""
    if rec.mime_type:
        return rec.mime_type
    ext = os.path.splitext(rec.file_path)[1].lower()
    return _media_type_for(rec.media_kind or "video", ext)


def _media_type_for(kind: str, ext: str) -> str:
    base = _MEDIA.get(ext, "video/webm")
    if kind == "audio" and not base.startswith("audio/"):
        if base == "video/webm":
            return "audio/webm"
        if base == "video/mp4":
            return "audio/mp4"
    return base


def _training_dict(t: Training, rec: Optional[Recording] = None) -> dict:
    return {
        "id": t.id,
        "live_type": t.live_type,
        "goal": t.goal,
        "topic": t.topic,
        "product_info": t.product_info,
        "script": t.script,
        "status": t.status,
        "prev_training_id": t.prev_training_id,
        "practice_mode": t.practice_mode or "full",
        "media_kind": t.media_kind or "video",
        "selected_must_cover_scenario_ids": t.selected_must_cover_scenario_ids or [],
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        "media": _media_dict(rec) if rec is not None else None,
    }


def _media_dict(rec: Recording) -> dict:
    """媒体元数据：是否存在 / 类型 / MIME / 时长 / 大小。"""
    exists = bool(rec.file_path) and os.path.exists(rec.file_path)
    return {
        "exists": exists,
        "media_kind": rec.media_kind or "video",
        "mime_type": _media_type(rec),
        "duration_sec": rec.duration_sec,
        "size_bytes": rec.size_bytes,
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
    # 旧客户端带回的弹幕也补齐分类/评分字段，保证新训练记录不再为空
    if sc is not None and sc.get("sample_type") == "adversarial":
        bullet_category = "adversarial"
    elif b.kind == "fixed_question":
        bullet_category = "must_cover"
    else:
        bullet_category = "related"
    return BulletEvent(
        training_id=training_id,
        kind=b.kind,
        text=b.text,
        at_sec=b.at_sec,
        source="client",
        scenario_id=scenario_id,
        meta=meta,
        bullet_category=bullet_category,
        requires_response=True,
        scorable=True,
        difficulty=sc.get("difficulty") if sc is not None else b.difficulty,
        display_at=b.at_sec,
    )


def _get_training(db: Session, training_id: int) -> Training:
    t = db.get(Training, training_id)
    if t is None:
        raise not_found("练习不存在")
    return t


def _validate_media(head: bytes, filename: str, media_kind: str = "video") -> Optional[str]:
    """校验媒体文件真实类型，返回扩展名（webm/mp4/ogg）。

    - video：仅接受 webm / mp4（带视频轨）。
    - audio：接受 webm（仅音频轨，MediaRecorder）或 ogg。
    """
    name = (filename or "").lower()
    if media_kind == "audio":
        if name.endswith(".ogg") and head[:4] == b"OggS":
            return ".ogg"
        if name.endswith((".webm", ".ogg")) and head[:4] == b"\x1a\x45\xdf\xa3":
            return ".webm"
        if name.endswith(".m4a") and b"ftyp" in head[:16]:
            return ".m4a"
        return None
    if name.endswith(".webm") and head[:4] == b"\x1a\x45\xdf\xa3":
        return ".webm"
    if name.endswith(".mp4") and b"ftyp" in head[:16]:
        return ".mp4"
    return None


@router.post("/trainings")
def create_training(payload: TrainingCreate, db: Session = Depends(get_db)):
    if payload.live_type not in LIVE_TYPES:
        raise bad_request(f"live_type 必须是 {LIVE_TYPES} 之一")
    if payload.practice_mode not in PRACTICE_MODES:
        raise bad_request(f"practice_mode 必须是 {PRACTICE_MODES} 之一")
    if payload.media_kind not in MEDIA_KINDS:
        raise bad_request(f"media_kind 必须是 {MEDIA_KINDS} 之一")
    t = Training(
        live_type=payload.live_type,
        goal=payload.goal,
        topic=payload.topic,
        product_info=payload.product_info,
        script=payload.script,
        status="created",
        practice_mode=payload.practice_mode,
        media_kind=payload.media_kind,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    live_type_en = content_library.LIVE_TYPE_TO_EN.get(t.live_type)
    # 新建练习：按练习 ID 确定性轮换选出 1–2 个必考场景，持久化到训练记录。
    t.selected_must_cover_scenario_ids = content_library.select_must_cover(
        live_type_en, t.id
    )
    db.commit()
    db.refresh(t)
    script = bullets_svc.build_script(
        t.live_type,
        t.goal,
        t.topic,
        seed=t.id,
        selected_must_ids=t.selected_must_cover_scenario_ids,
    )
    return {"training": _training_dict(t), "script": script}


@router.get("/trainings/{training_id}")
def get_training(training_id: int, db: Session = Depends(get_db)):
    t = _get_training(db, training_id)
    rec = db.query(Recording).filter_by(training_id=training_id).first()
    return {"training": _training_dict(t, rec)}


@router.post("/trainings/{training_id}/finish")
async def finish_training(
    training_id: int,
    file: UploadFile = File(...),
    bullets: Optional[str] = Form(None),
    duration_sec: Optional[float] = Form(None),
    media_kind: Optional[str] = Form(None),
    mime_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    t = _get_training(db, training_id)
    if t.status not in ("created", "recording"):
        raise conflict("当前状态不可结束练习")

    # 媒体类型：优先用请求声明，其次沿用创建练习时保存的值，默认 video
    kind = media_kind or t.media_kind or "video"
    if kind not in MEDIA_KINDS:
        raise bad_request(f"media_kind 必须是 {MEDIA_KINDS} 之一")

    bullet_items = []
    if bullets:
        try:
            bullets_raw = json.loads(bullets)
            bullet_items = [BulletIn(**b) for b in bullets_raw]
        except Exception:  # noqa: BLE001
            raise bad_request("bullets 必须是 JSON 数组")

    content = await file.read()
    ext = _validate_media(content[:16], file.filename, kind)
    if ext is None:
        raise bad_request("媒体格式不支持（视频仅 webm/mp4，音频仅 webm/ogg）或文件损坏")
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
            media_kind=kind,
            mime_type=mime_type or _media_type_for(kind, ext),
        )
    )
    lib = content_library.get_library()
    for b in bullet_items:
        db.add(
            _bullet_event(training_id, b, lib)
        )
    t.status = "saved"
    t.media_kind = kind
    db.commit()
    db.refresh(t)

    run_pipeline(training_id)
    rec = db.query(Recording).filter_by(training_id=training_id).first()
    return {"training": _training_dict(t, rec)}


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


@router.get("/trainings/{training_id}/media")
def get_training_media(training_id: int, db: Session = Depends(get_db)):
    """返回媒体元数据：是否存在 / 类型 / MIME / 时长 / 大小。"""
    t = _get_training(db, training_id)
    rec = db.query(Recording).filter_by(training_id=training_id).first()
    if rec is None:
        return {"exists": False, "media_kind": t.media_kind or "none", "mime_type": None, "duration_sec": None, "size_bytes": None}
    return _media_dict(rec)


@router.get("/trainings/{training_id}/recording")
def get_recording(training_id: int, db: Session = Depends(get_db)):
    t = _get_training(db, training_id)
    rec = db.query(Recording).filter_by(training_id=training_id).first()
    if rec is None:
        raise not_found("录像不存在")
    if not os.path.exists(rec.file_path):
        raise not_found("录像文件不存在或已被删除")
    return FileResponse(rec.file_path, media_type=_media_type(rec))


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
        # 重练同一问题：继承原练习的必考场景，确保前后表现可比较。
        selected_must_cover_scenario_ids=t.selected_must_cover_scenario_ids,
    )
    db.add(new_t)
    db.commit()
    db.refresh(new_t)
    script = bullets_svc.build_script(
        new_t.live_type,
        new_t.goal,
        new_t.topic,
        seed=new_t.id,
        selected_must_ids=new_t.selected_must_cover_scenario_ids,
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


@router.delete("/trainings/{training_id}")
def delete_training(training_id: int, db: Session = Depends(get_db)):
    """删除训练及其媒体文件（个人主播本人触发）。"""
    t = _get_training(db, training_id)
    rec = db.query(Recording).filter_by(training_id=training_id).first()
    if rec is not None and rec.file_path and os.path.exists(rec.file_path):
        try:
            os.remove(rec.file_path)
        except OSError:  # noqa: BLE001
            pass
    db.query(Recording).filter_by(training_id=training_id).delete()
    db.query(BulletEvent).filter_by(training_id=training_id).delete()
    db.query(Feedback).filter_by(training_id=training_id).delete()
    db.query(Transcript).filter_by(training_id=training_id).delete()
    db.delete(t)
    db.commit()
    return {"deleted": True, "training_id": training_id}


@router.get("/trainings")
def list_trainings(db: Session = Depends(get_db)):
    """训练列表（真实记录，供首页最近练习与成长记录）。"""
    rows = (
        db.query(Training)
        .order_by(Training.finished_at.desc(), Training.id.desc())
        .limit(50)
        .all()
    )
    result = []
    for t in rows:
        rec = db.query(Recording).filter_by(training_id=t.id).first()
        result.append(_training_dict(t, rec))
    return {"trainings": result}


@router.get("/recordings")
def list_recordings(db: Session = Depends(get_db)):
    """真实媒体记录列表（含媒体是否存在/类型/MIME/时长/大小）。"""
    return {"recordings": stats.list_recordings()}


@router.get("/stats/week")
def week_stats(db: Session = Depends(get_db)):
    """真实训练统计（本周/上周），样本不足时返回 sample_sufficient=false。"""
    return stats.compute_week_stats()

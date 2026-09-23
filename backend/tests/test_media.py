"""媒体模式、真实回放、媒体列表与删除（PRD 4.3 / F07 / F23）。"""

import json

from app.api import trainings as t_mod
from app.db import SessionLocal
from app.models import Recording, Training

WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 64


def _create(client, **overrides):
    payload = {
        "live_type": "带货",
        "goal": "练习弹幕应答",
        "practice_mode": "full",
        "media_kind": "video",
    }
    payload.update(overrides)
    return client.post("/api/v1/trainings", json=payload)


def _finish(client, tid, media_kind="video", monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setattr(t_mod, "run_pipeline", lambda tid: None)
    return client.post(
        f"/api/v1/trainings/{tid}/finish",
        data={
            "bullets": "[]",
            "duration_sec": "10",
            "media_kind": media_kind,
        },
        files={"file": ("recording.webm", WEBM, "video/webm")},
    )


def test_create_practice_mode_and_media_kind(client):
    r = _create(client, practice_mode="focus", media_kind="audio")
    assert r.status_code == 200
    t = r.json()["training"]
    assert t["practice_mode"] == "focus"
    assert t["media_kind"] == "audio"
    assert isinstance(t["id"], int)


def test_create_invalid_media_kind(client):
    r = _create(client, media_kind="black")
    assert r.status_code == 400


def test_finish_audio_stores_audio_media(client, monkeypatch):
    """摄像头关闭、麦克风开启：保存音频媒体，media_kind=audio。"""
    tid = _create(client, media_kind="audio").json()["training"]["id"]
    resp = _finish(client, tid, media_kind="audio", monkeypatch=monkeypatch)
    assert resp.status_code == 200
    body = resp.json()["training"]
    assert body["media_kind"] == "audio"
    assert body["media"]["exists"] is True
    assert body["media"]["media_kind"] == "audio"
    assert body["media"]["mime_type"].startswith("audio/")

    db = SessionLocal()
    rec = db.query(Recording).filter_by(training_id=tid).first()
    assert rec.media_kind == "audio"
    db.close()


def test_finish_video_stores_video_media(client, monkeypatch):
    """摄像头开启：保存视频媒体，media_kind=video。"""
    tid = _create(client, media_kind="video").json()["training"]["id"]
    resp = _finish(client, tid, media_kind="video", monkeypatch=monkeypatch)
    assert resp.status_code == 200
    body = resp.json()["training"]
    assert body["media_kind"] == "video"
    assert body["media"]["mime_type"].startswith("video/")

    db = SessionLocal()
    rec = db.query(Recording).filter_by(training_id=tid).first()
    assert rec.media_kind == "video"
    db.close()


def test_recording_content_type_audio(client, monkeypatch):
    """音频回放接口返回 audio Content-Type。"""
    tid = _create(client, media_kind="audio").json()["training"]["id"]
    _finish(client, tid, media_kind="audio", monkeypatch=monkeypatch)
    r = client.get(f"/api/v1/trainings/{tid}/recording")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/webm")


def test_recording_content_type_video(client, monkeypatch):
    """视频回放接口返回 video Content-Type。"""
    tid = _create(client, media_kind="video").json()["training"]["id"]
    _finish(client, tid, media_kind="video", monkeypatch=monkeypatch)
    r = client.get(f"/api/v1/trainings/{tid}/recording")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("video/webm")


def test_media_not_exists(client):
    """无媒体时 media.exists=False（前端不渲染空白播放器）。"""
    tid = _create(client, media_kind="audio").json()["training"]["id"]
    r = client.get(f"/api/v1/trainings/{tid}/media")
    assert r.status_code == 200
    assert r.json()["exists"] is False
    assert r.json()["media_kind"] == "audio"


def test_recordings_list_real_only(client, monkeypatch):
    """媒体列表只返回真实后端记录。"""
    tid1 = _create(client, media_kind="video").json()["training"]["id"]
    tid2 = _create(client, media_kind="audio").json()["training"]["id"]
    _finish(client, tid1, media_kind="video", monkeypatch=monkeypatch)
    _finish(client, tid2, media_kind="audio", monkeypatch=monkeypatch)

    r = client.get("/api/v1/recordings")
    assert r.status_code == 200
    items = r.json()["recordings"]
    assert len(items) == 2
    kinds = {i["media_kind"] for i in items}
    assert kinds == {"video", "audio"}
    for i in items:
        assert isinstance(i["training_id"], int)
        assert i["exists"] is True


def test_delete_training_removes_media(client, monkeypatch):
    """删除操作真正调用后端删除接口并移除文件。"""
    tid = _create(client, media_kind="video").json()["training"]["id"]
    _finish(client, tid, media_kind="video", monkeypatch=monkeypatch)

    db = SessionLocal()
    rec = db.query(Recording).filter_by(training_id=tid).first()
    path = rec.file_path
    db.close()

    import os

    assert os.path.exists(path)
    r = client.delete(f"/api/v1/trainings/{tid}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    assert not os.path.exists(path)
    assert client.get(f"/api/v1/trainings/{tid}").status_code == 404

    r2 = client.get("/api/v1/recordings")
    assert all(i["training_id"] != tid for i in r2.json()["recordings"])


def test_delete_training_not_found(client):
    assert client.delete("/api/v1/trainings/999").status_code == 404

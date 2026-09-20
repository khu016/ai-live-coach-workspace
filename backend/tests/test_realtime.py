"""实时转写 WebSocket 端点与片段落库的测试（mock ASR，不连外网）。"""

from app.db import SessionLocal
from app.models import BulletEvent, TranscriptSegment
from app.services.asr_base import ASREvent
from app.services.realtime import event_to_message, save_segment


def test_save_segment(client):
    save_segment(
        1, ASREvent(kind="final", text="你好。", start_sec=0.0, end_sec=1.5, seq=0)
    )
    db = SessionLocal()
    rows = db.query(TranscriptSegment).filter_by(training_id=1).all()
    db.close()
    assert len(rows) == 1
    assert rows[0].text == "你好。"
    assert rows[0].source == "realtime"


def test_event_to_message():
    m = event_to_message(
        ASREvent(kind="partial", text="你好", start_sec=0.0, end_sec=0.5, seq=0)
    )
    assert m["type"] == "transcript"
    assert m["kind"] == "partial"
    assert m["text"] == "你好"


def test_asr_websocket_flow(client):
    r = client.post(
        "/api/v1/trainings", json={"live_type": "带货", "goal": "练习开场"}
    )
    assert r.status_code == 200
    tid = r.json()["training"]["id"]

    with client.websocket_connect(f"/api/v1/trainings/{tid}/asr/ws") as ws:
        ws.send_bytes(b"\x00\x01")
        m1 = ws.receive_json()
        assert m1["type"] == "transcript"
        assert m1["kind"] == "partial"

        ws.send_bytes(b"\x00\x01")
        m2 = ws.receive_json()
        assert m2["type"] == "transcript"
        assert m2["kind"] == "final"

        # 稳定片段触发必考弹幕（预设）
        m3 = ws.receive_json()
        assert m3["type"] == "bullet"
        assert m3["trigger_type"] == "预设必考"

        ws.send_text('{"type":"end"}')

    db = SessionLocal()
    segs = db.query(TranscriptSegment).filter_by(training_id=tid).all()
    bullets = db.query(BulletEvent).filter_by(training_id=tid).all()
    db.close()
    assert len(segs) >= 1
    assert all(s.source == "realtime" for s in segs)
    assert any(s.text == "大家好，欢迎来到我的直播间。" for s in segs)
    assert len(bullets) >= 1
    assert bullets[0].trigger_type == "预设必考"


def test_asr_websocket_not_found(client):
    with client.websocket_connect("/api/v1/trainings/99999/asr/ws") as ws:
        m = ws.receive_json()
        assert m["type"] == "error"

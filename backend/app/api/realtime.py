"""实时语音转写 WebSocket 路由（浏览器 ↔ 后端 ↔ 腾讯云）。

浏览器把麦克风 PCM（16kHz/16bit 单声道）分帧以二进制发到本端点，后端转发给
实时 ASR 供应商；供应商返回的临时/稳定转写事件回推给浏览器，稳定片段落库，
并交给动态弹幕引擎触发追问/质疑/普通互动/话题承接/冷场激活弹幕。

约定：
- 浏览器 → 后端：二进制帧 = PCM 音频；文本帧 {"type":"end"} = 结束转写。
- 后端 → 浏览器：
  {"type":"transcript", kind:"partial"|"final", text, start_sec, end_sec, seq}
  {"type":"bullet", text, at_sec, trigger_type, trigger_reason, status, ...}
  {"type":"asr_error", message} / {"type":"error", message}
腾讯云鉴权与密钥只在本后端，绝不下发浏览器。
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket

from ..db import SessionLocal
from ..models import Training
from ..services.asr_base import get_realtime_asr
from ..services.dynamic_bullets import DynamicBulletEngine
from ..services.realtime import (
    PCM_BYTES_PER_SEC,
    event_to_message,
    save_bullet,
    save_segment,
)

router = APIRouter()


@router.websocket("/trainings/{training_id}/asr/ws")
async def asr_ws(websocket: WebSocket, training_id: int):
    await websocket.accept()
    db = SessionLocal()
    try:
        t = db.get(Training, training_id)
        if t is None:
            await websocket.send_json({"type": "error", "message": "练习不存在"})
            await websocket.close()
            return
        if t.status not in ("created", "recording"):
            await websocket.send_json({"type": "error", "message": "当前状态不可开始实时转写"})
            await websocket.close()
            return
        if t.status == "created":
            t.status = "recording"
            db.commit()

        provider = get_realtime_asr()
        try:
            session = await provider.open_session(training_id=training_id)
        except Exception as e:  # noqa: BLE001
            await websocket.send_json({"type": "asr_error", "message": str(e)})
            await websocket.close()
            return

        engine = DynamicBulletEngine(t)
        total_audio_bytes = 0
        stop = asyncio.Event()

        async def _push(msg):
            try:
                await websocket.send_json(msg)
            except Exception:  # noqa: BLE001
                pass

        async def _process():
            try:
                while True:
                    ev = await session.receive_event()
                    if ev is None:
                        break
                    if ev.kind == "final" and ev.text.strip():
                        seg_id = save_segment(training_id, ev)
                        await _push(event_to_message(ev))
                        seg_dict = {
                            "id": seg_id,
                            "start_sec": ev.start_sec,
                            "end_sec": ev.end_sec,
                            "text": ev.text,
                        }
                        now_sec = ev.end_sec if ev.end_sec is not None else 0.0
                        draft = engine.on_final_segment(seg_dict, now_sec)
                        if draft is not None:
                            await _push(save_bullet(training_id, draft))
                    else:
                        await _push(event_to_message(ev))
            except Exception:  # noqa: BLE001
                await _push({"type": "asr_error", "message": "实时识别中断"})

        async def _cold_start_timer():
            nonlocal total_audio_bytes
            try:
                while not stop.is_set():
                    await asyncio.sleep(1.0)
                    now_sec = total_audio_bytes / PCM_BYTES_PER_SEC
                    draft = engine.on_tick(now_sec)
                    if draft is not None:
                        await _push(save_bullet(training_id, draft))
            except asyncio.CancelledError:
                pass

        proc_task = asyncio.create_task(_process())
        timer_task = asyncio.create_task(_cold_start_timer())
        try:
            while True:
                msg = await websocket.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                data = msg.get("bytes")
                if data is not None:
                    total_audio_bytes += len(data)
                    await session.send_audio(data)
                    continue
                text = msg.get("text")
                if text:
                    try:
                        ctrl = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if ctrl.get("type") == "end":
                        break
        finally:
            stop.set()
            timer_task.cancel()
            try:
                await session.send_end()
            except Exception:  # noqa: BLE001
                pass
            try:
                await asyncio.wait_for(proc_task, timeout=3.0)
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                proc_task.cancel()
            try:
                await session.close()
            except Exception:  # noqa: BLE001
                pass
    finally:
        db.close()
    try:
        await websocket.close()
    except Exception:  # noqa: BLE001
        pass

"""端到端真实冒烟：创建练习 → WebSocket 实时转写+动态弹幕 → 结束 → 反馈。

用一段真实录音（PCM）模拟浏览器麦克风流，走真实腾讯云 ASR + DeepSeek 反馈。
"""
import asyncio
import json
import os
import sys
import tempfile
import time

import httpx
from websockets.asyncio.client import connect as ws_connect

from app.services.audio import extract_audio_to_wav

BASE = "http://127.0.0.1:8001"


def extract_pcm(src: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = tmp.name
    try:
        extract_audio_to_wav(src, wav)
        data = open(wav, "rb").read()
    finally:
        os.unlink(wav)
    idx = data.find(b"data")
    return data[idx + 8:]


async def main(src: str, upload_file: str):
    # 1. 创建练习
    r = httpx.post(f"{BASE}/api/v1/trainings", json={"live_type": "带货", "goal": "练习弹幕应答"})
    r.raise_for_status()
    tid = r.json()["training"]["id"]
    print(f"[1] 创建练习 tid={tid}")

    pcm = extract_pcm(src)
    print(f"[2] PCM {len(pcm)} 字节 ≈ {len(pcm)/32000:.1f} 秒，连 WS")

    bullets, finals = [], []
    async with ws_connect(f"ws://127.0.0.1:8001/api/v1/trainings/{tid}/asr/ws") as ws:
        async def reader():
            async for msg in ws:
                d = json.loads(msg)
                if d.get("type") == "transcript" and d.get("kind") == "final" and d.get("text"):
                    finals.append(d["text"])
                if d.get("type") == "bullet":
                    bullets.append((d.get("trigger_type"), d.get("text")))
        rt = asyncio.create_task(reader())
        chunk = 3200
        for i in range(0, len(pcm), chunk):
            await ws.send(pcm[i:i+chunk])
            await asyncio.sleep(0.05)
        await ws.send(json.dumps({"type": "end"}))
        await asyncio.wait_for(rt, timeout=20)

    print(f"[3] 稳定转写 {len(finals)} 句：")
    for f in finals:
        print("    -", f)
    print(f"[4] 动态弹幕 {len(bullets)} 条：")
    for tt, tx in bullets:
        print(f"    [{tt}] {tx}")

    # 3. finish（上传录像，不传 bullets）
    data = open(upload_file, "rb").read()
    r = httpx.post(
        f"{BASE}/api/v1/trainings/{tid}/finish",
        files={"file": ("rec.webm", data, "video/webm")},
        data={"duration_sec": "20"},
    )
    r.raise_for_status()
    print(f"[5] finish status={r.json()['training']['status']}")

    # 4. 轮询反馈
    for _ in range(40):
        r = httpx.get(f"{BASE}/api/v1/trainings/{tid}/feedback")
        d = r.json()
        if d["status"] in ("feedback_ready", "failed"):
            print(f"[6] 反馈状态={d['status']}")
            if d.get("feedback"):
                for it in d["feedback"]["issues"]:
                    print(f"    · {it['dimension']} [{it['start_sec']}-{it['end_sec']}] {it['problem']}")
                    if it.get("evidence"):
                        print(f"      证据：{it['evidence']}")
            return
        time.sleep(2)
    print("[6] 反馈超时")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/recordings/10_71aa1743.webm"
    upload = sys.argv[2] if len(sys.argv) > 2 else "data/recordings/10_71aa1743.webm"
    asyncio.run(main(src, upload))

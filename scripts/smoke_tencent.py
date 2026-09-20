"""腾讯云实时语音识别真实冒烟脚本（临时，用真实 Key 跑一段真实录音）。"""
import asyncio
import os
import sys
import tempfile

from app.services.audio import extract_audio_to_wav
from app.services.asr_tencent import TencentRealtimeASR


def extract_pcm(src: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    try:
        extract_audio_to_wav(src, wav_path)
        data = open(wav_path, "rb").read()
    finally:
        os.unlink(wav_path)
    idx = data.find(b"data")
    if idx < 0:
        raise RuntimeError("WAV 无 data chunk")
    return data[idx + 8:]


async def main(src: str):
    pcm = extract_pcm(src)
    print(f"PCM: {len(pcm)} 字节 ≈ {len(pcm) / 32000:.1f} 秒")

    provider = TencentRealtimeASR()
    session = await provider.open_session()
    print("✅ 会话已建立（签名/鉴权通过）")

    events = []

    async def reader():
        while True:
            ev = await session.receive_event()
            if ev is None:
                break
            events.append(ev)
            print(f"  [{ev.kind}] ({ev.start_sec:.1f}-{ev.end_sec:.1f}) {ev.text}")

    rt = asyncio.create_task(reader())
    chunk = 3200  # 100ms
    for i in range(0, len(pcm), chunk):
        await session.send_audio(pcm[i : i + chunk])
        await asyncio.sleep(0.05)  # 2x 实时送
    await session.send_end()
    try:
        await asyncio.wait_for(rt, timeout=15)
    except asyncio.TimeoutError:
        print("⚠️ 等待结果超时")
    await session.close()

    finals = [e for e in events if e.kind == "final"]
    print(f"完成。事件 {len(events)} 条，稳定片段 {len(finals)} 条。")
    if finals:
        print("稳定转写全文：", "".join(e.text for e in finals))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "data/recordings/10_71aa1743.webm"))

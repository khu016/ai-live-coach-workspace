"""腾讯云实时语音识别适配器 + 统一 ASR 抽象层的单元测试（全 mock，不连外网）。"""

import asyncio
import base64
import hashlib
import hmac
import json
import urllib.parse

import pytest

from app.core.config import settings
from app.services.asr_base import ASREvent, get_realtime_asr
from app.services.asr_tencent import (
    TencentASRSession,
    TencentRealtimeASR,
    build_sign_string,
    build_signed_url,
    hmac_sha1_base64,
)
from app.services.asr import MockRealtimeASR


def _run(coro):
    return asyncio.run(coro)


async def _receive_with_timeout(session, timeout=0.05):
    return await asyncio.wait_for(session.receive_event(), timeout)


class FakeWS:
    def __init__(self, messages):
        self._messages = list(messages)
        self.sent = []

    async def recv(self):
        if self._messages:
            return self._messages.pop(0)
        raise RuntimeError("no more messages")

    async def send(self, data):
        self.sent.append(data)

    async def close(self):
        pass


# ---- 签名 ----


def test_build_sign_string_sorted_and_appid_in_path():
    params = {
        "appid": "1234567890",
        "secretid": "AKIDxxxx",
        "timestamp": "1700000000",
        "nonce": "1700000000",
        "expired": "1700086400",
        "engine_model_type": "16k_zh",
        "voice_id": "voice123",
        "voice_format": "1",
        "needvad": "1",
    }
    assert build_sign_string(params) == (
        "asr.cloud.tencent.com/asr/v2/1234567890?"
        "engine_model_type=16k_zh&expired=1700086400&needvad=1"
        "&nonce=1700000000&secretid=AKIDxxxx&timestamp=1700000000"
        "&voice_format=1&voice_id=voice123"
    )


def test_hmac_sha1_base64_matches_stdlib():
    key, msg = "sk-secret-123", "hello"
    expected = base64.b64encode(
        hmac.new(key.encode(), msg.encode(), hashlib.sha1).digest()
    ).decode()
    assert hmac_sha1_base64(key, msg) == expected


def test_build_signed_url_contains_encoded_signature():
    params = {
        "appid": "1234567890",
        "secretid": "AKIDxxxx",
        "timestamp": "1700000000",
        "nonce": "1700000000",
        "expired": "1700086400",
        "engine_model_type": "16k_zh",
        "voice_id": "voice123",
        "voice_format": "1",
        "needvad": "1",
    }
    url = build_signed_url(params, "sk-secret-123")
    assert url.startswith("wss://asr.cloud.tencent.com/asr/v2/1234567890?")
    assert "engine_model_type=16k_zh" in url
    sig = hmac_sha1_base64("sk-secret-123", build_sign_string(params))
    assert urllib.parse.quote(sig) in url


# ---- 会话解析（句子模式） ----


def _sentences_frame(sentences, final=0, code=0, message="success"):
    return json.dumps(
        {
            "code": code,
            "message": message,
            "final": final,
            "sentences": {"sentence_list": sentences},
        }
    )


def test_session_parses_sentence_mode():
    ws = FakeWS(
        [
            _sentences_frame(
                [
                    {"sentence_id": 0, "sentence_type": 0, "sentence": "大家好"},
                    {
                        "sentence_id": 1,
                        "sentence_type": 1,
                        "sentence": "大家好，欢迎来到直播间。",
                        "start_time": 0,
                        "end_time": 2500,
                    },
                ]
            ),
            json.dumps({"code": 0, "final": 1}),
        ]
    )
    session = TencentASRSession(ws, voice_id="v")
    ev1 = _run(session.receive_event())
    assert ev1.kind == "partial" and ev1.text == "大家好"
    ev2 = _run(session.receive_event())
    assert ev2.kind == "final" and ev2.text == "大家好，欢迎来到直播间。"
    assert ev2.start_sec == 0.0 and ev2.end_sec == 2.5
    assert _run(session.receive_event()) is None  # final=1 → 流结束


def test_session_binary_message_ignored():
    ws = FakeWS([b"\x00\x01", json.dumps({"code": 0, "final": 1})])
    session = TencentASRSession(ws, voice_id="v")
    assert _run(session.receive_event()) is None


def test_session_error_raises():
    ws = FakeWS([json.dumps({"code": 4002, "message": "签名错误"})])
    session = TencentASRSession(ws, voice_id="v")
    with pytest.raises(RuntimeError, match="腾讯云语音识别失败"):
        _run(session.receive_event())


def test_session_send_audio_and_end():
    ws = FakeWS([])
    session = TencentASRSession(ws, voice_id="v")
    _run(session.send_audio(b"\x00\x01"))
    _run(session.send_end())
    assert ws.sent[0] == b"\x00\x01"
    assert json.loads(ws.sent[1]) == {"type": "end"}


def test_require_credentials():
    provider = TencentRealtimeASR()
    provider.appid = ""
    with pytest.raises(RuntimeError, match="未配置"):
        provider._require_credentials()


# ---- mock 实时会话 ----


def test_mock_realtime_session_gated():
    async def scenario():
        events = [
            ASREvent(kind="partial", text="临时", start_sec=0.0, end_sec=1.0),
            ASREvent(kind="final", text="稳定一句话。", start_sec=0.0, end_sec=2.0),
        ]
        provider = MockRealtimeASR(events=events)
        session = await provider.open_session()

        with pytest.raises(asyncio.TimeoutError):
            await _receive_with_timeout(session)
        await session.send_audio(b"\x00")
        assert (await session.receive_event()).kind == "partial"
        await session.send_audio(b"\x01")
        assert (await session.receive_event()).kind == "final"
        with pytest.raises(asyncio.TimeoutError):
            await _receive_with_timeout(session)
        await session.send_end()
        assert await session.receive_event() is None

    asyncio.run(scenario())


# ---- 工厂 ----


def test_get_realtime_asr_mock(monkeypatch):
    monkeypatch.setattr(settings, "asr_provider", "mock")
    assert get_realtime_asr().provider == "mock"


def test_get_realtime_asr_tencent(monkeypatch):
    monkeypatch.setattr(settings, "asr_provider", "tencent_realtime")
    assert get_realtime_asr().provider == "tencent_realtime"


def test_get_realtime_asr_unknown(monkeypatch):
    monkeypatch.setattr(settings, "asr_provider", "nope")
    with pytest.raises(RuntimeError, match="不支持的 ASR_PROVIDER"):
        get_realtime_asr()

"""腾讯云实时语音识别（WebSocket v2）适配器。

协议（对照官方 Python SDK ``tencentcloud-speech-sdk-python`` 的
``asr/realtime_recognizer_v2.py``）：

- 端点：``wss://asr.cloud.tencent.com/asr/v2/{APPID}?{排序参数}&signature=...``
- 签名：``signStr = "asr.cloud.tencent.com/asr/v2/{appid}?{按 key 升序的 k=v&...}"``，
  ``signature = Base64(HmacSHA1(SecretKey, signStr))``，拼 URL 前对 signature 做 URL 编码。
- 请求参数里 ``appid`` 在路径中，其余参数按 key 升序参与签名。
- 结果（``result_mod=1`` 句子模式）：每条消息为 ``sentences.sentence_list``，
  ``sentence_type`` 0=稳定句、1=临时句；``final=1`` 表示识别结束。
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import uuid
from typing import List, Optional, Tuple

from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from ..core.config import settings
from .asr_base import ASREvent, ASRSession

TENCENT_ASR_HOST = "asr.cloud.tencent.com"
TENCENT_ASR_PATH = "/asr/v2/"

SLICE_PARTIAL = 1
SLICE_FINAL = 2


def hmac_sha1_base64(key: str, msg: str) -> str:
    digest = hmac.new(
        key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha1
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def build_sign_string(params: dict) -> str:
    """构建待签名字符串（不含 wss:// 前缀）。params 需包含 appid。"""
    sorted_params = sorted(params.items(), key=lambda d: d[0])
    signstr = f"{TENCENT_ASR_HOST}{TENCENT_ASR_PATH}"
    for k, v in sorted_params:
        if k == "appid":
            signstr += str(v)
            break
    signstr += "?"
    for k, v in sorted_params:
        if k == "appid":
            continue
        signstr += f"{k}={v}&"
    return signstr[:-1]


def build_signed_url(params: dict, secret_key: str) -> str:
    """构建带签名的 wss URL（签名覆盖排序后的全部参数，签名值 URL 编码）。"""
    sorted_params = sorted(params.items(), key=lambda d: d[0])
    signature = hmac_sha1_base64(secret_key, build_sign_string(params))
    url = f"wss://{TENCENT_ASR_HOST}{TENCENT_ASR_PATH}"
    for k, v in sorted_params:
        if k == "appid":
            url += str(v)
            break
    url += "?"
    for k, v in sorted_params:
        if k == "appid":
            continue
        url += f"{k}={v}&"
    url = url[:-1]
    url += "&signature=" + urllib.parse.quote(signature)
    return url


class TencentASRSession(ASRSession):
    def __init__(self, ws, voice_id: str) -> None:
        self.ws = ws
        self.voice_id = voice_id
        self._buffer: List[ASREvent] = []
        self._done = False
        self._closed = False

    async def send_audio(self, pcm: bytes) -> None:
        if self._closed or not pcm:
            return
        await self.ws.send(pcm)

    async def send_end(self) -> None:
        if self._closed:
            return
        await self.ws.send(json.dumps({"type": "end"}))

    async def receive_event(self) -> Optional[ASREvent]:
        while True:
            if self._buffer:
                return self._buffer.pop(0)
            if self._done or self._closed:
                return None
            try:
                msg = await self.ws.recv()
            except ConnectionClosed:
                self._closed = True
                return None
            except Exception:
                self._closed = True
                raise
            if isinstance(msg, bytes):
                continue
            events, done = self._parse(json.loads(msg))
            self._buffer.extend(events)
            if done:
                self._done = True

    def _parse(self, data: dict) -> Tuple[List[ASREvent], bool]:
        code = data.get("code", 0)
        if code != 0:
            raise RuntimeError(
                f"腾讯云语音识别失败（{code}）：{data.get('message')}"
            )
        if data.get("final", 0) == 1:
            return [], True
        events: List[ASREvent] = []
        sentence_list = (data.get("sentences") or {}).get("sentence_list") or []
        for s in sentence_list:
            text = (s.get("sentence") or "").strip()
            if not text:
                continue
            # sentence_type：0=中间（临时），1=最终（稳定）
            kind = "final" if s.get("sentence_type", 0) == 1 else "partial"
            start_ms = s.get("start_time")
            end_ms = s.get("end_time")
            events.append(
                ASREvent(
                    kind=kind,
                    text=text,
                    start_sec=start_ms / 1000.0 if start_ms is not None else None,
                    end_sec=end_ms / 1000.0 if end_ms is not None else None,
                    seq=s.get("sentence_id"),
                )
            )
        # 兼容流式模式（result.slice_type），以防某些参数组合返回旧格式
        if not events and isinstance(data.get("result"), dict):
            result = data["result"]
            slice_type = result.get("slice_type")
            if slice_type in (SLICE_PARTIAL, SLICE_FINAL):
                kind = "partial" if slice_type == SLICE_PARTIAL else "final"
                events.append(
                    ASREvent(
                        kind=kind,
                        text=result.get("voice_text_str") or "",
                        start_sec=(result.get("start_time") or 0) / 1000.0,
                        end_sec=(result.get("end_time") or 0) / 1000.0,
                        seq=result.get("index"),
                    )
                )
        return events, False

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self.ws.close()
        except Exception:  # noqa: BLE001
            pass


class TencentRealtimeASR:
    provider = "tencent_realtime"

    def __init__(self) -> None:
        self.appid = settings.tencent_asr_appid
        self.secret_id = settings.tencent_asr_secret_id
        self.secret_key = settings.tencent_asr_secret_key
        self.engine_model = settings.tencent_asr_engine_model
        self.voice_format = settings.tencent_asr_voice_format

    def _require_credentials(self) -> None:
        if not (self.appid and self.secret_id and self.secret_key):
            raise RuntimeError(
                "腾讯云语音识别未配置：请在 .env 填写 TENCENT_ASR_APPID、"
                "TENCENT_ASR_SECRET_ID、TENCENT_ASR_SECRET_KEY 后重启服务"
            )

    def _query_params(self, voice_id: str) -> dict:
        ts = int(time.time())
        return {
            "appid": self.appid,
            "secretid": self.secret_id,
            "timestamp": str(ts),
            "nonce": str(ts),
            "expired": str(ts + 86400),
            "engine_model_type": self.engine_model,
            "voice_id": voice_id,
            "voice_format": str(self.voice_format),
            "needvad": "1",
            "convert_num_mode": "1",
        }

    async def open_session(self, **params) -> TencentASRSession:
        self._require_credentials()
        voice_id = str(uuid.uuid4()).replace("-", "")
        url = build_signed_url(self._query_params(voice_id), self.secret_key)
        ws = await ws_connect(url)
        return TencentASRSession(ws, voice_id)

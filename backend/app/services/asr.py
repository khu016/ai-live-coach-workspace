import base64
import hashlib
import hmac
import json
import tempfile
import time
from pathlib import Path

import httpx

from ..core.config import settings
from .audio import extract_audio_to_wav

# 讯飞语音转写（录音文件转写，LFASR）WebAPI
XFYUN_BASE_URL = "https://raasr.xfyun.cn/api"
XFYUN_PREPARE = f"{XFYUN_BASE_URL}/prepare"
XFYUN_UPLOAD = f"{XFYUN_BASE_URL}/upload"
XFYUN_MERGE = f"{XFYUN_BASE_URL}/merge"
XFYUN_PROGRESS = f"{XFYUN_BASE_URL}/getProgress"
XFYUN_RESULT = f"{XFYUN_BASE_URL}/getResult"

# 任务状态：9 = 转写结果上传完成（才可获取结果）
TASK_FINISHED = 9


class MockASR:
    """开发/测试用的确定性转写，明确标注为 mock，不得冒充真实转写。"""

    provider = "mock"

    def transcribe(self, file_path, duration=None):
        segments = [
            {"start": 0.0, "end": 6.0, "text": "大家好，欢迎来到我的直播间。"},
            {"start": 6.0, "end": 14.0, "text": "今天给大家介绍一款很实用的产品。"},
            {"start": 14.0, "end": 22.0, "text": "价格非常实惠，有需要的朋友抓紧下单。"},
        ]
        full_text = "".join(s["text"] for s in segments)
        return {"segments": segments, "full_text": full_text, "provider": "mock"}


class XfyunASR:
    """讯飞开放平台·语音转写（录音文件转写，LFASR WebAPI）。

    流程：录像(webm) → 抽取音频为 16k 单声道 wav → prepare → upload → merge
    → 轮询 getProgress 至 status=9 → getResult → 返回带时间戳的分段文本。
    凭证来自 ``.env`` 的 ``ASR_APP_ID`` 与 ``ASR_SECRET_KEY``。
    """

    provider = "xfyun"

    def __init__(self) -> None:
        self.app_id = settings.asr_app_id
        self.secret_key = settings.asr_secret_key

    def _signa(self, ts: str) -> str:
        # signa = base64(HmacSHA1(MD5(appid + ts), secret_key))
        md5_hex = hashlib.md5((self.app_id + ts).encode("utf-8")).hexdigest()
        digest = hmac.new(
            self.secret_key.encode("utf-8"),
            md5_hex.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _common_params(self, **extra) -> dict:
        ts = str(int(time.time()))
        params = {
            "app_id": self.app_id,
            "signa": self._signa(ts),
            "ts": ts,
        }
        params.update(extra)
        return params

    def _post(self, url: str, **kwargs):
        resp = httpx.post(url, timeout=60.0, **kwargs)
        resp.raise_for_status()
        body = resp.json()
        if body.get("ok") != 0:
            raise RuntimeError(
                f"讯飞语音转写失败（{body.get('err_no')}）：{body.get('failed')}"
            )
        return body

    def _prepare(self, wav_path: Path) -> str:
        size = wav_path.stat().st_size
        body = self._post(
            XFYUN_PREPARE,
            data=self._common_params(
                file_len=str(size),
                file_name=wav_path.name,
                slice_num="1",
                lfasr_type="0",
            ),
        )
        task_id = body.get("data")
        if not task_id:
            raise RuntimeError(f"讯飞预处理未返回任务ID：{body}")
        return task_id

    def _upload(self, wav_path: Path, task_id: str) -> None:
        content = wav_path.read_bytes()
        self._post(
            XFYUN_UPLOAD,
            data=self._common_params(task_id=task_id, slice_id="aaaaaaaaaa"),
            files={"content": (wav_path.name, content, "application/octet-stream")},
        )

    def _merge(self, wav_path: Path, task_id: str) -> None:
        self._post(
            XFYUN_MERGE,
            data=self._common_params(task_id=task_id, file_name=wav_path.name),
        )

    def _wait_finished(self, task_id: str, timeout: float = 600.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            body = self._post(
                XFYUN_PROGRESS, data=self._common_params(task_id=task_id)
            )
            data = body.get("data")
            status = None
            if isinstance(data, str):
                try:
                    status = json.loads(data).get("status")
                except json.JSONDecodeError:
                    status = None
            elif isinstance(data, dict):
                status = data.get("status")
            if status == TASK_FINISHED:
                return
            time.sleep(5)
        raise RuntimeError("讯飞语音转写超时")

    def _get_result(self, task_id: str) -> str:
        body = self._post(
            XFYUN_RESULT, data=self._common_params(task_id=task_id)
        )
        return body.get("data") or ""

    def _parse_result(self, data: str):
        # data 形如：[{"bg":"0","ed":"4950","onebest":"...","speaker":"0"}]
        try:
            items = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            items = []
        if not isinstance(items, list):
            items = []
        segments = []
        for it in items:
            text = str(it.get("onebest") or "").strip()
            if not text:
                continue
            try:
                start = float(it.get("bg", 0)) / 1000.0
                end = float(it.get("ed", 0)) / 1000.0
            except (TypeError, ValueError):
                start, end = 0.0, 0.0
            segments.append({"start": start, "end": end, "text": text})
        full_text = "".join(s["text"] for s in segments)
        return segments, full_text

    def transcribe(self, file_path, duration=None):
        if not (self.app_id and self.secret_key):
            raise RuntimeError(
                "讯飞语音转写未配置：请在 .env 填写 ASR_APP_ID 和 ASR_SECRET_KEY 后重启服务"
            )
        src = Path(file_path)
        if not src.exists():
            raise RuntimeError(f"录像文件不存在：{src}")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)
        try:
            extract_audio_to_wav(str(src), str(wav_path))
            task_id = self._prepare(wav_path)
            self._upload(wav_path, task_id)
            self._merge(wav_path, task_id)
            self._wait_finished(task_id)
            segments, full_text = self._parse_result(self._get_result(task_id))
            return {"segments": segments, "full_text": full_text, "provider": "xfyun"}
        finally:
            wav_path.unlink(missing_ok=True)


def get_asr():
    if settings.asr_provider == "mock":
        return MockASR()
    if settings.asr_provider == "xfyun":
        return XfyunASR()
    raise RuntimeError(f"不支持的 ASR_PROVIDER: {settings.asr_provider!r}")

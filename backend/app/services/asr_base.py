"""统一 ASR 抽象层。

业务层（实时会话编排、动态弹幕触发、练后反馈）只依赖这里的接口，
不 import 具体供应商，方便以后更换 ASR 供应商而不改业务。

- ``ASREvent``：实时转写事件，``partial``（临时，会变化）或 ``final``（稳定）。
- ``ASRTranscript``：离线转写结果（segments + full_text），供兜底复用。
- ``ASRSession``：一次实时识别会话（喂音频 → 收事件）。
- ``RealtimeASRProvider``：实时供应商工厂接口。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Protocol

from ..core.config import settings


@dataclass
class ASREvent:
    kind: str  # "partial" | "final"
    text: str
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None
    seq: Optional[int] = None


@dataclass
class ASRTranscript:
    segments: List[dict] = field(default_factory=list)
    full_text: str = ""
    provider: str = ""


class ASRSession(Protocol):
    """一次实时识别会话。实现方负责网络连接与协议细节。"""

    async def send_audio(self, pcm: bytes) -> None: ...

    async def send_end(self) -> None: ...

    async def receive_event(self) -> Optional[ASREvent]:
        """返回下一个事件；流结束时返回 None。"""
        ...

    async def close(self) -> None: ...


class RealtimeASRProvider(Protocol):
    provider: str

    async def open_session(self, **params) -> ASRSession: ...


def get_realtime_asr() -> RealtimeASRProvider:
    """按 ``ASR_PROVIDER`` 返回实时 ASR 供应商。

    - ``tencent_realtime``：腾讯云实时语音识别（WebSocket）。
    - ``mock``：测试/开发用确定性实时转写。
    """
    if settings.asr_provider == "tencent_realtime":
        from .asr_tencent import TencentRealtimeASR

        return TencentRealtimeASR()
    if settings.asr_provider == "mock":
        from .asr import MockRealtimeASR

        return MockRealtimeASR()
    raise RuntimeError(f"不支持的 ASR_PROVIDER: {settings.asr_provider!r}")

from ..core.config import settings


class MockASR:
    """开发/测试用的确定性转写，明确标注为 mock，不得冒充真实转写。"""

    provider = "mock"

    def transcribe(self, file_path):
        segments = [
            {"start": 0.0, "end": 6.0, "text": "大家好，欢迎来到我的直播间。"},
            {"start": 6.0, "end": 14.0, "text": "今天给大家介绍一款很实用的产品。"},
            {"start": 14.0, "end": 22.0, "text": "价格非常实惠，有需要的朋友抓紧下单。"},
        ]
        full_text = "".join(s["text"] for s in segments)
        return {"segments": segments, "full_text": full_text, "provider": "mock"}


class XfyunASR:
    """讯飞开放平台语音转写（真实接入待 Key 与 API 集成，当前未接入）。"""

    provider = "xfyun"

    def transcribe(self, file_path):
        raise RuntimeError("讯飞 ASR 尚未接入（待提供 Key 并完成 API 集成）")


def get_asr():
    if settings.asr_provider == "mock":
        return MockASR()
    return XfyunASR()

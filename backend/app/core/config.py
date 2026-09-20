import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    def __init__(self) -> None:
        self.model_provider = os.getenv("MODEL_PROVIDER", "deepseek")
        self.model_name = os.getenv("MODEL_NAME", "deepseek-chat")
        self.model_api_key = os.getenv("MODEL_API_KEY", "")
        self.model_base_url = os.getenv(
            "MODEL_BASE_URL", "https://api.deepseek.com/v1"
        ).rstrip("/")
        # 实时 ASR（第一版主 ASR，驱动动态弹幕）：tencent_realtime | mock
        self.asr_provider = os.getenv("ASR_PROVIDER", "mock")
        # 腾讯云实时语音识别（WebSocket）
        self.tencent_asr_appid = os.getenv("TENCENT_ASR_APPID", "")
        self.tencent_asr_secret_id = os.getenv("TENCENT_ASR_SECRET_ID", "")
        self.tencent_asr_secret_key = os.getenv("TENCENT_ASR_SECRET_KEY", "")
        self.tencent_asr_engine_model = os.getenv(
            "TENCENT_ASR_ENGINE_MODEL", "16k_zh"
        )
        self.tencent_asr_voice_format = int(
            os.getenv("TENCENT_ASR_VOICE_FORMAT", "1")
        )
        # 讯飞录音文件转写（暂不启用，字段保留备以后兑底）
        self.asr_app_id = os.getenv("ASR_APP_ID", "")
        self.asr_secret_key = os.getenv("ASR_SECRET_KEY", "")
        # 动态弹幕参数
        self.bullet_min_interval_sec = float(
            os.getenv("BULLET_MIN_INTERVAL_SEC", "5")
        )
        self.bullet_cold_start_sec = float(os.getenv("BULLET_COLD_START_SEC", "15"))
        self.bullet_generate_timeout_sec = float(
            os.getenv("BULLET_GENERATE_TIMEOUT_SEC", "8")
        )
        self.data_dir = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
        self.recording_max_mb = int(os.getenv("RECORDING_MAX_MB", "1024"))
        self.practice_max_sec = int(os.getenv("PRACTICE_MAX_SEC", "1200"))

    def ensure_dirs(self) -> None:
        (self.data_dir / "recordings").mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()

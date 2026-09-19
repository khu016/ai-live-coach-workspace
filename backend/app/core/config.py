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
        self.asr_provider = os.getenv("ASR_PROVIDER", "mock")
        self.asr_app_id = os.getenv("ASR_APP_ID", "")
        self.asr_secret_key = os.getenv("ASR_SECRET_KEY", "")
        self.data_dir = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
        self.recording_max_mb = int(os.getenv("RECORDING_MAX_MB", "1024"))
        self.practice_max_sec = int(os.getenv("PRACTICE_MAX_SEC", "1200"))

    def ensure_dirs(self) -> None:
        (self.data_dir / "recordings").mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()

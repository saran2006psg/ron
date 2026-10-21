from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("DATABASE_PATH", "./data/broll.db"))
    artifact_dir: Path = Path(os.getenv("ARTIFACT_DIR", "./data/artifacts"))
    work_dir: Path = Path(os.getenv("WORK_DIR", "./data/work"))
    ffmpeg_bin: str = os.getenv("FFMPEG_BIN", "ffmpeg")
    footage_provider: str = os.getenv("FOOTAGE_PROVIDER", "mock")
    pexels_api_key: str | None = os.getenv("PEXELS_API_KEY") or None
    tts_provider: str = os.getenv("TTS_PROVIDER", "mock")
    max_audio_seconds: int = int(os.getenv("MAX_AUDIO_SECONDS", "600"))
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")


settings = Settings()


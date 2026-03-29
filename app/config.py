from __future__ import annotations

import os
from pathlib import Path


class Settings:
    app_name = "OpenClaw AI Support Core"
    database_url = os.getenv("AI_SERVER_DATABASE_URL", "sqlite:///./var/ai_server.db")
    platforms_dir = Path(os.getenv("AI_SERVER_PLATFORMS_DIR", "platforms"))
    default_platform = os.getenv("AI_SERVER_DEFAULT_PLATFORM", "okx_help")
    temp_dir = Path(os.getenv("AI_SERVER_TEMP_DIR", "tmp/runtime"))
    request_timeout_s = float(os.getenv("AI_SERVER_REQUEST_TIMEOUT_S", "20"))


settings = Settings()

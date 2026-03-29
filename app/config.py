from __future__ import annotations

import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_env_file(Path(".env.local"))


class Settings:
    app_name = "OpenClaw AI Support Core"
    database_url = os.getenv("AI_SERVER_DATABASE_URL", "sqlite:///./var/ai_server.db")
    platforms_dir = Path(os.getenv("AI_SERVER_PLATFORMS_DIR", "platforms"))
    default_platform = os.getenv("AI_SERVER_DEFAULT_PLATFORM", "okx_help")
    temp_dir = Path(os.getenv("AI_SERVER_TEMP_DIR", "tmp/runtime"))
    request_timeout_s = float(os.getenv("AI_SERVER_REQUEST_TIMEOUT_S", "20"))


settings = Settings()

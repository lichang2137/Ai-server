#!/usr/bin/env bash
set -euo pipefail

export AI_SERVER_DATABASE_URL="${AI_SERVER_DATABASE_URL:-sqlite:///./var/ai_server.db}"
export AI_SERVER_DEFAULT_PLATFORM="${AI_SERVER_DEFAULT_PLATFORM:-okx_help}"

python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

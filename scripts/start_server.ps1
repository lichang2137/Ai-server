$ErrorActionPreference = "Stop"

if (-not $env:AI_SERVER_DATABASE_URL) {
  $env:AI_SERVER_DATABASE_URL = "sqlite:///./var/ai_server.db"
}

if (-not $env:AI_SERVER_DEFAULT_PLATFORM) {
  $env:AI_SERVER_DEFAULT_PLATFORM = "okx_help"
}

python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

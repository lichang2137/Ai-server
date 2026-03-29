# OpenClaw Installation Guide

## Goal

Hand this repository to OpenClaw so it can install one HTTP service and start handling:

- conversational knowledge QA
- status diagnosis
- KYB document review
- structured human handoff

## What OpenClaw needs to do

1. Install Python dependencies.
2. Set the runtime environment variables.
3. Start the HTTP service.
4. Configure OpenClaw to forward channel events and attachment metadata to `POST /v1/support/message`.

## Environment variables

- `AI_SERVER_DATABASE_URL`
  Default example: `sqlite:///./var/ai_server.db`
- `AI_SERVER_DEFAULT_PLATFORM`
  Default example: `okx_help`
- `AI_SERVER_PLATFORMS_DIR`
  Default example: `platforms`
- `AI_SERVER_REQUEST_TIMEOUT_S`
  Default example: `15`

## Start commands

PowerShell:

```powershell
./scripts/start_server.ps1
```

POSIX shell:

```bash
./scripts/start_server.sh
```

Direct:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## OpenClaw forwarding contract

OpenClaw should forward:

- `channel`
- `channel_user_id`
- `session_id`
- `platform_user_id`
- `message_id`
- `text`
- `timestamp`
- `context.locale`
- `context.attachments[*]`

Each attachment should contain:

- `attachment_id`
- `name`
- `mime_type`
- `url`
- `size_bytes`

## Platform switch procedure

To switch platforms:

1. Add or replace `platforms/<platform_id>/`.
2. Add a live adapter in `platforms/<platform_id>/adapters/` if available.
3. Set `AI_SERVER_DEFAULT_PLATFORM=<platform_id>`.
4. Restart the service.
5. Run `pytest` before exposing the platform to OpenClaw.

## Attachment handling notes

- PDF, DOCX, XLSX, and image files are supported.
- If OCR infrastructure is unavailable, image review can fall back to filename hints and local `.ocr.txt` sidecars for deterministic validation.
- Recommendations are for human review only and do not write final approvals.

## OKX default package

The repository now defaults to `platforms/okx_help`.

Temporary live status can be backed by Feishu Bitable:

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `OKX_FEISHU_BITABLE_APP_TOKEN`
- `OKX_FEISHU_VERIFICATION_TABLE_ID`
- `OKX_FEISHU_DEPOSIT_TABLE_ID`
- `OKX_FEISHU_WITHDRAW_TABLE_ID`
- `OKX_FEISHU_NETWORK_TABLE_ID`
- optional `OKX_FEISHU_TICKET_TABLE_ID`

See [docs/OKX_FEISHU_BITABLE_SETUP.md](/C:/Users/26265/Documents/New%20project/Ai-server/docs/OKX_FEISHU_BITABLE_SETUP.md).

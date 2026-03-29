# OKX Feishu Bitable Setup

## Purpose

Use Feishu Bitable as a temporary live adapter source for the `okx_help` platform package.

The assistant will keep public OKX help-center articles as the knowledge layer, while reading current operational state from Feishu Bitable tables.

## Environment variables

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `OKX_FEISHU_BITABLE_APP_TOKEN`
- `OKX_FEISHU_VERIFICATION_TABLE_ID`
- `OKX_FEISHU_DEPOSIT_TABLE_ID`
- `OKX_FEISHU_WITHDRAW_TABLE_ID`
- `OKX_FEISHU_NETWORK_TABLE_ID`
- optional `OKX_FEISHU_TICKET_TABLE_ID`

## Required tables

The table schema is defined in [feishu_bitable_tables.yaml](/C:/Users/26265/Documents/New%20project/Ai-server/platforms/okx_help/schemas/feishu_bitable_tables.yaml).

Recommended tables:

1. `verification_status`
2. `deposit_status`
3. `withdraw_status`
4. `network_status`
5. optional `support_tickets`

## Field design

### `verification_status`

Use this table for KYC or KYB progress.

Required fields:

- `user_id`
- `verification_scope`
- `current_status`
- `updated_at`

Recommended fields:

- `missing_items`
- `rejection_reason`
- `next_action`
- `eta`
- `case_id`
- `is_active`

Recommended `current_status` values:

- `pending_review`
- `material_missing`
- `in_review`
- `rejected`
- `approved`
- `expired`
- `manual_review`

### `deposit_status`

Required fields:

- `user_id`
- `asset`
- `status`
- `updated_at`

Recommended fields:

- `network`
- `txid`
- `confirmations`
- `next_action`
- `is_active`

### `withdraw_status`

Required fields:

- `user_id`
- `asset`
- `status`
- `updated_at`

Recommended fields:

- `network`
- `txid`
- `review_reason`
- `next_action`
- `is_active`

### `network_status`

Required fields:

- `asset`
- `network`
- `deposit_enabled`
- `withdraw_enabled`
- `updated_at`

Recommended fields:

- `announcement_url`
- `eta`
- `current_status_note`
- `is_active`

### `support_tickets`

Optional table for later use.

Recommended fields:

- `user_id`
- `ticket_id`
- `status`
- `latest_reply`
- `next_action`
- `updated_at`
- `is_active`

## Writing rules for operations

- Keep one active latest row per live issue whenever possible.
- Use `is_active=false` to retire stale rows instead of deleting them immediately.
- Use plain text or single-select values for statuses.
- Keep `updated_at` accurate because the adapter sorts by recency.
- Keep `next_action` user-readable. The assistant may surface it directly.

## Seed example

See [feishu_bitable_seed.yaml](/C:/Users/26265/Documents/New%20project/Ai-server/platforms/okx_help/examples/feishu_bitable_seed.yaml).

## Bootstrap script

Use [create_okx_feishu_bitable.py](/C:/Users/26265/Documents/New%20project/Ai-server/scripts/create_okx_feishu_bitable.py) to create the Bitable app, required tables, and seed rows in one run.

Example:

```bash
python scripts/create_okx_feishu_bitable.py --include-support-tickets
```

The script writes a local runtime artifact to `var/okx_feishu_bitable_runtime.json` and prints the `OKX_FEISHU_BITABLE_*` env values you should configure locally.

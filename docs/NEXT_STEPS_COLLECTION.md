# Next Step: OKX/Binance Data Collection

## 1) Collect these datasets first

1. Wallet network params and availability
2. Withdraw order history
3. Deposit order history
4. System status + announcements
5. Helpcenter articles

## 2) Official endpoints to map

### OKX
- `GET /api/v5/asset/currencies`
- `GET /api/v5/asset/deposit-history`
- `GET /api/v5/asset/withdrawal-history`
- `GET /api/v5/system/status`
- `GET /api/v5/support/announcements`

### Binance
- `GET /sapi/v1/capital/config/getall`
- `GET /sapi/v1/capital/deposit/hisrec`
- `GET /sapi/v1/capital/withdraw/history`
- Support center and announcement pages for KB ingestion

## 3) Run order

1. Load schema: `sql/support_kb_schema.sql`
2. Import bootstrap docs: `data/kb/bootstrap_kb.jsonl`
3. Ingest helpcenter seeds:
   `python scripts/kb_ingest_helpcenter.py --out data/kb/helpcenter_docs.jsonl`
4. Prefer Playwright ingestion for JS pages + incremental updates:
   `python scripts/kb_ingest_helpcenter_playwright.py --out data/kb/helpcenter_docs.jsonl --state data/kb/helpcenter_state.json --delta data/kb/helpcenter_delta.jsonl`
5. Merge `bootstrap_kb.jsonl + helpcenter_docs.jsonl` into final `kb_documents`
6. Build chunks and embeddings for retrieval

## 4) Minimum acceptance for this step

1. At least 30 helpcenter docs in `kb_documents`
2. Every row has `source_url` and `updated_at`
3. Top-3 retrieval can return wallet/deposit/withdraw/KYB related docs
4. Status questions can map to one of:
   `get_wallet_network_status`, `get_withdraw_status`, `get_deposit_status`, `get_kyb_status`

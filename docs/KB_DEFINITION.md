# Knowledge Base Definition

## Knowledge bases

1. `okx` (external)
- Source: help center crawl
- Files: `data/kb/okx_helpcenter_docs.jsonl`, `data/kb/helpcenter_docs.jsonl`
- Audience: `user`

2. `binance` (external)
- Source: help center crawl + curated docs
- Files: `data/kb/helpcenter_docs.jsonl`, `data/kb/bootstrap_kb.jsonl`
- Audience: `user`

3. `px` (manual/internal)
- Source: manually maintained product docs + workflow docs
- Folder: `data/kb/manual/px/`
- Ingest script: `scripts/kb_ingest_local_docs.py --platform px`
- Audience: default `internal`

## Unified document schema

Each JSONL row should include:
- `id`
- `title`
- `category`
- `product`
- `symbol`
- `network`
- `tags`
- `content`
- `source_url`
- `status_tag`
- `effective_time`
- `updated_at`
- `audience`
- `platform`
- `content_fingerprint`

## Build sequence

1. Crawl external docs (`okx`, `binance`)
2. Ingest manual docs (`px`)
3. Merge into `data/kb/kb_master.jsonl`
4. `search_kb` reads `kb_master.jsonl` first, mock fallback second

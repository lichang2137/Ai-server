-- Support agent MVP schema (6 tables)

CREATE TABLE IF NOT EXISTS kb_documents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  product TEXT,
  symbol TEXT,
  network TEXT,
  tags TEXT NOT NULL, -- JSON array string
  content TEXT NOT NULL,
  source_url TEXT NOT NULL,
  status_tag TEXT NOT NULL DEFAULT 'active',
  effective_time TEXT,
  updated_at TEXT NOT NULL,
  audience TEXT NOT NULL DEFAULT 'user',
  platform TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kb_chunks (
  chunk_id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  token_count INTEGER,
  embedding_key TEXT,
  FOREIGN KEY (doc_id) REFERENCES kb_documents(id)
);

CREATE TABLE IF NOT EXISTS source_sync_runs (
  run_id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  source_type TEXT NOT NULL, -- helpcenter/api/announcement
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL, -- running/success/failed/partial
  fetched_count INTEGER NOT NULL DEFAULT 0,
  written_count INTEGER NOT NULL DEFAULT 0,
  error_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS source_sync_errors (
  error_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  source_url TEXT,
  error_code TEXT,
  error_message TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES source_sync_runs(run_id)
);

CREATE TABLE IF NOT EXISTS wallet_network_status_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  asset TEXT NOT NULL,
  network TEXT NOT NULL,
  deposit_enabled INTEGER NOT NULL,
  withdraw_enabled INTEGER NOT NULL,
  maintenance_status TEXT,
  maintenance_reason TEXT,
  estimated_recovery_time TEXT,
  raw_payload TEXT NOT NULL, -- original API response JSON
  captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_status_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  user_id TEXT NOT NULL,
  order_type TEXT NOT NULL, -- deposit/withdraw
  order_id TEXT NOT NULL,
  asset TEXT NOT NULL,
  network TEXT,
  amount TEXT,
  txid TEXT,
  internal_status TEXT,
  chain_status TEXT,
  confirmations INTEGER,
  required_confirmations INTEGER,
  risk_review_status TEXT,
  raw_payload TEXT NOT NULL,
  last_updated_at TEXT,
  captured_at TEXT NOT NULL
);

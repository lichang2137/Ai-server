CREATE TABLE IF NOT EXISTS support_sessions (
  session_id TEXT PRIMARY KEY,
  platform_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  channel_user_id TEXT NOT NULL,
  platform_user_id TEXT,
  locale TEXT NOT NULL DEFAULT 'zh-CN',
  last_route TEXT,
  turns_count INTEGER NOT NULL DEFAULT 0,
  clarification_turns INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS message_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  direction TEXT NOT NULL,
  route TEXT,
  text TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES support_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS handoff_summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  route TEXT NOT NULL,
  summary_type TEXT NOT NULL,
  user_id TEXT,
  current_status TEXT,
  missing_items_json TEXT NOT NULL DEFAULT '[]',
  rejection_reason TEXT,
  suggested_action TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES support_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS review_cases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL UNIQUE,
  session_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  route TEXT NOT NULL,
  decision TEXT NOT NULL,
  confidence REAL NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES support_sessions(session_id)
);

#!/usr/bin/env python3
"""Ingest manually maintained docs (px/okx/binance) into KB JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


SUPPORTED = {".md", ".txt", ".json", ".html"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".json":
        try:
            obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            return path.read_text(encoding="utf-8", errors="ignore")
    return path.read_text(encoding="utf-8", errors="ignore")


def _guess_category(path: Path, text: str) -> str:
    blob = f"{path.name} {text[:1000]}".lower()
    if "workflow" in blob:
        return "workflow"
    if "kyb" in blob or "kyc" in blob or "verification" in blob:
        return "kyb"
    if "withdraw" in blob:
        return "withdraw"
    if "deposit" in blob:
        return "deposit"
    if "announcement" in blob or "notice" in blob:
        return "announcement"
    return "helpcenter"


def ingest_dir(root: Path, platform: str, audience: str = "internal") -> List[Dict]:
    rows: List[Dict] = []
    if not root.exists():
        return rows

    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in SUPPORTED:
            continue
        text = _read_text(p).strip()
        if not text:
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        fid = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:12]
        rows.append(
            {
                "id": f"{platform}_manual_{fid}",
                "title": p.stem,
                "category": _guess_category(p, text),
                "product": "support",
                "symbol": None,
                "network": None,
                "tags": [platform, "manual_docs"],
                "content": text[:20000],
                "source_url": f"file://{rel}",
                "status_tag": "active",
                "effective_time": None,
                "updated_at": _now_iso(),
                "audience": audience,
                "platform": platform,
                "content_fingerprint": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
    return rows


def write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest local manual docs into KB JSONL")
    parser.add_argument("--input-dir", required=True, help="Folder containing docs")
    parser.add_argument("--platform", required=True, choices=["px", "okx", "binance"])
    parser.add_argument("--audience", default="internal", choices=["internal", "user"])
    parser.add_argument("--out", default="data/kb/manual_docs.jsonl")
    args = parser.parse_args()

    rows = ingest_dir(Path(args.input_dir), args.platform, args.audience)
    write_jsonl(Path(args.out), rows)
    print(json.dumps({"status": "ok", "count": len(rows), "out": args.out}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

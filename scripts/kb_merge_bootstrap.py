#!/usr/bin/env python3
"""Merge bootstrap KB and crawled helpcenter docs into one JSONL.

Dedup order:
1) content_fingerprint
2) source_url
3) id
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _fp(row: Dict) -> str:
    seed = _norm_text(row.get("content", "")) + "|" + str(row.get("source_url", ""))
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def merge(bootstrap_path: Path, crawled_path: Path, out_path: Path) -> Dict:
    merged_by_id: Dict[str, Dict] = {}
    seen_fp: Dict[str, str] = {}
    seen_url: Dict[str, str] = {}
    stats = {"bootstrap": 0, "crawled": 0, "deduped": 0, "written": 0}

    for row in _load_jsonl(bootstrap_path):
        stats["bootstrap"] += 1
        row.setdefault("content_fingerprint", _fp(row))
        rid = str(row["id"])
        merged_by_id[rid] = row
        seen_fp[row["content_fingerprint"]] = rid
        if row.get("source_url"):
            seen_url[row["source_url"]] = rid

    for row in _load_jsonl(crawled_path):
        stats["crawled"] += 1
        row.setdefault("content_fingerprint", _fp(row))
        rid = str(row["id"])
        fpk = row["content_fingerprint"]
        src = row.get("source_url")

        if fpk in seen_fp:
            stats["deduped"] += 1
            merged_by_id[seen_fp[fpk]] = row
            continue
        if src and src in seen_url:
            stats["deduped"] += 1
            merged_by_id[seen_url[src]] = row
            continue

        merged_by_id[rid] = row
        seen_fp[fpk] = rid
        if src:
            seen_url[src] = rid

    rows = sorted(merged_by_id.values(), key=lambda r: (r.get("platform", ""), r.get("id", "")))
    _write_jsonl(out_path, rows)
    stats["written"] = len(rows)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge KB bootstrap + crawled docs")
    parser.add_argument("--bootstrap", default="data/kb/bootstrap_kb.jsonl")
    parser.add_argument("--crawled", default="data/kb/helpcenter_docs.jsonl")
    parser.add_argument("--out", default="data/kb/kb_master.jsonl")
    args = parser.parse_args()

    stats = merge(Path(args.bootstrap), Path(args.crawled), Path(args.out))
    print(json.dumps({"status": "ok", "stats": stats}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

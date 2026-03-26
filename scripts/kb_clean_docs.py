#!/usr/bin/env python3
"""Clean low-quality or blocked docs from KB JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def _blocked(row: Dict) -> bool:
    blob = f"{row.get('title', '')} {row.get('content', '')}".lower()
    signals = [
        "human verification",
        "verify you are human",
        "security check",
        "captcha",
    ]
    return any(s in blob for s in signals)


def clean(path: Path) -> Dict:
    if not path.exists():
        return {"status": "missing", "removed": 0, "written": 0}

    rows: List[Dict] = []
    removed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if _blocked(row):
            removed += 1
            continue
        rows.append(row)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"status": "ok", "removed": removed, "written": len(rows)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean KB JSONL docs")
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    print(json.dumps(clean(Path(args.file)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

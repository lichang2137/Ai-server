#!/usr/bin/env python3
"""Ingest OKX/Binance helpcenter seeds into normalized JSONL.

Usage:
  python scripts/kb_ingest_helpcenter.py --out data/kb/helpcenter_docs.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Dict, List


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AiServerBot/0.1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug_from_url(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[:80]


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if not m:
        return "untitled"
    title = re.sub(r"\s+", " ", unescape(m.group(1))).strip()
    return title


def _extract_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _guess_category(url: str, title: str) -> str:
    s = (url + " " + title).lower()
    if any(k in s for k in ["kyc", "kyb", "verification"]):
        return "kyb"
    if "withdraw" in s:
        return "withdraw"
    if "deposit" in s:
        return "deposit"
    if any(k in s for k in ["announcement", "notice"]):
        return "announcement"
    return "helpcenter"


def _fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def run(seed_file: Path, out_file: Path, delay_sec: float) -> Dict[str, int]:
    seed = json.loads(seed_file.read_text(encoding="utf-8"))
    rows: List[Dict] = []
    ok = 0
    fail = 0

    for source in seed.get("sources", []):
        platform = source.get("platform")
        for url in source.get("urls", []):
            try:
                html = _fetch(url)
                title = _extract_title(html)
                content = _extract_text(html)[:8000]
                rows.append(
                    {
                        "id": f"{platform}_{_slug_from_url(url)}",
                        "title": title,
                        "category": _guess_category(url, title),
                        "product": "wallet",
                        "symbol": None,
                        "network": None,
                        "tags": [platform, "helpcenter"],
                        "content": content,
                        "source_url": url,
                        "status_tag": "active",
                        "effective_time": None,
                        "updated_at": _now_iso(),
                        "audience": "user",
                        "platform": platform,
                    }
                )
                ok += 1
            except Exception:
                fail += 1
            time.sleep(delay_sec)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"success": ok, "failed": fail, "written": len(rows)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest helpcenter pages")
    parser.add_argument(
        "--seed",
        default="data/kb/helpcenter_seed_urls.json",
        help="Path to seed URL config JSON",
    )
    parser.add_argument(
        "--out",
        default="data/kb/helpcenter_docs.jsonl",
        help="Output normalized JSONL path",
    )
    parser.add_argument("--delay", type=float, default=0.6, help="Delay between requests")
    args = parser.parse_args()

    stats = run(Path(args.seed), Path(args.out), args.delay)
    print(json.dumps({"status": "ok", "stats": stats}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

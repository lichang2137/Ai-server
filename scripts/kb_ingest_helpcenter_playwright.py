#!/usr/bin/env python3
"""Playwright-based helpcenter ingestion with dedupe + incremental sync.

Features:
- Rendered page crawling (JS-heavy pages)
- Automatic dedupe (by content fingerprint)
- Incremental update (URL state tracking)
- Upsert into normalized JSONL

Install:
  pip install playwright
  playwright install chromium

Run:
  python scripts/kb_ingest_helpcenter_playwright.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug_from_url(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[:80]


def _normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _content_fingerprint(text: str) -> str:
    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()


def _guess_category(url: str, title: str, content: str) -> str:
    blob = f"{url} {title} {content}".lower()
    if any(k in blob for k in ["kyc", "kyb", "identity verification", "verification failed"]):
        return "kyb"
    if "withdraw" in blob:
        return "withdraw"
    if "deposit" in blob:
        return "deposit"
    if any(k in blob for k in ["announcement", "notice"]):
        return "announcement"
    return "helpcenter"


def _looks_like_human_verification(title: str, content: str) -> bool:
    blob = f"{title} {content}".lower()
    signals = [
        "human verification",
        "verify you are human",
        "security check",
        "before continuing",
        "captcha",
    ]
    return any(s in blob for s in signals)


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl_map(path: Path, key: str) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows[str(row[key])] = row
    return rows


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _extract_updated_hint(title: str, content: str) -> str:
    text = f"{title} {content}"
    m = re.search(r"Updated on ([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", text)
    if m:
        return m.group(1)
    return ""


def _crawl_with_playwright(url: str, timeout_ms: int, wait_ms: int) -> Tuple[str, str]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Playwright is not available. Install with: pip install playwright && playwright install chromium"
        ) from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(wait_ms)
        title = page.title() or "untitled"
        # Prefer main/article text where possible.
        content = page.evaluate(
            """() => {
              const selectors = ['article', 'main', '[role="main"]', '.article', '.content'];
              for (const s of selectors) {
                const n = document.querySelector(s);
                if (n && n.innerText && n.innerText.trim().length > 100) return n.innerText;
              }
              return document.body ? document.body.innerText : '';
            }"""
        )
        browser.close()
    return _normalize_text(title), _normalize_text(content)


def run(
    seed_path: Path,
    out_path: Path,
    state_path: Path,
    delta_path: Path,
    delay_sec: float,
    timeout_ms: int,
    wait_ms: int,
    force: bool,
) -> Dict[str, Any]:
    seed = _load_json(seed_path, {"sources": []})
    state = _load_json(state_path, {"urls": {}, "fingerprints": {}, "updated_at": None})
    docs_by_id = _load_jsonl_map(out_path, "id")
    docs_by_fp = {row.get("content_fingerprint"): row.get("id") for row in docs_by_id.values() if row.get("content_fingerprint")}

    stats = {
        "fetched": 0,
        "updated": 0,
        "unchanged": 0,
        "deduped": 0,
        "failed": 0,
        "written_total": 0,
    }
    delta_rows: List[Dict[str, Any]] = []

    for source in seed.get("sources", []):
        platform = source.get("platform", "unknown")
        urls = source.get("urls", [])
        for url in urls:
            old_meta = state["urls"].get(url, {})
            try:
                title, content = _crawl_with_playwright(url, timeout_ms=timeout_ms, wait_ms=wait_ms)
                stats["fetched"] += 1
                content = content[:12000]
                if _looks_like_human_verification(title, content):
                    raise RuntimeError("Blocked by human-verification page")
                fp = _content_fingerprint(content)

                if not force and old_meta.get("content_fingerprint") == fp:
                    stats["unchanged"] += 1
                    state["urls"][url] = {
                        **old_meta,
                        "last_seen_at": _now_iso(),
                    }
                    time.sleep(delay_sec)
                    continue

                # Cross-url dedupe: same content hash under different URL.
                existing_id = docs_by_fp.get(fp)
                if existing_id and existing_id not in docs_by_id:
                    existing_id = None

                if existing_id:
                    stats["deduped"] += 1
                    doc_id = existing_id
                else:
                    doc_id = f"{platform}_{_slug_from_url(url)}"

                row = {
                    "id": doc_id,
                    "title": title,
                    "category": _guess_category(url, title, content),
                    "product": "wallet",
                    "symbol": None,
                    "network": None,
                    "tags": [platform, "helpcenter"],
                    "content": content,
                    "source_url": url,
                    "status_tag": "active",
                    "effective_time": None,
                    "updated_at": _now_iso(),
                    "updated_hint": _extract_updated_hint(title, content),
                    "audience": "user",
                    "platform": platform,
                    "content_fingerprint": fp,
                }
                docs_by_id[row["id"]] = row
                docs_by_fp[fp] = row["id"]
                delta_rows.append(row)
                stats["updated"] += 1

                state["urls"][url] = {
                    "doc_id": row["id"],
                    "title": title,
                    "content_fingerprint": fp,
                    "last_seen_at": _now_iso(),
                }
            except Exception as e:
                stats["failed"] += 1
                state["urls"][url] = {
                    **old_meta,
                    "last_error": str(e),
                    "last_error_at": _now_iso(),
                }
            time.sleep(delay_sec)

    state["updated_at"] = _now_iso()
    state["doc_count"] = len(docs_by_id)

    all_rows = sorted(docs_by_id.values(), key=lambda r: (r.get("platform", ""), r.get("id", "")))
    stats["written_total"] = len(all_rows)

    _write_jsonl(out_path, all_rows)
    _write_jsonl(delta_path, delta_rows)
    _write_json(state_path, state)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Playwright helpcenter ingestion")
    parser.add_argument("--seed", default="data/kb/helpcenter_seed_urls.json")
    parser.add_argument("--out", default="data/kb/helpcenter_docs.jsonl")
    parser.add_argument("--state", default="data/kb/helpcenter_state.json")
    parser.add_argument("--delta", default="data/kb/helpcenter_delta.jsonl")
    parser.add_argument("--delay", type=float, default=0.8)
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument("--wait-ms", type=int, default=1800)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    stats = run(
        seed_path=Path(args.seed),
        out_path=Path(args.out),
        state_path=Path(args.state),
        delta_path=Path(args.delta),
        delay_sec=args.delay,
        timeout_ms=args.timeout_ms,
        wait_ms=args.wait_ms,
        force=args.force,
    )
    print(json.dumps({"status": "ok", "stats": stats}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


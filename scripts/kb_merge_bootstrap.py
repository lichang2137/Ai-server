#!/usr/bin/env python3
"""Build KB master file from registry + files + manual directories.

Capabilities:
1) Read registry-defined sources (okx/binance/px)
2) Ingest manual docs from directories (.md/.txt/.json/.html)
3) Normalize all rows to fixed schema
4) Dedupe by content_fingerprint, then source_url, then id
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


SUPPORTED_SUFFIX = {".md", ".txt", ".json", ".html"}
BASE_FIELDS = [
    "id",
    "title",
    "category",
    "product",
    "symbol",
    "network",
    "tags",
    "content",
    "source_url",
    "status_tag",
    "effective_time",
    "updated_at",
    "audience",
    "platform",
    "content_fingerprint",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _guess_category(blob: str) -> str:
    s = blob.lower()
    if any(k in s for k in ["workflow", "sop", "runbook"]):
        return "workflow"
    if any(k in s for k in ["kyb", "kyc", "verification"]):
        return "kyb"
    if "withdraw" in s:
        return "withdraw"
    if "deposit" in s:
        return "deposit"
    if any(k in s for k in ["announcement", "notice"]):
        return "announcement"
    return "helpcenter"


def _fp_from_text(content: str, source_url: str) -> str:
    seed = f"{_norm_text(content)}|{_norm_text(source_url)}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _is_low_quality_row(row: Dict[str, Any]) -> bool:
    title = _norm_text(row.get("title", "")).lower()
    content = _norm_text(row.get("content", "")).lower()
    source_url = _norm_text(row.get("source_url", "")).lower()
    category = _norm_text(row.get("category", "")).lower()

    blocked = [
        "human verification",
        "verify you are human",
        "security check",
        "captcha",
    ]
    generic = [
        "support faq",
        "help center",
        "cookie preferences",
    ]
    min_len = 40 if category in {"kyb", "workflow"} else 60
    if len(content) < min_len:
        return True
    if any(s in title or s in content for s in blocked):
        return True
    if (source_url.endswith("/help") or "/support/faq" in source_url) and any(g in content for g in generic):
        return True
    return False


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".json":
        try:
            obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            return path.read_text(encoding="utf-8", errors="ignore")
    return path.read_text(encoding="utf-8", errors="ignore")


def _ingest_manual_dir(path: Path, platform: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for p in path.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in SUPPORTED_SUFFIX:
            continue
        content = _read_text(p).strip()
        if not content:
            continue
        rel = str(p.relative_to(path)).replace("\\", "/")
        doc_id = f"{platform}_manual_{hashlib.sha256(rel.encode('utf-8')).hexdigest()[:12]}"
        row = {
            "id": doc_id,
            "title": p.stem,
            "category": _guess_category(f"{p.name} {content[:1200]}"),
            "product": "support",
            "symbol": None,
            "network": None,
            "tags": [platform, "manual_docs"],
            "content": content[:20000],
            "source_url": f"file://{rel}",
            "status_tag": "active",
            "effective_time": None,
            "updated_at": _now_iso(),
            "audience": "internal",
            "platform": platform,
        }
        row["content_fingerprint"] = _fp_from_text(row["content"], row["source_url"])
        rows.append(row)
    return rows


def _normalize_row(row: Dict[str, Any], default_platform: str = "unknown") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    out["id"] = str(row.get("id") or f"{default_platform}_{hashlib.sha256(json.dumps(row, ensure_ascii=False).encode('utf-8')).hexdigest()[:12]}")
    out["title"] = _norm_text(row.get("title") or "untitled")
    content = _norm_text(row.get("content") or "")
    out["content"] = content
    out["category"] = _norm_text(row.get("category") or _guess_category(f"{out['title']} {content[:1200]}"))
    out["product"] = _norm_text(row.get("product") or "support")
    out["symbol"] = row.get("symbol")
    out["network"] = row.get("network")
    tags = row.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    out["tags"] = [str(x).strip() for x in tags if str(x).strip()]
    out["source_url"] = _norm_text(row.get("source_url") or "")
    out["status_tag"] = _norm_text(row.get("status_tag") or "active")
    out["effective_time"] = row.get("effective_time")
    out["updated_at"] = _norm_text(row.get("updated_at") or _now_iso())
    out["audience"] = _norm_text(row.get("audience") or "user")
    out["platform"] = _norm_text(row.get("platform") or default_platform)
    out["content_fingerprint"] = _norm_text(
        row.get("content_fingerprint") or _fp_from_text(out["content"], out["source_url"])
    )

    # Keep output fixed and predictable.
    return {k: out.get(k) for k in BASE_FIELDS}


def _collect_rows_from_registry(registry_path: Path, root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    all_rows: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}

    for kb in registry.get("knowledge_bases", []):
        if not kb.get("enabled", True):
            continue
        name = kb.get("name", "unknown")
        source_count = 0
        for p in kb.get("inputs", []):
            path = (root / p).resolve()
            if path.is_dir():
                rows = _ingest_manual_dir(path, platform=name)
                all_rows.extend(rows)
                source_count += len(rows)
            elif path.is_file():
                if path.suffix.lower() == ".jsonl":
                    rows = _read_jsonl(path)
                    all_rows.extend(rows)
                    source_count += len(rows)
                elif path.suffix.lower() == ".json":
                    data = json.loads(path.read_text(encoding="utf-8"))
                    # ignore registry/seed-style json here
                    if isinstance(data, list):
                        all_rows.extend(data)
                        source_count += len(data)
        counts[name] = source_count
    return all_rows, counts


def _dedupe_rows(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    by_id: Dict[str, Dict[str, Any]] = {}
    by_fp: Dict[str, str] = {}
    by_url: Dict[str, str] = {}
    deduped = 0

    for row in rows:
        rid = row["id"]
        fp = row.get("content_fingerprint", "")
        url = row.get("source_url", "")

        if fp and fp in by_fp:
            by_id[by_fp[fp]] = row
            deduped += 1
            continue
        if url and url in by_url:
            by_id[by_url[url]] = row
            deduped += 1
            continue

        by_id[rid] = row
        if fp:
            by_fp[fp] = rid
        if url:
            by_url[url] = rid

    merged = sorted(by_id.values(), key=lambda r: (r.get("platform", ""), r.get("id", "")))
    return merged, deduped


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build(registry_path: Path, out_path: Path, root: Path) -> Dict[str, Any]:
    raw_rows, counts = _collect_rows_from_registry(registry_path, root)
    normalized = [_normalize_row(r, default_platform=str(r.get("platform", "unknown"))) for r in raw_rows]
    filtered = [r for r in normalized if not _is_low_quality_row(r)]
    merged, deduped = _dedupe_rows(filtered)
    _write_jsonl(out_path, merged)
    return {
        "sources": counts,
        "raw_rows": len(raw_rows),
        "normalized_rows": len(normalized),
        "filtered_rows": len(filtered),
        "deduped": deduped,
        "written": len(merged),
        "out": str(out_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build kb_master.jsonl from registry")
    parser.add_argument("--registry", default="data/kb/source_registry.json")
    parser.add_argument("--out", default="data/kb/kb_master.jsonl")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    stats = build(Path(args.registry), Path(args.out), Path(args.root).resolve())
    print(json.dumps({"status": "ok", "stats": stats}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

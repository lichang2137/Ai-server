#!/usr/bin/env python3
"""Smoke test: 20 representative KB queries should return usable Top3."""

from __future__ import annotations

import json

from p0_tools import search_kb


QUERIES = [
    "deposit not credited",
    "why has not my deposit been credited",
    "withdrawal pending",
    "how to withdraw on okx",
    "tag memo required",
    "forgot memo when withdrawing",
    "find deposit address",
    "network mismatch deposit",
    "minimum deposit amount",
    "unsupported network",
    "identity verification failed",
    "kyc verification failed",
    "wallet maintenance",
    "binance deposit withdrawal guide",
    "how to complete identity verification",
    "txid not found",
    "withdraw not arrived",
    "deposit confirmation delay",
    "crypto withdrawal fee",
    "support ticket for memo issue",
]


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    results = []
    for q in QUERIES:
        r = search_kb(q, limit=3)
        _assert(r.get("status_code") == "OK", f"status not OK for query: {q}")
        docs = r.get("data", {}).get("results", [])
        _assert(len(docs) > 0, f"empty result for query: {q}")
        _assert(len(docs) <= 3, f"more than Top3 for query: {q}")
        _assert(all(d.get("source_url") for d in docs), f"missing source_url for query: {q}")
        results.append({"query": q, "top": docs[0].get("title")})

    print(json.dumps({"smoke": "passed", "queries": len(QUERIES), "samples": results[:5]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

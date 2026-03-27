#!/usr/bin/env python3
"""P0 adapter layer for support-agent mock tools.

This module exposes the first-batch MVP tool names with a unified response
contract so the Agent can call stable interfaces before real integrations.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import mock_tools


STATUS_OK = "OK"
STATUS_ERROR = "ERROR"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_MASTER_PATH = os.path.join(BASE_DIR, "data", "kb", "kb_master.jsonl")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    text = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _latest_timestamp(candidates: List[Optional[str]]) -> str:
    parsed = [_parse_iso(x) for x in candidates if x]
    if not parsed:
        return _now_iso()
    return max(parsed).isoformat().replace("+00:00", "Z")


def _build_success(data: Dict[str, Any], message: str, last_updated_at: Optional[str] = None) -> Dict[str, Any]:
    return {
        "status_code": STATUS_OK,
        "error_code": None,
        "message": message,
        "last_updated_at": last_updated_at or _now_iso(),
        "data": data,
        "is_mock": True,
    }


def _build_error(error_code: str, message: str, last_updated_at: Optional[str] = None) -> Dict[str, Any]:
    return {
        "status_code": STATUS_ERROR,
        "error_code": error_code,
        "message": message,
        "last_updated_at": last_updated_at or _now_iso(),
        "data": {},
        "is_mock": True,
    }


def _assert_user_access(user_id: str, requester_user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if requester_user_id and requester_user_id != user_id:
        return _build_error(
            "TOOL_ERROR_PERMISSION_DENIED",
            "Permission denied: requester can only query their own records.",
        )
    return None


def _safe_call(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if "error" not in result:
        return None
    return _build_error(result["error"], result.get("message", "tool error"))


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9_]+", (text or "").lower()) if t]


def _load_master_docs() -> List[Dict[str, Any]]:
    if not os.path.exists(KB_MASTER_PATH):
        return []
    docs: List[Dict[str, Any]] = []
    with open(KB_MASTER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                docs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return docs


def _score_doc(query_tokens: List[str], doc: Dict[str, Any]) -> int:
    title = (doc.get("title") or "").lower()
    content = (doc.get("content") or "").lower()
    tags = " ".join(doc.get("tags") or []).lower()
    score = 0
    for t in query_tokens:
        if t in title:
            score += 5
        if t in tags:
            score += 3
        if t in content:
            score += 1
    return score


def search_kb(query: str, context: Optional[Dict[str, Any]] = None, limit: int = 3) -> Dict[str, Any]:
    """Search help center / KB with MVP schema.

    Required minimum fields:
    doc_id, title, category, content, source_url, updated_at, tags
    """
    context = context or {}
    platform = context.get("platform")
    category = context.get("category")
    max_n = max(1, min(limit, 10))

    # Primary source: merged local KB.
    master_docs = _load_master_docs()
    mapped: List[Dict[str, Any]] = []
    if master_docs:
        q_tokens = _tokenize(query)
        scored = []
        for doc in master_docs:
            if platform and doc.get("platform") != platform:
                continue
            if category and doc.get("category") != category:
                continue
            s = _score_doc(q_tokens, doc)
            if s > 0:
                scored.append((s, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        for _, doc in scored[:max_n]:
            mapped.append(
                {
                    "doc_id": doc.get("id"),
                    "title": doc.get("title"),
                    "category": doc.get("category", "faq"),
                    "content": (doc.get("content") or "")[:400],
                    "source_url": doc.get("source_url"),
                    "updated_at": doc.get("updated_at"),
                    "tags": doc.get("tags") or [],
                }
            )

    # Fallback: legacy mock list.
    if not mapped:
        raw = mock_tools.docs_search_helpcenter(
            query=query,
            platform=platform,
            category=category,
            limit=max_n,
        )
        for idx, doc in enumerate(raw.get("docs", []), start=1):
            mapped.append(
                {
                    "doc_id": f"kb_{idx}",
                    "title": doc.get("title"),
                    "category": doc.get("category", "faq"),
                    "content": doc.get("snippet", ""),
                    "source_url": doc.get("url"),
                    "updated_at": doc.get("updated_at"),
                    "tags": [x for x in [doc.get("platform"), doc.get("category")] if x],
                }
            )

    if not mapped:
        return _build_success(
            {
                "results": [],
                "empty_reason": "No matching KB documents for query.",
                "query": query,
                "context": context,
            },
            message="KB search completed with empty result.",
        )

    return _build_success(
        {
            "results": mapped,
            "empty_reason": None,
            "query": query,
            "context": context,
        },
        message="KB search completed.",
        last_updated_at=_latest_timestamp([x.get("updated_at") for x in mapped]),
    )


def get_kyb_status(user_id: str, requester_user_id: Optional[str] = None) -> Dict[str, Any]:
    permission_error = _assert_user_access(user_id, requester_user_id)
    if permission_error:
        return permission_error

    raw = mock_tools.get_kyb_status(user_id=user_id)
    err = _safe_call(raw)
    if err:
        return err

    kyb = raw.get("kyb_status") or {}
    data = {
        "user_id": user_id,
        "current_status": kyb.get("current_status"),
        "review_stage": kyb.get("current_status"),
        "missing_docs": [i.get("doc_type") for i in kyb.get("items", []) if i.get("status") == "missing"],
        "rejected_docs": [i.get("doc_type") for i in kyb.get("items", []) if i.get("status") == "rejected"],
        "rejection_reason": kyb.get("rejection_reason"),
        "next_action": kyb.get("next_action"),
    }
    data["last_updated_at"] = _latest_timestamp([kyb.get("reviewed_at"), kyb.get("submitted_at")])
    return _build_success(data, "KYB status fetched.", last_updated_at=data["last_updated_at"])


def get_withdraw_status(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    requester_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    permission_error = _assert_user_access(user_id, requester_user_id)
    if permission_error:
        return permission_error

    filters = filters or {}
    asset = filters.get("asset")
    network = filters.get("network")
    order_id = filters.get("order_id")
    txid = filters.get("txid")

    raw = mock_tools.get_withdraw_status(user_id=user_id, asset=asset, network=network, limit=20)
    err = _safe_call(raw)
    if err:
        return err

    rows = raw.get("withdrawals", [])

    def matches(row: Dict[str, Any]) -> bool:
        if order_id and order_id.lower() not in str(row.get("order_id", "")).lower():
            return False
        if txid and txid.lower() not in str(row.get("txid", "")).lower():
            return False
        return True

    rows = [r for r in rows if matches(r)]

    mapped = []
    for row in rows:
        mapped.append(
            {
                "order_id": row.get("order_id"),
                "asset": row.get("asset"),
                "network": row.get("network"),
                "amount": row.get("amount"),
                "submit_time": row.get("submit_time"),
                "internal_status": row.get("internal_status"),
                "txid": row.get("txid"),
                "chain_status": row.get("chain_status"),
                "confirmations": row.get("confirmations"),
                "required_confirmations": row.get("required_confirmations"),
                "risk_review_status": row.get("risk_review_status"),
                "last_updated_at": row.get("last_update_time"),
            }
        )

    if not mapped:
        return _build_success(
            {
                "results": [],
                "empty_reason": "No withdrawal order matched the filters.",
                "filters": filters,
            },
            "Withdraw status query completed with empty result.",
        )

    return _build_success(
        {
            "results": mapped,
            "empty_reason": None,
            "filters": filters,
        },
        "Withdraw status fetched.",
        last_updated_at=_latest_timestamp([x.get("last_updated_at") for x in mapped]),
    )


def get_wallet_network_status(asset: str, network: str, requester_user_id: Optional[str] = None) -> Dict[str, Any]:
    _ = requester_user_id
    raw = mock_tools.get_wallet_network_status(asset=asset, network=network)
    err = _safe_call(raw)
    if err:
        return err

    row = raw.get("wallet_status") or {}
    data = {
        "asset": row.get("asset"),
        "network": row.get("network"),
        "deposit_enabled": row.get("deposit_enabled"),
        "withdraw_enabled": row.get("withdraw_enabled"),
        "maintenance_status": row.get("maintenance_status"),
        "maintenance_reason": row.get("maintenance_reason"),
        "estimated_recovery_time": row.get("estimated_recovery"),
        "notice_link": None,
        "updated_at": _now_iso(),
    }
    data["last_updated_at"] = data["updated_at"]
    return _build_success(data, "Wallet network status fetched.", last_updated_at=data["last_updated_at"])


def main() -> None:
    parser = argparse.ArgumentParser(description="P0 unified mock tool adapter")
    parser.add_argument("tool", choices=[
        "search_kb",
        "get_kyb_status",
        "get_withdraw_status",
        "get_wallet_network_status",
    ])
    parser.add_argument("--query", default="")
    parser.add_argument("--context", default="{}", help="JSON string")
    parser.add_argument("--user_id", default="")
    parser.add_argument("--requester_user_id", default=None)
    parser.add_argument("--filters", default="{}", help="JSON string")
    parser.add_argument("--asset", default="")
    parser.add_argument("--network", default="")
    args = parser.parse_args()

    if args.tool == "search_kb":
        result = search_kb(query=args.query, context=json.loads(args.context or "{}"))
    elif args.tool == "get_kyb_status":
        result = get_kyb_status(user_id=args.user_id, requester_user_id=args.requester_user_id)
    elif args.tool == "get_withdraw_status":
        result = get_withdraw_status(
            user_id=args.user_id,
            filters=json.loads(args.filters or "{}"),
            requester_user_id=args.requester_user_id,
        )
    else:
        result = get_wallet_network_status(
            asset=args.asset,
            network=args.network,
            requester_user_id=args.requester_user_id,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

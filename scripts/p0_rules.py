#!/usr/bin/env python3
"""Rule engine skeleton for Stage 2.

Includes:
- YAML(JSON-compatible) rule loading
- P0 diagnosis helpers for KYB / withdraw / wallet
- Minimal follow-up entrypoint (ask at most one question)
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Optional

import p0_tools


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_DIR = os.path.join(BASE_DIR, "rules")


def _load_rule_set(filename: str) -> Dict[str, Any]:
    path = os.path.join(RULES_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _match_when(payload: Dict[str, Any], when: Dict[str, Any]) -> bool:
    for key, expected in when.items():
        actual = payload.get(key)
        if isinstance(expected, dict) and "in" in expected:
            if actual not in expected["in"]:
                return False
            continue
        if actual != expected:
            return False
    return True


def _apply_rules(rule_set: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    defaults = rule_set.get("defaults", {})
    rules = sorted(rule_set.get("rules", []), key=lambda x: int(x.get("priority", 0)), reverse=True)
    for rule in rules:
        if _match_when(payload, rule.get("when", {})):
            result = dict(defaults)
            result.update(rule.get("result", {}))
            result["matched_rule_id"] = rule.get("id")
            return result
    result = dict(defaults)
    result["matched_rule_id"] = None
    return result


def diagnose_kyb(kyb_status: Dict[str, Any]) -> Dict[str, Any]:
    rules = _load_rule_set("kyb_rules.yaml")
    return _apply_rules(rules, kyb_status)


def diagnose_withdraw(withdraw_status: Dict[str, Any]) -> Dict[str, Any]:
    rules = _load_rule_set("withdraw_rules.yaml")
    return _apply_rules(rules, withdraw_status)


def diagnose_wallet(wallet_status: Dict[str, Any]) -> Dict[str, Any]:
    rules = _load_rule_set("wallet_rules.yaml")
    return _apply_rules(rules, wallet_status)


FOLLOWUP_ORDER = {
    "kyb": ["user_id"],
    "withdraw": ["user_id", "asset"],
    "wallet": ["asset", "network"],
    "kb": ["query"],
}

FOLLOWUP_QUESTION = {
    "user_id": "Please share your UID so I can check your exact status.",
    "asset": "Please tell me the asset symbol, for example USDT or BTC.",
    "network": "Please tell me the network, for example TRC20 or ERC20.",
    "query": "Please provide a keyword for your question so I can search the help center.",
}


def minimal_followup(intent: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    context = context or {}
    required = FOLLOWUP_ORDER.get(intent, [])
    for field in required:
        value = context.get(field)
        if value is None or value == "":
            return {
                "need_follow_up": True,
                "missing_field": field,
                "question": FOLLOWUP_QUESTION[field],
            }
    return {
        "need_follow_up": False,
        "missing_field": None,
        "question": None,
    }


def diagnose_from_tool(intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
    followup = minimal_followup(intent, context)
    if followup["need_follow_up"]:
        return {"intent": intent, "followup": followup, "diagnosis": None}

    if intent == "kyb":
        result = p0_tools.get_kyb_status(
            user_id=context["user_id"],
            requester_user_id=context.get("requester_user_id"),
        )
        if result["status_code"] != "OK":
            return {"intent": intent, "followup": followup, "tool_result": result, "diagnosis": None}
        diagnosis = diagnose_kyb(result["data"])
        return {"intent": intent, "followup": followup, "tool_result": result, "diagnosis": diagnosis}

    if intent == "withdraw":
        result = p0_tools.get_withdraw_status(
            user_id=context["user_id"],
            requester_user_id=context.get("requester_user_id"),
            filters={"asset": context.get("asset"), "network": context.get("network")},
        )
        if result["status_code"] != "OK" or not result["data"].get("results"):
            return {"intent": intent, "followup": followup, "tool_result": result, "diagnosis": None}
        diagnosis = diagnose_withdraw(result["data"]["results"][0])
        return {"intent": intent, "followup": followup, "tool_result": result, "diagnosis": diagnosis}

    if intent == "wallet":
        result = p0_tools.get_wallet_network_status(
            asset=context["asset"],
            network=context["network"],
            requester_user_id=context.get("requester_user_id"),
        )
        if result["status_code"] != "OK":
            return {"intent": intent, "followup": followup, "tool_result": result, "diagnosis": None}
        diagnosis = diagnose_wallet(result["data"])
        return {"intent": intent, "followup": followup, "tool_result": result, "diagnosis": diagnosis}

    if intent == "kb":
        result = p0_tools.search_kb(query=context["query"], context=context.get("kb_context"))
        return {"intent": intent, "followup": followup, "tool_result": result, "diagnosis": None}

    return {
        "intent": intent,
        "followup": followup,
        "tool_result": None,
        "diagnosis": None,
        "message": "unsupported intent",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="P0 rules engine")
    parser.add_argument("intent", choices=["kyb", "withdraw", "wallet", "kb"])
    parser.add_argument("--context", default="{}", help="JSON string")
    args = parser.parse_args()
    context = json.loads(args.context or "{}")
    result = diagnose_from_tool(args.intent, context)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

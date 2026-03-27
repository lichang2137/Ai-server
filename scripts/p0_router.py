#!/usr/bin/env python3
"""P0 intent router with response template and escalation hints."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from p0_rules import diagnose_from_tool


INTENT_HINTS = {
    "withdraw": [
        "withdraw",
        "withdrawal",
        "提币",
        "提现",
        "没到账",
        "未到账",
        "txid",
    ],
    "wallet": [
        "wallet",
        "network",
        "cosmos",
        "trc20",
        "erc20",
        "maintenance",
        "充值",
        "提币开关",
        "能不能充",
        "能不能提",
    ],
    "kyb": [
        "kyb",
        "kyc",
        "verification",
        "审核",
        "补件",
        "驳回",
    ],
}

HIGH_RISK_HINTS = [
    "hacked",
    "stolen",
    "scam",
    "fraud",
    "security incident",
    "盗",
    "被骗",
    "冻结",
    "封禁",
]


def detect_intent(user_text: str) -> str:
    text = (user_text or "").lower()
    # Prefer wallet status intent if network cues are present.
    if any(k in text for k in ["network", "cosmos", "trc20", "erc20", "maintenance", "能不能提", "能不能充"]):
        return "wallet"

    best_intent = "kb"
    best_score = 0
    for intent, hints in INTENT_HINTS.items():
        score = sum(1 for h in hints if h.lower() in text)
        if score > best_score:
            best_score = score
            best_intent = intent
    if best_score > 0:
        return best_intent
    return "kb"


def _is_high_risk_text(user_text: str) -> bool:
    text = (user_text or "").lower()
    return any(h in text for h in HIGH_RISK_HINTS)


def _build_evidence(tool_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not tool_result:
        return []
    data = tool_result.get("data", {})
    out: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list):
            for row in data["results"][:3]:
                out.append(
                    {
                        "type": "knowledge_or_status",
                        "source_url": row.get("source_url"),
                        "summary": row.get("title") or row.get("internal_status") or "record",
                    }
                )
        else:
            out.append({"type": "status_snapshot", "summary": json.dumps(data, ensure_ascii=False)[:300]})
    return out


def _format_followup_message(followup: Dict[str, Any]) -> str:
    if not followup:
        return "Please provide more context so I can continue."
    return followup.get("question") or "Please provide one missing field to continue."


def _compose_template(intent: str, user_text: str, result: Dict[str, Any]) -> Dict[str, Any]:
    followup = result.get("followup", {})
    diagnosis = result.get("diagnosis")
    tool_result = result.get("tool_result")
    high_risk = _is_high_risk_text(user_text)

    escalation = {
        "should_escalate": high_risk,
        "reason": "High-risk security scenario detected from user text." if high_risk else None,
    }

    if followup.get("need_follow_up"):
        return {
            "intent": intent,
            "conclusion": "Need one more detail before diagnosis.",
            "evidence": [],
            "next_action": _format_followup_message(followup),
            "escalation": escalation,
        }

    if diagnosis:
        should_escalate = bool(diagnosis.get("should_escalate")) or high_risk
        escalation = {
            "should_escalate": should_escalate,
            "reason": diagnosis.get("diagnosis") if should_escalate else None,
        }
        return {
            "intent": intent,
            "conclusion": diagnosis.get("diagnosis") or "Diagnosis completed.",
            "evidence": _build_evidence(tool_result),
            "next_action": diagnosis.get("next_action") or "Follow the support guidance.",
            "escalation": escalation,
        }

    if tool_result and tool_result.get("status_code") == "ERROR":
        return {
            "intent": intent,
            "conclusion": "Tool query failed.",
            "evidence": [{"type": "error", "summary": tool_result.get("error_code")}],
            "next_action": tool_result.get("message") or "Retry or contact support.",
            "escalation": {"should_escalate": True, "reason": "Tool error on user query path."},
        }

    return {
        "intent": intent,
        "conclusion": "Query completed.",
        "evidence": _build_evidence(tool_result),
        "next_action": "If this does not solve your issue, provide order_id/txid for deeper check.",
        "escalation": escalation,
    }


def route(user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    intent = detect_intent(user_text)
    result = diagnose_from_tool(intent, context)
    response = _compose_template(intent, user_text, result)
    return {
        "intent": intent,
        "user_text": user_text,
        "result": result,
        "response_template": response,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="P0 intent router")
    parser.add_argument("--text", required=True, help="User message")
    parser.add_argument("--context", default="{}", help="JSON string")
    args = parser.parse_args()
    context = json.loads(args.context or "{}")
    print(json.dumps(route(args.text, context), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

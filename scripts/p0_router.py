#!/usr/bin/env python3
"""Minimal P0 intent router.

Maps user utterance to one of the first-batch intents and executes
the Stage-2 diagnosis path.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from p0_rules import diagnose_from_tool


INTENT_HINTS = {
    "withdraw": ["withdraw", "提币", "提现", "没到账", "未到账", "txid"],
    "wallet": ["network", "充值", "提币开关", "维护", "wallet status", "能不能充", "能不能提"],
    "kyb": ["kyb", "kyc", "认证", "审核", "补件", "驳回"],
}


def detect_intent(user_text: str) -> str:
    text = (user_text or "").lower()
    for intent, hints in INTENT_HINTS.items():
        if any(h.lower() in text for h in hints):
            return intent
    return "kb"


def route(user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    intent = detect_intent(user_text)
    result = diagnose_from_tool(intent, context)
    return {
        "intent": intent,
        "user_text": user_text,
        "result": result,
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

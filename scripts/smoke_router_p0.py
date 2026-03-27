#!/usr/bin/env python3
"""Smoke tests for P0 router with response template."""

from __future__ import annotations

import json

from p0_router import detect_intent, route


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    cases = []

    _assert(detect_intent("my withdrawal has not arrived") == "withdraw", "withdraw intent expected")
    cases.append("intent_withdraw")

    _assert(detect_intent("can I withdraw on atom cosmos now") == "wallet", "wallet intent expected")
    cases.append("intent_wallet")

    _assert(detect_intent("why was my KYB rejected") == "kyb", "kyb intent expected")
    cases.append("intent_kyb")

    _assert(detect_intent("how are fees calculated") == "kb", "kb fallback expected")
    cases.append("intent_kb")

    out = route("my withdrawal is not credited", {"user_id": "uid_10001"})
    _assert(out["intent"] == "withdraw", "route intent mismatch")
    _assert(out["result"]["followup"]["need_follow_up"] is True, "follow-up expected when asset missing")
    _assert("response_template" in out, "response_template expected")
    cases.append("route_followup_template")

    risk = route("my account is hacked and funds stolen", {"user_id": "uid_10001"})
    _assert(risk["response_template"]["escalation"]["should_escalate"] is True, "high-risk escalation expected")
    cases.append("route_high_risk_escalation")

    print(json.dumps({"smoke": "passed", "cases": cases}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

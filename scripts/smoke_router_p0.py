#!/usr/bin/env python3
"""Smoke tests for minimal P0 router."""

from __future__ import annotations

import json

from p0_router import detect_intent, route


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    cases = []

    _assert(detect_intent("我提币还没到账") == "withdraw", "withdraw intent expected")
    cases.append("intent_withdraw")

    _assert(detect_intent("ATOM Cosmos 现在能不能提") == "wallet", "wallet intent expected")
    cases.append("intent_wallet")

    _assert(detect_intent("我的KYB为什么被驳回") == "kyb", "kyb intent expected")
    cases.append("intent_kyb")

    _assert(detect_intent("手续费怎么计算") == "kb", "kb fallback expected")
    cases.append("intent_kb")

    out = route("我提币没到账", {"user_id": "uid_10001"})
    _assert(out["intent"] == "withdraw", "route intent mismatch")
    _assert(out["result"]["followup"]["need_follow_up"] is True, "follow-up expected when asset missing")
    cases.append("route_followup")

    print(json.dumps({"smoke": "passed", "cases": cases}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

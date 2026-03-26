#!/usr/bin/env python3
"""Smoke tests for P0 rule engine skeleton."""

from __future__ import annotations

import json

from p0_rules import diagnose_from_tool, minimal_followup


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    cases = []

    fu = minimal_followup("withdraw", {"user_id": "uid_10001"})
    _assert(fu["need_follow_up"] is True, "withdraw should ask asset first")
    _assert(fu["missing_field"] == "asset", "missing asset expected")
    cases.append("followup_withdraw_asset")

    k = diagnose_from_tool("kyb", {"user_id": "uid_10002", "requester_user_id": "uid_10002"})
    _assert(k["diagnosis"] is not None, "kyb diagnosis expected")
    _assert(k["diagnosis"]["matched_rule_id"] == "kyb_material_missing", "kyb rule mismatch")
    cases.append("diagnose_kyb_material_missing")

    w = diagnose_from_tool(
        "withdraw",
        {"user_id": "uid_10001", "asset": "USDT", "requester_user_id": "uid_10001"},
    )
    _assert(w["diagnosis"] is not None, "withdraw diagnosis expected")
    _assert(w["diagnosis"]["matched_rule_id"] == "wd_broadcasted_confirming", "withdraw rule mismatch")
    cases.append("diagnose_withdraw_broadcasted")

    wallet = diagnose_from_tool("wallet", {"asset": "ATOM", "network": "Cosmos"})
    _assert(wallet["diagnosis"] is not None, "wallet diagnosis expected")
    _assert(wallet["diagnosis"]["matched_rule_id"] == "wallet_withdraw_paused", "wallet rule mismatch")
    cases.append("diagnose_wallet_paused")

    print(json.dumps({"smoke": "passed", "cases": cases}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

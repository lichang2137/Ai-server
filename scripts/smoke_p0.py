#!/usr/bin/env python3
"""P0 smoke tests for adapter layer."""

from __future__ import annotations

import json
import sys

from p0_tools import (
    get_kyb_status,
    get_wallet_network_status,
    get_withdraw_status,
    search_kb,
)


def assert_ok(result, label: str) -> None:
    if result.get("status_code") != "OK":
        raise AssertionError(f"{label} expected OK, got: {json.dumps(result, ensure_ascii=False)}")


def assert_error(result, code: str, label: str) -> None:
    if result.get("status_code") != "ERROR" or result.get("error_code") != code:
        raise AssertionError(
            f"{label} expected ERROR/{code}, got: {json.dumps(result, ensure_ascii=False)}"
        )


def main() -> int:
    cases = []

    r1 = search_kb("KYB", {"platform": "okx"})
    assert_ok(r1, "search_kb hit")
    cases.append("search_kb hit")

    r2 = search_kb("definitely_not_exist_keyword")
    assert_ok(r2, "search_kb empty")
    assert r2["data"]["results"] == []
    cases.append("search_kb empty")

    r3 = get_kyb_status("uid_10002", requester_user_id="uid_10002")
    assert_ok(r3, "get_kyb_status self")
    cases.append("get_kyb_status self")

    r4 = get_kyb_status("uid_10002", requester_user_id="uid_10001")
    assert_error(r4, "TOOL_ERROR_PERMISSION_DENIED", "get_kyb_status permission")
    cases.append("get_kyb_status permission")

    r5 = get_withdraw_status("uid_10001", filters={"asset": "USDT"}, requester_user_id="uid_10001")
    assert_ok(r5, "get_withdraw_status filtered")
    assert len(r5["data"]["results"]) >= 1
    cases.append("get_withdraw_status filtered")

    r6 = get_withdraw_status("uid_10001", filters={"order_id": "not_exist"}, requester_user_id="uid_10001")
    assert_ok(r6, "get_withdraw_status empty")
    assert r6["data"]["results"] == []
    cases.append("get_withdraw_status empty")

    r7 = get_wallet_network_status("ATOM", "Cosmos")
    assert_ok(r7, "get_wallet_network_status")
    cases.append("get_wallet_network_status")

    print(json.dumps({"smoke": "passed", "cases": cases}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"smoke": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        raise

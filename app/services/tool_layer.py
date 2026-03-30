from __future__ import annotations

import re
from typing import Any

from app.schemas import ToolExecutionResult
from app.services.adapters.base import ToolNotConfigured
from app.services.knowledge import search_platform_kb
from app.services.platform_registry import PlatformPackage


def _infer_status_tool(text: str) -> str:
    lowered = (text or "").lower()
    if any(token in lowered for token in ["kyb", "kyc", "认证", "审核", "补件", "驳回", "企业认证"]):
        return "get_kyb_status"
    if any(token in lowered for token in ["提现", "withdraw"]):
        return "get_withdraw_status"
    if any(token in lowered for token in ["充币", "未到账", "deposit"]):
        return "get_deposit_status"
    if any(token in lowered for token in ["钱包", "network", "maintenance"]):
        return "get_wallet_network_status"
    return "search_platform_kb"


def _extract_filters(text: str) -> dict[str, Any]:
    lowered = (text or "").lower()
    filters: dict[str, Any] = {}

    asset_match = re.search(r"\b([A-Z]{2,10})\b", text or "")
    if asset_match:
        filters["asset"] = asset_match.group(1)
    else:
        for asset in ("BTC", "ETH", "USDT", "USDC", "SOL", "XRP", "OKB"):
            if asset.lower() in lowered:
                filters["asset"] = asset
                break

    network_map = {
        "trc20": "TRC20",
        "erc20": "ERC20",
        "bep20": "BEP20",
        "arbitrum": "Arbitrum",
        "polygon": "Polygon",
        "solana": "Solana",
        "tron": "TRC20",
        "optimism": "Optimism",
    }
    for key, value in network_map.items():
        if key in lowered:
            filters["network"] = value
            break

    txid_match = re.search(r"\b([A-Fa-f0-9]{16,})\b", text or "")
    if txid_match:
        filters["txid"] = txid_match.group(1)

    return filters


def _documentation_fallback(
    package: PlatformPackage,
    text: str,
    tool_name: str,
    warning: str,
) -> ToolExecutionResult:
    hits = search_platform_kb(package, text, limit=3)
    evidence = [f"{hit.title} | {hit.source_url}" for hit in hits]
    if warning:
        evidence.insert(0, warning)
    return ToolExecutionResult(
        tool_name=tool_name,
        source_mode="documentation_fallback",
        degraded=True,
        data={"results": [hit.model_dump() for hit in hits]},
        evidence=evidence,
        warning=warning,
        handoff_required=False,
    )


def call_status_tool(package: PlatformPackage, text: str, platform_user_id: str | None, context: dict[str, Any]) -> ToolExecutionResult:
    tool_name = _infer_status_tool(text)
    filters = _extract_filters(text)
    adapter = package.adapter
    if tool_name == "search_platform_kb":
        return _documentation_fallback(package, text, tool_name, "No live status tool matched the request.")
    if adapter is None:
        return _documentation_fallback(package, text, tool_name, "Live status adapter is not configured for this platform package.")

    try:
        if tool_name == "get_kyb_status":
            if not platform_user_id:
                raise ToolNotConfigured("platform_user_id is required for KYB status")
            result = adapter.get_kyb_status(platform_user_id, context)
        elif tool_name == "get_withdraw_status":
            if not platform_user_id:
                raise ToolNotConfigured("platform_user_id is required for withdraw status")
            result = adapter.get_withdraw_status(platform_user_id, filters, context)
        elif tool_name == "get_deposit_status":
            if not platform_user_id:
                raise ToolNotConfigured("platform_user_id is required for deposit status")
            result = adapter.get_deposit_status(platform_user_id, filters, context)
        else:
            result = adapter.get_wallet_network_status(filters, context)
        return ToolExecutionResult(
            tool_name=tool_name,
            source_mode=result.source_mode,
            degraded=result.degraded,
            data=result.data,
            evidence=result.evidence,
            warning=None,
            handoff_required=tool_name == "get_kyb_status" and result.data.get("current_status") in {"rejected", "expired"},
        )
    except ToolNotConfigured as exc:
        return _documentation_fallback(package, text, tool_name, str(exc))
    except Exception as exc:
        return _documentation_fallback(package, text, tool_name, f"Adapter error: {exc.__class__.__name__}")

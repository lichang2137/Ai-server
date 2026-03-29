from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ToolNotConfigured(Exception):
    """Raised when a platform package does not provide a live tool."""


@dataclass
class AdapterResult:
    data: dict[str, Any]
    evidence: list[str]
    source_mode: str = "api"
    degraded: bool = False


class BasePlatformAdapter:
    platform_id: str

    def __init__(self, platform_id: str):
        self.platform_id = platform_id

    def get_kyb_status(self, user_id: str, context: dict[str, Any]) -> AdapterResult:
        raise ToolNotConfigured("KYB status adapter is not configured")

    def get_deposit_status(self, user_id: str, filters: dict[str, Any], context: dict[str, Any]) -> AdapterResult:
        raise ToolNotConfigured("Deposit status adapter is not configured")

    def get_withdraw_status(self, user_id: str, filters: dict[str, Any], context: dict[str, Any]) -> AdapterResult:
        raise ToolNotConfigured("Withdraw status adapter is not configured")

    def get_wallet_network_status(self, filters: dict[str, Any], context: dict[str, Any]) -> AdapterResult:
        raise ToolNotConfigured("Wallet status adapter is not configured")

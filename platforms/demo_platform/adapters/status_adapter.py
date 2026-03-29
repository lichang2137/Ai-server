from __future__ import annotations

from app.services.adapters.base import AdapterResult, BasePlatformAdapter
from scripts import mock_tools


class DemoPlatformAdapter(BasePlatformAdapter):
    def get_kyb_status(self, user_id: str, context: dict) -> AdapterResult:
        result = mock_tools.get_kyb_status(user_id)
        if "error" in result:
            return AdapterResult(data={"error": result["error"], "message": result.get("message")}, evidence=["mock KYB status not found"], degraded=True)
        record = result["kyb_status"]
        evidence = [f"mock status source for {record['user_id']}", f"status={record['current_status']}"]
        return AdapterResult(data=record, evidence=evidence)

    def get_deposit_status(self, user_id: str, filters: dict, context: dict) -> AdapterResult:
        result = mock_tools.get_deposit_status(user_id, asset=filters.get("asset"), network=filters.get("network"))
        evidence = [f"mock deposit records for {user_id}"]
        return AdapterResult(data=result, evidence=evidence)

    def get_withdraw_status(self, user_id: str, filters: dict, context: dict) -> AdapterResult:
        result = mock_tools.get_withdraw_status(user_id, asset=filters.get("asset"), network=filters.get("network"))
        evidence = [f"mock withdraw records for {user_id}"]
        return AdapterResult(data=result, evidence=evidence)

    def get_wallet_network_status(self, filters: dict, context: dict) -> AdapterResult:
        asset = filters.get("asset") or "USDT"
        network = filters.get("network") or "TRC20"
        result = mock_tools.get_wallet_network_status(asset, network)
        evidence = [f"mock wallet status for {asset}/{network}"]
        return AdapterResult(data=result, evidence=evidence)


def build_adapter(platform_id: str) -> DemoPlatformAdapter:
    return DemoPlatformAdapter(platform_id)

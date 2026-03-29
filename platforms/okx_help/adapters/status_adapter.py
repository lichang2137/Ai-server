from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.config import settings
from app.services.adapters.base import AdapterResult, BasePlatformAdapter, ToolNotConfigured
from app.services.adapters.feishu_bitable import FeishuBitableClient


def _coerce_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        flattened = [_coerce_scalar(item) for item in value]
        cleaned = [item for item in flattened if item]
        return ", ".join(cleaned) if cleaned else None
    if isinstance(value, dict):
        for key in ("text", "name", "value"):
            if value.get(key):
                return str(value[key]).strip()
        return None
    return str(value).strip()


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            coerced = _coerce_scalar(item)
            if coerced:
                result.append(coerced)
        return result
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    coerced = _coerce_scalar(value)
    return [coerced] if coerced else []


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "enabled", "on"}:
            return True
        if normalized in {"false", "no", "0", "disabled", "off"}:
            return False
    return None


def _parse_time(value: Any) -> tuple[int, str]:
    if value is None:
        return 0, ""
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000.0
        return int(timestamp), str(value)
    text = _coerce_scalar(value)
    if not text:
        return 0, ""
    if text.isdigit():
        timestamp = float(text)
        if timestamp > 10_000_000_000:
            timestamp /= 1000.0
        return int(timestamp), text
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return int(dt.timestamp()), text
    except ValueError:
        return 0, text


class OKXFeishuBitableAdapter(BasePlatformAdapter):
    def __init__(self, platform_id: str, schema_path: Path):
        super().__init__(platform_id)
        self.schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.app_token = os.getenv("OKX_FEISHU_BITABLE_APP_TOKEN")
        self.table_ids = {
            "verification_status": os.getenv("OKX_FEISHU_VERIFICATION_TABLE_ID"),
            "deposit_status": os.getenv("OKX_FEISHU_DEPOSIT_TABLE_ID"),
            "withdraw_status": os.getenv("OKX_FEISHU_WITHDRAW_TABLE_ID"),
            "network_status": os.getenv("OKX_FEISHU_NETWORK_TABLE_ID"),
            "support_tickets": os.getenv("OKX_FEISHU_TICKET_TABLE_ID"),
        }
        self.client: FeishuBitableClient | None = None
        if self.app_id and self.app_secret and self.app_token:
            self.client = FeishuBitableClient(self.app_id, self.app_secret, self.app_token, settings.request_timeout_s)

    def _require_client(self) -> FeishuBitableClient:
        if self.client is None:
            raise ToolNotConfigured("Feishu Bitable credentials are not configured")
        return self.client

    def _require_table(self, key: str) -> str:
        table_id = self.table_ids.get(key)
        if not table_id:
            raise ToolNotConfigured(f"Feishu Bitable table is not configured for {key}")
        return table_id

    def _list_rows(self, key: str) -> list[dict[str, Any]]:
        client = self._require_client()
        table_id = self._require_table(key)
        return client.list_records(table_id)

    def _active_and_sorted(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def sort_key(row: dict[str, Any]) -> tuple[int, str]:
            fields = row.get("fields", {})
            return _parse_time(fields.get("updated_at"))

        filtered = [row for row in rows if _coerce_bool(row.get("fields", {}).get("is_active")) is not False]
        return sorted(filtered, key=sort_key, reverse=True)

    def _match_user_rows(self, rows: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
        matched = []
        for row in self._active_and_sorted(rows):
            fields = row.get("fields", {})
            if _coerce_scalar(fields.get("user_id")) == user_id:
                matched.append(row)
        return matched

    def _evidence(self, table_key: str, row: dict[str, Any], extra: list[str] | None = None) -> list[str]:
        fields = row.get("fields", {})
        evidence = [
            f"feishu_table={table_key}",
            f"user_id={_coerce_scalar(fields.get('user_id')) or '-'}",
            f"updated_at={_coerce_scalar(fields.get('updated_at')) or '-'}",
        ]
        if extra:
            evidence.extend(extra)
        return evidence

    def get_kyb_status(self, user_id: str, context: dict[str, Any]) -> AdapterResult:
        rows = self._match_user_rows(self._list_rows("verification_status"), user_id)
        if not rows:
            raise ToolNotConfigured("No verification status row was found in Feishu Bitable")
        fields = rows[0]["fields"]
        data = {
            "user_id": user_id,
            "verification_scope": _coerce_scalar(fields.get("verification_scope")) or "institutional_kyb",
            "current_status": _coerce_scalar(fields.get("current_status")),
            "missing_items": _coerce_list(fields.get("missing_items")),
            "rejection_reason": _coerce_scalar(fields.get("rejection_reason")),
            "next_action": _coerce_scalar(fields.get("next_action")),
            "eta": _coerce_scalar(fields.get("eta")),
            "case_id": _coerce_scalar(fields.get("case_id")),
        }
        return AdapterResult(
            data=data,
            evidence=self._evidence("verification_status", rows[0], [f"current_status={data['current_status'] or '-'}"]),
        )

    def get_deposit_status(self, user_id: str, filters: dict[str, Any], context: dict[str, Any]) -> AdapterResult:
        rows = self._match_user_rows(self._list_rows("deposit_status"), user_id)
        asset = filters.get("asset")
        network = filters.get("network")
        txid = filters.get("txid")
        for row in rows:
            fields = row["fields"]
            if asset and (_coerce_scalar(fields.get("asset")) or "").upper() != asset.upper():
                continue
            if network and (_coerce_scalar(fields.get("network")) or "").lower() != network.lower():
                continue
            if txid and (_coerce_scalar(fields.get("txid")) or "").lower() != txid.lower():
                continue
            data = {
                "user_id": user_id,
                "asset": _coerce_scalar(fields.get("asset")),
                "network": _coerce_scalar(fields.get("network")),
                "status": _coerce_scalar(fields.get("status")),
                "txid": _coerce_scalar(fields.get("txid")),
                "confirmations": _coerce_scalar(fields.get("confirmations")),
                "next_action": _coerce_scalar(fields.get("next_action")),
            }
            return AdapterResult(data=data, evidence=self._evidence("deposit_status", row, [f"status={data['status'] or '-'}"]))
        raise ToolNotConfigured("No matching deposit status row was found in Feishu Bitable")

    def get_withdraw_status(self, user_id: str, filters: dict[str, Any], context: dict[str, Any]) -> AdapterResult:
        rows = self._match_user_rows(self._list_rows("withdraw_status"), user_id)
        asset = filters.get("asset")
        network = filters.get("network")
        txid = filters.get("txid")
        for row in rows:
            fields = row["fields"]
            if asset and (_coerce_scalar(fields.get("asset")) or "").upper() != asset.upper():
                continue
            if network and (_coerce_scalar(fields.get("network")) or "").lower() != network.lower():
                continue
            if txid and (_coerce_scalar(fields.get("txid")) or "").lower() != txid.lower():
                continue
            data = {
                "user_id": user_id,
                "asset": _coerce_scalar(fields.get("asset")),
                "network": _coerce_scalar(fields.get("network")),
                "status": _coerce_scalar(fields.get("status")),
                "txid": _coerce_scalar(fields.get("txid")),
                "review_reason": _coerce_scalar(fields.get("review_reason")),
                "next_action": _coerce_scalar(fields.get("next_action")),
            }
            return AdapterResult(data=data, evidence=self._evidence("withdraw_status", row, [f"status={data['status'] or '-'}"]))
        raise ToolNotConfigured("No matching withdraw status row was found in Feishu Bitable")

    def get_wallet_network_status(self, filters: dict[str, Any], context: dict[str, Any]) -> AdapterResult:
        rows = self._active_and_sorted(self._list_rows("network_status"))
        asset = filters.get("asset")
        network = filters.get("network")
        for row in rows:
            fields = row["fields"]
            if asset and (_coerce_scalar(fields.get("asset")) or "").upper() != asset.upper():
                continue
            if network and (_coerce_scalar(fields.get("network")) or "").lower() != network.lower():
                continue
            data = {
                "asset": _coerce_scalar(fields.get("asset")),
                "network": _coerce_scalar(fields.get("network")),
                "deposit_enabled": _coerce_bool(fields.get("deposit_enabled")),
                "withdraw_enabled": _coerce_bool(fields.get("withdraw_enabled")),
                "announcement_url": _coerce_scalar(fields.get("announcement_url")),
                "eta": _coerce_scalar(fields.get("eta")),
                "current_status_note": _coerce_scalar(fields.get("current_status_note")),
            }
            return AdapterResult(
                data=data,
                evidence=self._evidence(
                    "network_status",
                    row,
                    [f"deposit_enabled={data['deposit_enabled']}", f"withdraw_enabled={data['withdraw_enabled']}"],
                ),
            )
        raise ToolNotConfigured("No matching network status row was found in Feishu Bitable")


def build_adapter(platform_id: str) -> OKXFeishuBitableAdapter:
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "feishu_bitable_tables.yaml"
    return OKXFeishuBitableAdapter(platform_id, schema_path)

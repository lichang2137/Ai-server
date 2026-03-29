from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


class FeishuBitableClient:
    def __init__(self, app_id: str, app_secret: str, app_token: str, timeout_s: float = 20.0):
        self.app_id = app_id
        self.app_secret = app_secret
        self.app_token = app_token
        self.timeout_s = timeout_s
        self._tenant_access_token: str | None = None
        self._token_expire_at: datetime | None = None

    def _get_tenant_access_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._tenant_access_token and self._token_expire_at and now < self._token_expire_at:
            return self._tenant_access_token

        response = httpx.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"Feishu auth failed: {payload.get('msg', 'unknown error')}")
        self._tenant_access_token = payload["tenant_access_token"]
        expires_in = int(payload.get("expire", 7200))
        self._token_expire_at = now + timedelta(seconds=max(expires_in - 60, 60))
        return self._tenant_access_token

    def list_records(self, table_id: str, page_size: int = 500) -> list[dict[str, Any]]:
        token = self._get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        items: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            params: dict[str, Any] = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            response = httpx.get(
                f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records",
                params=params,
                headers=headers,
                timeout=self.timeout_s,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(f"Feishu bitable query failed: {payload.get('msg', 'unknown error')}")
            data = payload.get("data", {})
            items.extend(data.get("items", []))
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break

        return items

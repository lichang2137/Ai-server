from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import yaml


FIELD_TYPE_MAP: dict[str, tuple[int, str]] = {
    "text": (1, "Text"),
    "long_text": (1, "Text"),
    "multi_select_or_text": (1, "Text"),
    "single_select": (3, "SingleSelect"),
    "datetime": (5, "DateTime"),
    "checkbox": (7, "Checkbox"),
    "url": (15, "Url"),
}

DEFAULT_SELECT_COLORS = [0, 1, 2, 3, 4, 5, 6, 7]


class FeishuSetupClient:
    def __init__(self, app_id: str, app_secret: str, timeout_s: float = 60.0):
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout_s = timeout_s
        self._tenant_access_token: str | None = None

    def _headers(self) -> dict[str, str]:
        if self._tenant_access_token is None:
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
        return {"Authorization": f"Bearer {self._tenant_access_token}"}

    def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = httpx.request(method, url, headers=self._headers(), timeout=self.timeout_s, **kwargs)
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") != 0:
                    raise RuntimeError(
                        f"{method} {url} failed: {payload.get('msg', 'unknown error')} ({payload.get('code')})"
                    )
                return payload
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt == 2:
                    break
                time.sleep(1.5 * (attempt + 1))
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"{method} {url} failed without a response payload")

    def create_app(self, name: str, time_zone: str = "Asia/Shanghai") -> dict[str, Any]:
        return self._request(
            "POST",
            "https://open.feishu.cn/open-apis/bitable/v1/apps",
            json={"name": name, "time_zone": time_zone},
        )

    def create_table(self, app_token: str, table: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables",
            json={"table": table},
        )

    def batch_create_records(self, app_token: str, table_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        return self._request(
            "POST",
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
            params={"client_token": str(uuid4())},
            json={"records": records},
        )


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _field_definition(field_name: str, field_spec: dict[str, Any]) -> dict[str, Any]:
    field_type = field_spec["type"]
    if field_type not in FIELD_TYPE_MAP:
        raise ValueError(f"Unsupported field type for Feishu Bitable: {field_type}")
    type_id, ui_type = FIELD_TYPE_MAP[field_type]
    payload: dict[str, Any] = {"field_name": field_name, "type": type_id, "ui_type": ui_type}
    property_payload: dict[str, Any] = {}
    if field_type == "single_select":
        options = field_spec.get("options", [])
        property_payload["options"] = [
            {"name": option, "color": DEFAULT_SELECT_COLORS[index % len(DEFAULT_SELECT_COLORS)]}
            for index, option in enumerate(options)
        ]
    if field_type == "datetime":
        property_payload["date_formatter"] = "yyyy-MM-dd HH:mm"
    if property_payload:
        payload["property"] = property_payload
    return payload


def _normalize_record(fields: dict[str, Any], field_specs: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in fields.items():
        if value is None:
            continue
        field_type = field_specs.get(key, {}).get("type")
        if isinstance(value, datetime):
            normalized[key] = int(value.timestamp() * 1000)
        elif isinstance(value, list) and field_type in {"text", "long_text", "multi_select_or_text"}:
            normalized[key] = ", ".join(str(item) for item in value if item is not None)
        else:
            normalized[key] = value
    return normalized


def build_tables(schema: dict[str, Any], seed: dict[str, Any], include_support_tickets: bool) -> list[dict[str, Any]]:
    tables = []
    for table_name, table_spec in schema["tables"].items():
        if table_name == "support_tickets" and not include_support_tickets:
            continue
        tables.append(
            {
                "name": table_name,
                "payload": {
                    "name": table_name,
                    "default_view_name": "All Records",
                    "fields": [
                        _field_definition(field_name, field_spec)
                        for field_name, field_spec in table_spec["fields"].items()
                    ],
                },
                "seed_rows": seed.get(table_name, []),
            }
        )
    return tables


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the OKX Feishu Bitable app and standard tables.")
    parser.add_argument("--app-id", default=os.getenv("FEISHU_APP_ID"))
    parser.add_argument("--app-secret", default=os.getenv("FEISHU_APP_SECRET"))
    parser.add_argument("--schema", default=str(Path("platforms/okx_help/schemas/feishu_bitable_tables.yaml")))
    parser.add_argument("--seed", default=str(Path("platforms/okx_help/examples/feishu_bitable_seed.yaml")))
    parser.add_argument("--name", default=f"OKX Support Live Status {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    parser.add_argument("--include-support-tickets", action="store_true")
    parser.add_argument("--output", default=str(Path("var/okx_feishu_bitable_runtime.json")))
    args = parser.parse_args()

    if not args.app_id or not args.app_secret:
        raise SystemExit("FEISHU_APP_ID and FEISHU_APP_SECRET are required.")

    schema = _load_yaml(Path(args.schema))
    seed = _load_yaml(Path(args.seed))
    tables = build_tables(schema, seed, include_support_tickets=args.include_support_tickets)

    client = FeishuSetupClient(args.app_id, args.app_secret)
    app_payload = client.create_app(args.name)
    app_data = app_payload["data"]["app"]
    app_token = app_data["app_token"]

    result: dict[str, Any] = {
        "app": {
            "name": app_data.get("name"),
            "app_token": app_token,
            "url": app_data.get("url"),
            "time_zone": app_data.get("time_zone"),
        },
        "tables": {},
    }

    env_lines = [f"OKX_FEISHU_BITABLE_APP_TOKEN={app_token}"]

    for table in tables:
        created = client.create_table(app_token, table["payload"])
        table_data = created["data"]
        table_id = table_data["table_id"]
        table_name = table["name"]
        created_records = 0
        field_specs = schema["tables"][table_name]["fields"]
        seed_rows = [_normalize_record(row, field_specs) for row in table["seed_rows"]]
        if seed_rows:
            payload_rows = [{"fields": row} for row in seed_rows]
            batch_result = client.batch_create_records(app_token, table_id, payload_rows)
            created_records = len(batch_result["data"].get("records", []))
        result["tables"][table_name] = {
            "table_id": table_id,
            "view_id": table_data.get("default_view_id"),
            "record_count_seeded": created_records,
        }
        env_name = schema["tables"][table_name]["required_env"]
        env_lines.append(f"{env_name}={table_id}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n# Environment")
    for line in env_lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

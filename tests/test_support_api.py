from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

TEST_DB_PATH = Path(f"test_ai_server_framework_{uuid4().hex}.db")
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
os.environ["AI_SERVER_DATABASE_URL"] = f"sqlite:///./{TEST_DB_PATH.name}"
os.environ["AI_SERVER_DEFAULT_PLATFORM"] = "demo_platform"

import pytest
from docx import Document
from fastapi.testclient import TestClient
from PIL import Image
from reportlab.pdfgen import canvas

from app.main import app
from app.services.knowledge import search_platform_kb
from app.services.platform_registry import PlatformRegistry
from app.services.tool_layer import call_status_tool
from platforms.okx_help.adapters.status_adapter import OKXFeishuBitableAdapter


def _write_pdf(path: Path, lines: list[str]) -> None:
    pdf = canvas.Canvas(str(path))
    y = 800
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 20
    pdf.save()


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.save(path)


def _write_png_with_sidecar(path: Path, ocr_text: str) -> None:
    image = Image.new("RGB", (1200, 800), color="white")
    image.save(path)
    Path(f"{path}.ocr.txt").write_text(ocr_text, encoding="utf-8")


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _payload(
    text: str,
    *,
    platform_user_id: str | None = "uid_10002",
    session_id: str = "sess-1",
    attachments: list[dict] | None = None,
) -> dict:
    return {
        "channel": "telegram",
        "channel_user_id": "tg-user-1",
        "session_id": session_id,
        "platform_user_id": platform_user_id,
        "message_id": f"msg-{session_id}-{abs(hash((text, platform_user_id, session_id)))}",
        "text": text,
        "timestamp": "2026-03-28T10:00:00Z",
        "context": {"locale": "zh-CN", "attachments": attachments or []},
    }


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_knowledge_route_returns_source_evidence(client: TestClient) -> None:
    response = client.post("/v1/support/message", json=_payload("What materials are required for KYB onboarding?"))
    body = response.json()
    assert response.status_code == 200
    assert body["route"] == "knowledge_qa"
    assert body["review"]["needed"] is False
    assert any("platform://knowledge/kyb-required-materials" in item for item in body["reply"]["structured"]["evidence"])


def test_status_route_uses_live_adapter_and_handoff_for_rejected_case(client: TestClient) -> None:
    response = client.post(
        "/v1/support/message",
        json=_payload("Why was my KYB rejected?", platform_user_id="uid_10004", session_id="sess-rejected"),
    )
    body = response.json()
    assert response.status_code == 200
    assert body["route"] == "status_diagnosis"
    assert body["handoff"]["needed"] is True
    assert body["handoff"]["summary"]["current_status"] == "rejected"
    assert body["reply"]["structured"]["conclusion"] == "Current KYB status: rejected."


def test_repeated_clarification_loops_auto_handoff(client: TestClient) -> None:
    first = client.post(
        "/v1/support/message",
        json=_payload("Please check my KYB status", platform_user_id=None, session_id="sess-loop"),
    )
    second = client.post(
        "/v1/support/message",
        json=_payload("I still need my KYB status checked", platform_user_id=None, session_id="sess-loop"),
    )
    first_body = first.json()
    second_body = second.json()
    assert first.status_code == 200
    assert first_body["handoff"]["needed"] is False
    assert second.status_code == 200
    assert second_body["handoff"]["needed"] is True
    assert second_body["handoff"]["summary"]["type"] == "followup_required"
    assert "documentation-backed guidance" in second_body["reply"]["structured"]["conclusion"]


def test_security_route_escalates_immediately(client: TestClient) -> None:
    response = client.post("/v1/support/message", json=_payload("My account may be hacked", session_id="sess-sec"))
    body = response.json()
    assert response.status_code == 200
    assert body["route"] == "handoff"
    assert body["handoff"]["needed"] is True
    assert body["handoff"]["summary"]["type"] == "security_or_manual"


def test_kyb_review_processes_pdf_docx_and_image_files(client: TestClient, tmp_path: Path) -> None:
    ci_path = tmp_path / "ci.pdf"
    _write_pdf(
        ci_path,
        [
            "CERTIFICATE OF INCORPORATION",
            "Vista Capital Ltd.",
            "Reg. No. 136466",
            "Issue Date: January 20, 2026",
        ],
    )

    coi_path = tmp_path / "coi.pdf"
    _write_pdf(
        coi_path,
        [
            "CERTIFICATE OF INCUMBENCY",
            "Vista Capital Ltd.",
            "Reg. No. 136466",
            "LI, YANG 50,000 shares",
            "Issue Date: January 20, 2026",
        ],
    )

    passport_path = tmp_path / "passport.docx"
    _write_docx(
        passport_path,
        [
            "Passport",
            "Name: YANG LI",
            "Passport No: EQ6500339",
            "Issue Date: 2026-01-20",
        ],
    )

    onboarding_path = tmp_path / "onboarding_form.docx"
    _write_docx(
        onboarding_path,
        [
            "XCoin Corporate and Institutional Account Application Form",
            "Customer: YANG LI",
            "Passport No: EQ6500339",
            "Vista Capital Ltd.",
            "Appendix 2",
            "YANG LI",
            "100%",
        ],
    )

    poba_path = tmp_path / "water_bill.png"
    _write_png_with_sidecar(
        poba_path,
        "Water bill Name: YANG LI Address: Whampoa Garden Kowloon Issue Date: 2026-01-30",
    )

    attachments = []
    for index, path in enumerate([ci_path, coi_path, passport_path, onboarding_path, poba_path], start=1):
        attachments.append(
            {
                "attachment_id": f"att-{index}",
                "name": path.name,
                "mime_type": {
                    ".pdf": "application/pdf",
                    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ".png": "image/png",
                }[path.suffix],
                "url": str(path),
                "size_bytes": path.stat().st_size,
            }
        )

    response = client.post(
        "/v1/support/message",
        json=_payload("Please review these KYB documents", platform_user_id="uid_10001", session_id="sess-review", attachments=attachments),
    )
    body = response.json()
    assert response.status_code == 200
    assert body["route"] == "kyb_review"
    assert body["review"]["needed"] is True
    assert body["handoff"]["needed"] is True
    assert body["review"]["summary"]["recommendation"]["decision"] == "approve"
    assert any(doc["document_type"] == "COI" for doc in body["review"]["summary"]["documents"])
    assert any(check["check"] == "shareholding_consistency" and check["result"] == "pass" for check in body["review"]["summary"]["cross_checks"])
    assert any(ref["file_name"] == "water_bill.png" for ref in body["handoff"]["summary"]["evidence_refs"])


def test_platform_registry_rejects_incomplete_platform_package(tmp_path: Path) -> None:
    broken_root = tmp_path / "platforms"
    broken_package = broken_root / "broken"
    broken_package.mkdir(parents=True)
    (broken_package / "platform.yaml").write_text(
        "\n".join(
            [
                "id: broken",
                "name: Broken",
                "default_locale: zh-CN",
                "enabled_routes:",
                "  - knowledge_qa",
                "workflow_nodes:",
                "  knowledge_qa:",
                "    - classify",
            ]
        ),
        encoding="utf-8",
    )
    (broken_package / "knowledge").mkdir()
    (broken_package / "schemas").mkdir()
    (broken_package / "prompts").mkdir()
    (broken_package / "examples").mkdir()

    registry = PlatformRegistry(broken_root, "broken")
    with pytest.raises(RuntimeError, match="missing required directories"):
        registry.load()


def test_adapter_error_degrades_to_documentation_fallback(tmp_path: Path) -> None:
    platforms_root = tmp_path / "platforms"
    demo_root = Path("platforms") / "demo_platform"
    error_root = platforms_root / "error_platform"
    shutil.copytree(demo_root, error_root)
    platform_yaml = error_root / "platform.yaml"
    platform_yaml.write_text(platform_yaml.read_text(encoding="utf-8").replace("demo_platform", "error_platform", 1), encoding="utf-8")
    adapter_path = error_root / "adapters" / "status_adapter.py"
    adapter_path.write_text(
        "\n".join(
            [
                "from app.services.adapters.base import BasePlatformAdapter",
                "",
                "class ErrorAdapter(BasePlatformAdapter):",
                "    def get_kyb_status(self, user_id, context):",
                "        raise RuntimeError('boom')",
                "",
                "def build_adapter(platform_id):",
                "    return ErrorAdapter(platform_id)",
            ]
        ),
        encoding="utf-8",
    )

    registry = PlatformRegistry(platforms_root, "error_platform")
    registry.load()
    package = registry.get("error_platform")
    result = call_status_tool(package, "check my KYB status", "uid_10001", {"locale": "zh-CN"})

    assert result.source_mode == "documentation_fallback"
    assert result.degraded is True
    assert result.warning == "Adapter error: RuntimeError"


def test_okx_help_package_supports_cjk_queries() -> None:
    registry = PlatformRegistry(Path("platforms"), "okx_help")
    registry.load()
    package = registry.get("okx_help")

    hits = search_platform_kb(package, "\u4f01\u4e1a\u8ba4\u8bc1\u9700\u8981\u4ec0\u4e48\u6750\u6599", limit=3)

    assert hits
    assert any("\u4f01\u4e1a" in hit.title for hit in hits)


def test_okx_help_status_tool_falls_back_without_feishu_config(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "OKX_FEISHU_BITABLE_APP_TOKEN",
        "OKX_FEISHU_VERIFICATION_TABLE_ID",
        "OKX_FEISHU_DEPOSIT_TABLE_ID",
        "OKX_FEISHU_WITHDRAW_TABLE_ID",
        "OKX_FEISHU_NETWORK_TABLE_ID",
    ):
        monkeypatch.delenv(key, raising=False)

    registry = PlatformRegistry(Path("platforms"), "okx_help")
    registry.load()
    package = registry.get("okx_help")
    result = call_status_tool(package, "\u4f01\u4e1a\u8ba4\u8bc1\u5ba1\u6838\u8fdb\u5ea6", "uid_20001", {"locale": "zh-CN"})

    assert result.source_mode == "documentation_fallback"
    assert result.degraded is True
    assert result.warning == "Feishu Bitable credentials are not configured"


def test_okx_feishu_adapter_maps_verification_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
    monkeypatch.setenv("FEISHU_APP_SECRET", "sec_test")
    monkeypatch.setenv("OKX_FEISHU_BITABLE_APP_TOKEN", "app_test")
    monkeypatch.setenv("OKX_FEISHU_VERIFICATION_TABLE_ID", "tbl_verification")

    def fake_list_records(self, table_id: str, page_size: int = 500) -> list[dict]:
        assert table_id == "tbl_verification"
        return [
            {
                "fields": {
                    "user_id": "uid_30001",
                    "verification_scope": "institutional_kyb",
                    "current_status": "material_missing",
                    "missing_items": ["shareholder_register", "business_address_proof"],
                    "rejection_reason": None,
                    "next_action": "Upload missing documents.",
                    "eta": "1-3 business days",
                    "case_id": "kyb-001",
                    "updated_at": "2026-03-29T20:00:00+08:00",
                    "is_active": True,
                }
            }
        ]

    monkeypatch.setattr("app.services.adapters.feishu_bitable.FeishuBitableClient.list_records", fake_list_records)

    adapter = OKXFeishuBitableAdapter("okx_help", Path("platforms/okx_help/schemas/feishu_bitable_tables.yaml"))
    result = adapter.get_kyb_status("uid_30001", {"locale": "zh-CN"})

    assert result.data["current_status"] == "material_missing"
    assert result.data["missing_items"] == ["shareholder_register", "business_address_proof"]
    assert result.data["case_id"] == "kyb-001"


def test_okx_feishu_adapter_sorts_timestamp_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
    monkeypatch.setenv("FEISHU_APP_SECRET", "sec_test")
    monkeypatch.setenv("OKX_FEISHU_BITABLE_APP_TOKEN", "app_test")
    monkeypatch.setenv("OKX_FEISHU_VERIFICATION_TABLE_ID", "tbl_verification")

    def fake_list_records(self, table_id: str, page_size: int = 500) -> list[dict]:
        assert table_id == "tbl_verification"
        return [
            {
                "fields": {
                    "user_id": "uid_30002",
                    "current_status": "pending_review",
                    "updated_at": 1774807200000,
                    "is_active": True,
                }
            },
            {
                "fields": {
                    "user_id": "uid_30002",
                    "current_status": "approved",
                    "updated_at": 1774800000000,
                    "is_active": True,
                }
            },
        ]

    monkeypatch.setattr("app.services.adapters.feishu_bitable.FeishuBitableClient.list_records", fake_list_records)

    adapter = OKXFeishuBitableAdapter("okx_help", Path("platforms/okx_help/schemas/feishu_bitable_tables.yaml"))
    result = adapter.get_kyb_status("uid_30002", {"locale": "zh-CN"})

    assert result.data["current_status"] == "pending_review"

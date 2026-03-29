from __future__ import annotations

import csv
import json
import textwrap
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = Path(r"C:\Users\26265\Documents\New project\garrytan\artifacts\okx_help")
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "platforms" / "okx_help"

ONBOARDING_SECTIONS = {"faq-verification", "faq-institutional-onboarding"}
ASSET_OPS_SECTIONS = {
    "faq-crypto-deposits",
    "faq-crypto-withdrawals",
    "announcements-deposit-withdrawal-suspension-resumption",
}
SECURITY_SECTIONS = {
    "faq-account-management-and-security",
    "faq-account-and-wallet-safeguard-measures",
    "faq-fraud-prevention",
}
MARKET_ANNOUNCEMENT_SECTIONS = {
    "announcements-new-listings",
    "announcements-delistings",
    "announcements-p2p-trading",
    "announcements-trading-updates",
    "latest-events",
}


def strip_frontmatter(markdown_text: str) -> str:
    if not markdown_text.startswith("---"):
        return markdown_text.strip()
    parts = markdown_text.split("---", 2)
    if len(parts) < 3:
        return markdown_text.strip()
    return parts[2].strip()


def article_path(source_root: Path, row: dict[str, str]) -> Path:
    return source_root / "articles" / row["category_slug"] / row["section_slug"] / f"{row['slug']}.md"


def infer_domain(row: dict[str, str]) -> str:
    category = row["category_slug"]
    section = row["section_slug"]
    title = row["title"]
    if section in ONBOARDING_SECTIONS:
        return "onboarding"
    if section in ASSET_OPS_SECTIONS:
        return "asset_ops"
    if section in SECURITY_SECTIONS or "工单" in title:
        return "account_security"
    if category == "terms-of-agreement":
        return "terms"
    if category == "product-documentation":
        return "trading_rules"
    if section in MARKET_ANNOUNCEMENT_SECTIONS:
        return "market_announcements"
    return "general_support"


def infer_route_hint(row: dict[str, str], domain: str) -> str:
    if domain == "onboarding":
        return "knowledge_qa"
    if domain == "asset_ops":
        return "status_diagnosis"
    if domain == "account_security":
        return "handoff" if "工单" not in row["title"] else "knowledge_qa"
    return "knowledge_qa"


def load_articles(source_root: Path) -> list[dict[str, Any]]:
    index_path = source_root / "article_index.csv"
    articles: list[dict[str, Any]] = []
    with index_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            path = article_path(source_root, row)
            body = strip_frontmatter(path.read_text(encoding="utf-8"))
            domain = infer_domain(row)
            route_hint = infer_route_hint(row, domain)
            articles.append(
                {
                    "id": f"okx-{row['slug']}",
                    "title": row["title"],
                    "content": body,
                    "tags": [
                        row["category_slug"],
                        row["section_slug"],
                        domain,
                        route_hint,
                    ],
                    "source_url": row["url"],
                    "updated_at": row["updated_at"],
                    "publish_time": row["publish_time"],
                    "category": row["category_slug"],
                    "category_title": row["category_title"],
                    "section_slug": row["section_slug"],
                    "section_title": row["section_title"],
                    "domain": domain,
                    "route_hint": route_hint,
                }
            )
    return articles


def write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    lines = [json.dumps(item, ensure_ascii=False) for item in items]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def build_route_rules() -> dict[str, Any]:
    return {
        "section_route_hints": {
            "faq-verification": {"route": "knowledge_qa", "supports_review": True},
            "faq-institutional-onboarding": {"route": "knowledge_qa", "supports_review": True},
            "faq-crypto-deposits": {"route": "status_diagnosis", "tool": "get_deposit_status"},
            "faq-crypto-withdrawals": {"route": "status_diagnosis", "tool": "get_withdraw_status"},
            "announcements-deposit-withdrawal-suspension-resumption": {
                "route": "status_diagnosis",
                "tool": "get_wallet_network_status",
            },
            "faq-account-management-and-security": {"route": "knowledge_qa", "handoff_on_security": True},
            "faq-account-and-wallet-safeguard-measures": {"route": "handoff", "handoff_on_security": True},
            "faq-fraud-prevention": {"route": "handoff", "handoff_on_security": True},
            "terms-of-agreement": {"route": "knowledge_qa"},
            "product-documentation-risk-management": {"route": "knowledge_qa"},
        },
        "handoff_keywords": [
            "盗号",
            "冻结",
            "被骗",
            "安全风险",
            "身份信息被占用",
            "联系客服",
            "工单",
        ],
        "degrade_rules": {
            "status_without_live_adapter": "Return documentation-backed guidance and label the answer as non-realtime.",
            "ticket_queries_without_ticket_api": "Explain how to check the support ticket through OKX help-center guidance.",
        },
    }


def build_work_rules() -> dict[str, Any]:
    return {
        "operational_policies": [
            {
                "id": "one_entity_one_account",
                "applies_to": ["institutional_onboarding"],
                "rule": "One legal entity should operate one account. Duplicate account scenarios require manual support review.",
            },
            {
                "id": "individual_cannot_convert_to_institutional",
                "applies_to": ["institutional_onboarding"],
                "rule": "An account already completed as individual verification cannot be converted into an institutional account.",
            },
            {
                "id": "institutional_onboarding_web_only",
                "applies_to": ["institutional_onboarding"],
                "rule": "Institutional onboarding currently requires the web flow instead of the app flow.",
            },
            {
                "id": "ticket_follow_up_same_thread",
                "applies_to": ["ticket_support"],
                "rule": "Users should continue follow-up in the same support ticket instead of creating a new one for the same issue.",
            },
        ],
        "handoff_conditions": [
            "account compromised or stolen",
            "verification identity occupied by another account",
            "unsupported country or service restriction",
            "document mismatch that cannot be resolved by self-service instructions",
            "institutional edge-case types requiring email verification follow-up",
        ],
    }


def build_review_rules() -> dict[str, Any]:
    return {
        "institutional_required_documents": [
            "certificate_of_incorporation_or_business_license",
            "memorandum_articles_or_bylaws",
            "director_list",
            "latest_shareholding_chart_or_shareholder_register_within_12_months",
            "business_address_proof",
            "identity_document_and_address_proof_for_directors_ubo_and_authorized_users",
        ],
        "individual_verification_rules": [
            {
                "id": "id_validity_threshold",
                "rule": "Identity documents must remain valid for at least 60 days.",
                "decision": "resubmit",
            },
            {
                "id": "poa_recency",
                "rule": "Proof of address must show the user's real name, full current address, and be issued within the last 3 months.",
                "decision": "resubmit",
            },
            {
                "id": "document_quality",
                "rule": "Blurred, cropped, edited, screenshot, black-and-white, damaged, or incomplete documents are not accepted.",
                "decision": "resubmit",
            },
            {
                "id": "identity_mismatch",
                "rule": "Face mismatch or identity inconsistency between selfie and document requires manual review and may lead to rejection.",
                "decision": "manual_review",
            },
            {
                "id": "duplicate_identity",
                "rule": "A single identity should not verify multiple accounts. Duplicate identity occupation requires manual support intervention.",
                "decision": "manual_review",
            },
            {
                "id": "age_requirement",
                "rule": "Users must be at least 18 years old to pass verification.",
                "decision": "reject",
            },
            {
                "id": "unsupported_country",
                "rule": "Users in unsupported countries or restricted regions cannot complete verification for service activation.",
                "decision": "reject",
            },
        ],
        "accepted_poa_documents": [
            "government_issued_identity_document_with_address",
            "bank_or_credit_card_statement",
            "utility_bill",
            "stamped_tenancy_agreement",
            "tax_document",
            "salary_slip",
            "valid_insurance_contract",
            "government_or_public_authority_residence_letter",
        ],
        "rejected_poa_documents": [
            "bank_account_opening_certificate",
            "electronic_driver_license_only",
            "payment_screenshot",
            "ecommerce_order_record",
            "food_delivery_order_record",
            "mobile_phone_bill",
        ],
        "escalation_targets": {
            "institutional_general_questions": "verification@okx.com",
            "identity_occupied_or_manual_kyc_review": "human_support",
        },
    }


def build_status_fields() -> dict[str, Any]:
    return {
        "normalized_issue_fields": [
            "issue_family",
            "route_hint",
            "source_mode",
            "section_slug",
            "section_title",
            "required_documents",
            "unsupported_conditions",
            "handoff_required",
            "recommended_next_action",
            "evidence_urls",
        ],
        "tool_contracts": {
            "get_kyb_status": {
                "description": "Institutional or identity verification status.",
                "expected_fields": ["current_status", "missing_items", "rejection_reason", "next_action", "eta"],
            },
            "get_deposit_status": {
                "description": "Deposit status lookup.",
                "expected_fields": ["asset", "network", "status", "txid", "confirmations", "next_action"],
            },
            "get_withdraw_status": {
                "description": "Withdrawal status lookup.",
                "expected_fields": ["asset", "network", "status", "txid", "review_reason", "next_action"],
            },
            "get_wallet_network_status": {
                "description": "Wallet and network suspension or recovery status.",
                "expected_fields": ["asset", "network", "deposit_enabled", "withdraw_enabled", "announcement_url", "eta"],
            },
        },
        "document_review_fields": {
            "core_identity": ["full_name", "date_of_birth", "id_number", "country"],
            "proof_of_address": ["full_name", "full_address", "issue_date", "document_type"],
            "institutional_core": ["entity_name", "registration_number", "incorporation_date", "ownership_structure"],
        },
    }


def build_examples() -> dict[str, Any]:
    return {
        "cases": [
            {
                "id": "okx-kyc-reject-invalid-photo",
                "route": "knowledge_qa",
                "user_message": "为什么我的身份认证失败了？",
                "expected_intent": "verification_failure_reason",
                "expected_sections": ["faq-verification"],
            },
            {
                "id": "okx-poa-requirements",
                "route": "knowledge_qa",
                "user_message": "地址证明需要什么文件，多久内有效？",
                "expected_intent": "poa_requirements",
                "expected_sections": ["faq-verification"],
            },
            {
                "id": "okx-institutional-docs",
                "route": "knowledge_qa",
                "user_message": "企业认证需要准备哪些材料？",
                "expected_intent": "institutional_required_documents",
                "expected_sections": ["faq-institutional-onboarding"],
            },
            {
                "id": "okx-ticket-followup",
                "route": "knowledge_qa",
                "user_message": "怎么查看我的客服工单进度？",
                "expected_intent": "ticket_followup",
                "expected_sections": ["faq-account-management-and-security"],
            },
            {
                "id": "okx-withdraw-suspension",
                "route": "status_diagnosis",
                "user_message": "某条链现在能提现吗？",
                "expected_intent": "wallet_network_status",
                "expected_sections": ["announcements-deposit-withdrawal-suspension-resumption", "faq-crypto-withdrawals"],
            },
            {
                "id": "okx-security-handoff",
                "route": "handoff",
                "user_message": "我账号可能被盗了，想先冻结账户。",
                "expected_intent": "account_security_incident",
                "expected_sections": ["faq-account-and-wallet-safeguard-measures", "faq-account-management-and-security"],
            },
            {
                "id": "okx-kyb-review",
                "route": "kyb_review",
                "user_message": "我上传了企业认证材料，帮我先看还缺什么。",
                "expected_intent": "institutional_document_review",
                "expected_sections": ["faq-institutional-onboarding"],
            },
        ]
    }


def build_prompt() -> str:
    return textwrap.dedent(
        """
        You are the OKX Chinese help-center support runtime.

        Use live tools when available. When no live tool is configured, clearly say the answer is based on public OKX help-center documentation.

        Always answer in this structure:
        1. Conclusion
        2. Evidence
        3. Next action

        Operational rules:
        - Security incidents, identity occupation, and irreversible compliance conflicts must go to handoff.
        - Verification and institutional onboarding questions should cite the exact OKX article or rule.
        - Do not pretend to know live ticket status, deposit status, withdraw status, or verification state without a real adapter.
        - Document-review output is a human-review recommendation only.
        """
    ).strip() + "\n"


def build_processing_record(
    source_root: Path,
    output_root: Path,
    source_summary: dict[str, Any],
    articles: list[dict[str, Any]],
) -> str:
    category_counts = Counter(article["category"] for article in articles)
    domain_counts = Counter(article["domain"] for article in articles)
    section_counts = Counter(article["section_slug"] for article in articles)
    top_sections = section_counts.most_common(12)
    lines = [
        "# OKX Platform Package Processing Record",
        "",
        "## Input package",
        "",
        f"- Source root: `{source_root}`",
        f"- Output root: `{output_root}`",
        f"- Total articles discovered: `{source_summary['article_count']}`",
        f"- Successfully fetched articles: `{source_summary['article_success_count']}`",
        f"- Public source count: `{source_summary['public_source_count']}`",
        "",
        "## Step 1. Read package metadata",
        "",
        "- Loaded `summary.json`, `source_catalog.csv`, `article_index.csv`, and the `articles/` markdown corpus.",
        "- Used article index metadata as the primary routing key, with markdown body as the knowledge payload.",
        "",
        "## Step 2. First-pass article classification",
        "",
        "Articles were bucketed by original OKX category first, then mapped into assistant domains:",
        "",
    ]
    for category, count in category_counts.items():
        lines.append(f"- `{category}`: `{count}` articles")
    lines.extend(
        [
            "",
            "Assistant domain mapping:",
            "",
        ]
    )
    for domain, count in domain_counts.items():
        lines.append(f"- `{domain}`: `{count}` articles")

    lines.extend(
        [
            "",
            "Top sections by article volume:",
            "",
        ]
    )
    for slug, count in top_sections:
        lines.append(f"- `{slug}`: `{count}` articles")

    lines.extend(
        [
            "",
            "## Step 3. Knowledge-document identification",
            "",
            "Knowledge documents are public OKX help-center articles that can support direct customer responses.",
            "Selection rule:",
            "- Keep FAQ, public announcements, product documentation, and terms articles.",
            "- Preserve `category`, `section_slug`, `section_title`, and `route_hint` as retrieval metadata.",
            "- Store the body as normalized markdown text inside JSONL records.",
            "",
            "## Step 4. Work-rule identification",
            "",
            "Work rules were derived from sections that describe operational handling rather than static definitions.",
            "Primary sources:",
            "- `faq-account-management-and-security`",
            "- `faq-crypto-deposits`",
            "- `faq-crypto-withdrawals`",
            "- `announcements-deposit-withdrawal-suspension-resumption`",
            "",
            "Examples of extracted work rules:",
            "- continue follow-up in the same support ticket",
            "- mark deposit or withdrawal guidance as documentation fallback without live API",
            "- hand off immediately on account-compromise signals",
            "",
            "## Step 5. Review-rule identification",
            "",
            "Review rules were derived from identity verification and institutional onboarding articles.",
            "Primary sources:",
            "- `faq-verification`",
            "- `faq-institutional-onboarding`",
            "",
            "Examples of extracted review rules:",
            "- POA must be issued within 3 months",
            "- identity documents must remain valid for at least 60 days",
            "- screenshots, edited images, or incomplete documents are not accepted",
            "- institutional onboarding requires company registration, ownership, address, and beneficial-owner material",
            "",
            "## Step 6. Normalized state-field design",
            "",
            "Created schema files to normalize what the assistant should ask for and store even before a live OKX adapter exists.",
            "This includes route hints, issue family, evidence URLs, required document lists, and tool contracts.",
            "",
            "## Step 7. Response templates and examples",
            "",
            "Created:",
            "- fixed reply template for public-help answers",
            "- example cases for KYC, KYB, ticket follow-up, wallet status, and security handoff",
            "",
            "## Step 8. Output package",
            "",
            "Generated the following platform-package components:",
            "- `platform.yaml`",
            "- `knowledge/*.jsonl`",
            "- `rules/*.yaml`",
            "- `schemas/*.yaml`",
            "- `prompts/reply.txt`",
            "- `examples/cases.yaml`",
            "",
            "## Notes",
            "",
            "- This package is documentation-driven and does not yet contain a live OKX adapter.",
            "- Ticket status, deposit status, withdrawal status, and verification status remain public-help fallbacks until an adapter is provided.",
            "- The announcement corpus is large and should be filtered by keyword and recency during production retrieval.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def build_platform_package(source_root: Path = DEFAULT_SOURCE_ROOT, output_root: Path = DEFAULT_OUTPUT_ROOT) -> None:
    source_summary = json.loads((source_root / "summary.json").read_text(encoding="utf-8"))
    articles = load_articles(source_root)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for article in articles:
        grouped[article["domain"]].append(article)

    (output_root / "knowledge").mkdir(parents=True, exist_ok=True)
    (output_root / "rules").mkdir(parents=True, exist_ok=True)
    (output_root / "schemas").mkdir(parents=True, exist_ok=True)
    (output_root / "prompts").mkdir(parents=True, exist_ok=True)
    (output_root / "examples").mkdir(parents=True, exist_ok=True)

    platform_yaml = {
        "id": "okx_help",
        "name": "OKX Help Center",
        "default_locale": "zh-CN",
        "enabled_routes": ["knowledge_qa", "status_diagnosis", "kyb_review", "handoff"],
        "workflow_nodes": {
            "knowledge_qa": ["classify", "gather_context", "retrieve_kb", "render_reply"],
            "status_diagnosis": ["classify", "gather_context", "call_tool", "retrieve_kb", "render_reply", "handoff"],
            "kyb_review": ["classify", "gather_context", "review_documents", "cross_check", "handoff", "render_reply"],
            "handoff": ["classify", "gather_context", "handoff", "render_reply"],
        },
        "source_artifact": str(source_root),
        "article_count": len(articles),
    }
    (output_root / "platform.yaml").write_text(yaml.safe_dump(platform_yaml, allow_unicode=True, sort_keys=False), encoding="utf-8")

    for domain, items in grouped.items():
        write_jsonl(output_root / "knowledge" / f"{domain}.jsonl", items)

    (output_root / "rules" / "route_rules.yaml").write_text(
        yaml.safe_dump(build_route_rules(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (output_root / "rules" / "work_rules.yaml").write_text(
        yaml.safe_dump(build_work_rules(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (output_root / "rules" / "review_rules.yaml").write_text(
        yaml.safe_dump(build_review_rules(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (output_root / "schemas" / "status_fields.yaml").write_text(
        yaml.safe_dump(build_status_fields(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (output_root / "prompts" / "reply.txt").write_text(build_prompt(), encoding="utf-8")
    (output_root / "examples" / "cases.yaml").write_text(
        yaml.safe_dump(build_examples(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    package_summary = {
        "source_summary": source_summary,
        "output_summary": {
            "knowledge_domain_counts": dict(Counter(article["domain"] for article in articles)),
            "category_counts": dict(Counter(article["category"] for article in articles)),
        },
    }
    (output_root / "summary.json").write_text(json.dumps(package_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_root / "PROCESSING_RECORD.md").write_text(
        build_processing_record(source_root, output_root, source_summary, articles),
        encoding="utf-8",
    )


if __name__ == "__main__":
    build_platform_package()

# OKX Platform Package Processing Record

## Input package

- Source root: `C:\Users\26265\Documents\New project\garrytan\artifacts\okx_help`
- Output root: `C:\Users\26265\Documents\New project\Ai-server\platforms\okx_help`
- Total articles discovered: `983`
- Successfully fetched articles: `983`
- Public source count: `52`

## Step 1. Read package metadata

- Loaded `summary.json`, `source_catalog.csv`, `article_index.csv`, and the `articles/` markdown corpus.
- Used article index metadata as the primary routing key, with markdown body as the knowledge payload.

## Step 2. First-pass article classification

Articles were bucketed by original OKX category first, then mapped into assistant domains:

- `faq`: `128` articles
- `announcements`: `747` articles
- `product-documentation`: `55` articles
- `terms-of-agreement`: `53` articles

Assistant domain mapping:

- `general_support`: `41` articles
- `onboarding`: `18` articles
- `account_security`: `33` articles
- `asset_ops`: `341` articles
- `market_announcements`: `442` articles
- `trading_rules`: `55` articles
- `terms`: `53` articles

Top sections by article volume:

- `announcements-new-listings`: `388` articles
- `announcements-deposit-withdrawal-suspension-resumption`: `305` articles
- `terms-of-agreement`: `53` articles
- `announcements-delistings`: `44` articles
- `faq-account-management-and-security`: `23` articles
- `faq-crypto-deposits`: `22` articles
- `product-documentation-introduction-to-basic-trading-rules`: `21` articles
- `faq-crypto-withdrawals`: `14` articles
- `product-documentation-option-contracts`: `11` articles
- `announcements-p2p-trading`: `10` articles
- `faq-verification`: `9` articles
- `faq-institutional-onboarding`: `9` articles

## Step 3. Knowledge-document identification

Knowledge documents are public OKX help-center articles that can support direct customer responses.
Selection rule:
- Keep FAQ, public announcements, product documentation, and terms articles.
- Preserve `category`, `section_slug`, `section_title`, and `route_hint` as retrieval metadata.
- Store the body as normalized markdown text inside JSONL records.

## Step 4. Work-rule identification

Work rules were derived from sections that describe operational handling rather than static definitions.
Primary sources:
- `faq-account-management-and-security`
- `faq-crypto-deposits`
- `faq-crypto-withdrawals`
- `announcements-deposit-withdrawal-suspension-resumption`

Examples of extracted work rules:
- continue follow-up in the same support ticket
- mark deposit or withdrawal guidance as documentation fallback without live API
- hand off immediately on account-compromise signals

## Step 5. Review-rule identification

Review rules were derived from identity verification and institutional onboarding articles.
Primary sources:
- `faq-verification`
- `faq-institutional-onboarding`

Examples of extracted review rules:
- POA must be issued within 3 months
- identity documents must remain valid for at least 60 days
- screenshots, edited images, or incomplete documents are not accepted
- institutional onboarding requires company registration, ownership, address, and beneficial-owner material

## Step 6. Normalized state-field design

Created schema files to normalize what the assistant should ask for and store even before a live OKX adapter exists.
This includes route hints, issue family, evidence URLs, required document lists, and tool contracts.

## Step 7. Response templates and examples

Created:
- fixed reply template for public-help answers
- example cases for KYC, KYB, ticket follow-up, wallet status, and security handoff

## Step 8. Output package

Generated the following platform-package components:
- `platform.yaml`
- `knowledge/*.jsonl`
- `rules/*.yaml`
- `schemas/*.yaml`
- `prompts/reply.txt`
- `examples/cases.yaml`

## Notes

- This package is documentation-driven and does not yet contain a live OKX adapter.
- Ticket status, deposit status, withdrawal status, and verification status remain public-help fallbacks until an adapter is provided.
- The announcement corpus is large and should be filtered by keyword and recency during production retrieval.


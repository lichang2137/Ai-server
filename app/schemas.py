from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


RouteType = Literal["knowledge_qa", "status_diagnosis", "kyb_review", "handoff"]
DecisionType = Literal["approve", "resubmit", "reject", "manual_review"]


class Attachment(BaseModel):
    attachment_id: str
    name: str
    mime_type: str
    url: str
    size_bytes: int = 0


class RequestContext(BaseModel):
    locale: str = "zh-CN"
    attachments: list[Attachment] = Field(default_factory=list)


class SupportMessageRequest(BaseModel):
    channel: Literal["lark", "telegram"]
    channel_user_id: str
    session_id: str
    platform_user_id: str | None = None
    message_id: str
    text: str
    timestamp: datetime
    context: RequestContext = Field(default_factory=RequestContext)


class StructuredReply(BaseModel):
    conclusion: str
    evidence: list[str]
    next_action: list[str]


class ReplyPayload(BaseModel):
    text: str
    structured: StructuredReply


class ReviewRecommendation(BaseModel):
    decision: DecisionType
    confidence: float
    reasons: list[str]


class EvidenceRef(BaseModel):
    file_name: str | None = None
    page: int | None = None
    locator: str | None = None
    snippet: str


class ReviewedDocument(BaseModel):
    file_name: str
    document_type: str
    fields: dict[str, Any]
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class CrossCheckResult(BaseModel):
    check: str
    result: Literal["pass", "fail", "unknown"]
    details: str


class DocumentReviewResult(BaseModel):
    documents: list[ReviewedDocument]
    cross_checks: list[CrossCheckResult]
    recommendation: ReviewRecommendation
    rule_hits: list[str] = Field(default_factory=list)


class ReviewEnvelope(BaseModel):
    needed: bool
    summary: DocumentReviewResult | None = None


class HandoffPayload(BaseModel):
    type: str
    case_id: str
    route: RouteType
    user_id: str | None = None
    current_status: str | None = None
    missing_items: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    suggested_action: str
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    failed_checks: list[str] = Field(default_factory=list)
    recommendation: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class HandoffEnvelope(BaseModel):
    needed: bool
    summary: HandoffPayload | None = None


class SupportMessageResponse(BaseModel):
    route: RouteType
    reply: ReplyPayload
    review: ReviewEnvelope
    handoff: HandoffEnvelope


class KnowledgeHit(BaseModel):
    title: str
    source_url: str
    updated_at: str | None = None
    summary: str
    tags: list[str] = Field(default_factory=list)


class ToolExecutionResult(BaseModel):
    tool_name: str
    source_mode: Literal["api", "documentation_fallback"]
    degraded: bool
    data: dict[str, Any]
    evidence: list[str] = Field(default_factory=list)
    warning: str | None = None
    handoff_required: bool = False


class WorkflowTrace(BaseModel):
    route: RouteType
    nodes: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

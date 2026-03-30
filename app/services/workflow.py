from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.schemas import (
    DocumentReviewResult,
    HandoffEnvelope,
    HandoffPayload,
    ReplyPayload,
    ReviewEnvelope,
    RouteType,
    StructuredReply,
    SupportMessageRequest,
    SupportMessageResponse,
    WorkflowTrace,
)
from app.services.document_review import review_uploaded_documents
from app.services.knowledge import search_platform_kb
from app.services.platform_registry import PlatformPackage
from app.services.tool_layer import call_status_tool


@dataclass
class WorkflowContext:
    payload: SupportMessageRequest
    package: PlatformPackage
    route: RouteType
    trace: WorkflowTrace = field(default_factory=lambda: WorkflowTrace(route="knowledge_qa"))
    tool_result: dict[str, Any] | None = None
    kb_hits: list[Any] = field(default_factory=list)
    review_result: DocumentReviewResult | None = None
    handoff: HandoffPayload | None = None
    structured: StructuredReply | None = None


class WorkflowEngine:
    def run(self, payload: SupportMessageRequest, package: PlatformPackage, route: RouteType) -> tuple[SupportMessageResponse, WorkflowTrace]:
        context = WorkflowContext(payload=payload, package=package, route=route, trace=WorkflowTrace(route=route))
        context.trace.nodes.append("classify")
        self._gather_context(context)
        if route == "knowledge_qa":
            self._retrieve_kb(context)
            self._render_knowledge_reply(context)
        elif route == "status_diagnosis":
            self._call_tool(context)
            self._retrieve_kb(context)
            self._render_status_reply(context)
        elif route == "kyb_review":
            self._review_documents(context)
            self._handoff_for_review(context)
            self._render_review_reply(context)
        else:
            self._handoff_direct(context)
            self._render_handoff_reply(context)

        response = SupportMessageResponse(
            route=route,
            reply=ReplyPayload(text=self._render_reply_text(context.structured), structured=context.structured),
            review=ReviewEnvelope(needed=context.review_result is not None, summary=context.review_result),
            handoff=HandoffEnvelope(needed=context.handoff is not None, summary=context.handoff),
        )
        return response, context.trace

    def _gather_context(self, context: WorkflowContext) -> None:
        context.trace.nodes.append("gather_context")
        context.trace.notes.append(f"platform={context.package.platform_id}")

    def _retrieve_kb(self, context: WorkflowContext) -> None:
        context.trace.nodes.append("retrieve_kb")
        context.kb_hits = search_platform_kb(context.package, context.payload.text, limit=3)

    def _call_tool(self, context: WorkflowContext) -> None:
        context.trace.nodes.append("call_tool")
        result = call_status_tool(
            context.package,
            context.payload.text,
            context.payload.platform_user_id,
            {"locale": context.payload.context.locale},
        )
        context.tool_result = result.model_dump()
        if result.degraded:
            context.trace.notes.append("needs_clarification")

    def _review_documents(self, context: WorkflowContext) -> None:
        context.trace.nodes.extend(["review_documents", "cross_check"])
        context.review_result = review_uploaded_documents(
            context.payload.context.attachments,
            context.package,
            context.payload.timestamp,
        )

    def _handoff_for_review(self, context: WorkflowContext) -> None:
        context.trace.nodes.append("handoff")
        review = context.review_result
        if review is None:
            return
        context.handoff = HandoffPayload(
            type="kyb_review",
            case_id=f"case-{uuid4().hex[:10]}",
            route=context.route,
            user_id=context.payload.platform_user_id,
            current_status=None,
            missing_items=[check.check for check in review.cross_checks if check.check.startswith("required_") and check.result == "fail"],
            rejection_reason=None,
            suggested_action="Escalate this case to a human reviewer with the extracted evidence bundle.",
            extracted_fields={doc.file_name: doc.fields for doc in review.documents},
            failed_checks=[check.check for check in review.cross_checks if check.result == "fail"],
            recommendation=review.recommendation.model_dump(),
            evidence_refs=[ref.model_dump() for doc in review.documents for ref in doc.evidence_refs[:2]],
        )

    def _handoff_direct(self, context: WorkflowContext) -> None:
        context.trace.nodes.append("handoff")
        context.handoff = HandoffPayload(
            type="security_or_manual",
            case_id=f"case-{uuid4().hex[:10]}",
            route=context.route,
            user_id=context.payload.platform_user_id,
            suggested_action="Escalate to a human support agent immediately.",
        )

    def _render_knowledge_reply(self, context: WorkflowContext) -> None:
        context.trace.nodes.append("render_reply")
        evidence = [f"{hit.title} | {hit.source_url}" for hit in context.kb_hits]
        if not evidence:
            evidence = ["No matching knowledge item was found in the active platform package."]
        context.structured = StructuredReply(
            conclusion="This answer is based on the active platform package knowledge and workflow rules.",
            evidence=evidence,
            next_action=["If you need a live status check, provide the platform user ID and the issue you want diagnosed."],
        )

    def _render_status_reply(self, context: WorkflowContext) -> None:
        context.trace.nodes.append("render_reply")
        result = context.tool_result or {}
        evidence = list(result.get("evidence", []))
        evidence.extend(f"{hit.title} | {hit.source_url}" for hit in context.kb_hits[:2])
        source_mode = result.get("source_mode", "documentation_fallback")
        degraded = result.get("degraded", False)
        warning = result.get("warning")

        conclusion = "Status diagnosis completed from the live platform tool."
        if source_mode == "documentation_fallback" or degraded:
            conclusion = "This is documentation-backed guidance, not a live system status."
            if warning:
                evidence.insert(0, warning)
        next_action = ["Connect a live adapter or provide the required identifiers for a more precise diagnosis."]

        data = result.get("data") or {}
        if result.get("tool_name") == "get_kyb_status" and isinstance(data, dict):
            status = data.get("current_status")
            if status:
                conclusion = f"Current KYB status: {status}."
            missing_items = data.get("missing_items") or []
            if missing_items:
                evidence.append("missing_items=" + ", ".join(str(item) for item in missing_items))
            if data.get("next_action"):
                evidence.append(f"adapter_next_action={data['next_action']}")
            if status == "material_missing":
                rendered_missing = ", ".join(str(item) for item in missing_items) or "see missing items in evidence"
                next_action = [data.get("next_action") or f"Upload the missing documents and resubmit. Missing items: {rendered_missing}."]
            elif status in {"pending_review", "in_review"}:
                next_action = [data.get("next_action") or "Wait for the review window to complete or escalate if the SLA is breached."]
            elif status in {"rejected", "expired"}:
                next_action = [data.get("next_action") or "Follow up with human support and prepare a corrected resubmission package."]
                context.handoff = HandoffPayload(
                    type="status_followup",
                    case_id=f"case-{uuid4().hex[:10]}",
                    route=context.route,
                    user_id=context.payload.platform_user_id,
                    current_status=status,
                    suggested_action=next_action[0],
                )
            elif status == "approved":
                next_action = [data.get("next_action") or "No further KYB action is required unless a new compliance request is raised."]

        context.structured = StructuredReply(conclusion=conclusion, evidence=evidence[:6], next_action=next_action)

    def _render_review_reply(self, context: WorkflowContext) -> None:
        context.trace.nodes.append("render_reply")
        review = context.review_result
        assert review is not None
        evidence = [f"{document.file_name} => {document.document_type}" for document in review.documents]
        evidence.extend(f"{check.check}: {check.result} ({check.details})" for check in review.cross_checks[:4])
        decision = review.recommendation.decision
        conclusion_map = {
            "approve": "System recommendation: approve after human verification.",
            "resubmit": "System recommendation: request resubmission or additional documents.",
            "reject": "System recommendation: reject after human verification of the conflicts.",
            "manual_review": "System recommendation: perform focused manual review before deciding.",
        }
        context.structured = StructuredReply(
            conclusion=conclusion_map[decision],
            evidence=evidence,
            next_action=["A structured review summary has been prepared for the human reviewer."],
        )

    def _render_handoff_reply(self, context: WorkflowContext) -> None:
        context.trace.nodes.append("render_reply")
        context.structured = StructuredReply(
            conclusion="This issue requires human follow-up.",
            evidence=["The message matched a security or manual-handoff rule."],
            next_action=["A structured handoff summary has been generated for the human support team."],
        )

    @staticmethod
    def _render_reply_text(structured: StructuredReply) -> str:
        evidence_lines = "\n".join(f"- {item}" for item in structured.evidence) if structured.evidence else "- No evidence available"
        next_lines = "\n".join(f"- {item}" for item in structured.next_action) if structured.next_action else "- No suggested action"
        return (
            "1. Conclusion\n"
            f"{structured.conclusion}\n\n"
            "2. Evidence\n"
            f"{evidence_lines}\n\n"
            "3. Next action\n"
            f"{next_lines}"
        )

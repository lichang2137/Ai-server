from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import HandoffSummary, MessageEvent, ReviewCase, SupportSession
from app.schemas import HandoffEnvelope, HandoffPayload, SupportMessageRequest, SupportMessageResponse
from app.services.platform_registry import PlatformPackage, registry
from app.services.router import route_message
from app.services.workflow import WorkflowEngine


def initialize_runtime() -> None:
    registry.load()


def _get_or_create_session(db: Session, payload: SupportMessageRequest, package: PlatformPackage, route: str) -> SupportSession:
    session = db.get(SupportSession, payload.session_id)
    if session is None:
        session = SupportSession(
            session_id=payload.session_id,
            platform_id=package.platform_id,
            channel=payload.channel,
            channel_user_id=payload.channel_user_id,
            platform_user_id=payload.platform_user_id,
            locale=payload.context.locale,
            last_route=route,
            turns_count=0,
            clarification_turns=0,
        )
        db.add(session)
    else:
        session.platform_id = package.platform_id
        session.channel = payload.channel
        session.channel_user_id = payload.channel_user_id
        session.platform_user_id = payload.platform_user_id or session.platform_user_id
        session.locale = payload.context.locale
        session.last_route = route
    return session


def _add_event(db: Session, payload: SupportMessageRequest, direction: str, route: str | None, text: str, raw_payload: dict) -> None:
    db.add(
        MessageEvent(
            message_id=payload.message_id if direction == "inbound" else f"reply-{payload.message_id}",
            session_id=payload.session_id,
            direction=direction,
            route=route,
            text=text,
            payload_json=json.dumps(raw_payload, ensure_ascii=False),
        )
    )


def _persist_handoff(db: Session, payload: SupportMessageRequest, summary: HandoffPayload) -> None:
    db.add(
        HandoffSummary(
            case_id=summary.case_id,
            session_id=payload.session_id,
            message_id=payload.message_id,
            route=summary.route,
            summary_type=summary.type,
            user_id=summary.user_id,
            current_status=summary.current_status,
            missing_items_json=json.dumps(summary.missing_items, ensure_ascii=False),
            rejection_reason=summary.rejection_reason,
            suggested_action=summary.suggested_action,
            payload_json=summary.model_dump_json(),
        )
    )


def _persist_review(db: Session, payload: SupportMessageRequest, route: str, response: SupportMessageResponse) -> None:
    if not response.review.needed or response.review.summary is None:
        return
    case_id = response.handoff.summary.case_id if response.handoff.needed and response.handoff.summary else f"case-{uuid4().hex[:10]}"
    db.add(
        ReviewCase(
            case_id=case_id,
            session_id=payload.session_id,
            message_id=payload.message_id,
            route=route,
            decision=response.review.summary.recommendation.decision,
            confidence=response.review.summary.recommendation.confidence,
            payload_json=response.review.summary.model_dump_json(),
        )
    )


def handle_support_message(db: Session, payload: SupportMessageRequest) -> SupportMessageResponse:
    package = registry.get()
    decision = route_message(payload)
    session = _get_or_create_session(db, payload, package, decision.route)
    session.turns_count += 1
    _add_event(db, payload, "inbound", decision.route, payload.text, payload.model_dump(mode="json"))

    response, trace = WorkflowEngine().run(payload, package, decision.route)
    session.updated_at = datetime.now(timezone.utc)
    session.last_route = response.route

    clarification_needed = "needs_clarification" in trace.notes
    if response.route not in {"knowledge_qa", "status_diagnosis"}:
        session.clarification_turns = 0
    elif clarification_needed:
        session.clarification_turns += 1
    else:
        session.clarification_turns = 0

    if clarification_needed and session.clarification_turns >= 2 and not response.handoff.needed:
        response.handoff = HandoffEnvelope(
            needed=True,
            summary=HandoffPayload(
                type="followup_required",
                case_id=f"case-{uuid4().hex[:10]}",
                route=response.route,
                user_id=payload.platform_user_id,
                suggested_action="Escalate after repeated clarification loops without a live resolution.",
            ),
        )

    _add_event(
        db,
        payload,
        "outbound",
        response.route,
        response.reply.text,
        {"response": response.model_dump(mode="json"), "trace": trace.model_dump(mode="json")},
    )
    if response.handoff.needed and response.handoff.summary:
        _persist_handoff(db, payload, response.handoff.summary)
    _persist_review(db, payload, response.route, response)

    db.commit()
    return response

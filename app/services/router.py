from __future__ import annotations

from dataclasses import dataclass

from app.schemas import RouteType, SupportMessageRequest


SECURITY_KEYWORDS = ("hacked", "stolen", "security", "compromised", "盗号", "被骗", "冻结", "安全")
KNOWLEDGE_KEYWORDS = ("materials", "requirements", "requirement", "guide", "policy", "faq", "材料", "要求", "规则", "流程", "公告")
STATUS_KEYWORDS = (
    "status",
    "kyb",
    "kyc",
    "审核",
    "认证",
    "补件",
    "驳回",
    "提现",
    "充值",
    "钱包",
    "network",
    "ticket",
)
HANDOFF_KEYWORDS = ("人工", "客服", "转人工", "complaint")


@dataclass
class RouteDecision:
    route: RouteType
    reason: str
    risk_level: str = "low"


def route_message(payload: SupportMessageRequest) -> RouteDecision:
    lowered = (payload.text or "").lower()
    if payload.context.attachments:
        return RouteDecision(route="kyb_review", reason="attachments_present", risk_level="medium")
    if any(keyword in lowered for keyword in SECURITY_KEYWORDS):
        return RouteDecision(route="handoff", reason="security_keyword", risk_level="high")
    if any(keyword in lowered for keyword in HANDOFF_KEYWORDS):
        return RouteDecision(route="handoff", reason="handoff_requested", risk_level="medium")
    if any(keyword in lowered for keyword in KNOWLEDGE_KEYWORDS):
        return RouteDecision(route="knowledge_qa", reason="knowledge_keyword", risk_level="low")
    if any(keyword in lowered for keyword in STATUS_KEYWORDS):
        return RouteDecision(route="status_diagnosis", reason="status_keyword", risk_level="low")
    return RouteDecision(route="knowledge_qa", reason="default_knowledge", risk_level="low")

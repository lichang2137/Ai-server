from __future__ import annotations

from dataclasses import dataclass

from app.schemas import RouteType, SupportMessageRequest


SECURITY_KEYWORDS = ("hacked", "stolen", "security", "compromised", "盗号", "被骗", "冻结", "安全")
KNOWLEDGE_KEYWORDS = ("materials", "requirements", "requirement", "guide", "policy", "faq", "材料", "要求", "规则", "流程", "公告")
STATUS_KEYWORDS = (
    "status",
    "审核",
    "认证",
    "进度",
    "补件",
    "驳回",
    "提现",
    "充值",
    "未到账",
    "还缺",
    "缺什么",
    "企业认证",
    "钱包",
    "network",
    "ticket",
)
STATUS_ENTITY_KEYWORDS = ("kyb", "kyc", "企业认证", "认证")
HANDOFF_KEYWORDS = ("人工", "客服", "转人工", "complaint", "投诉", "工单")


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
    if payload.platform_user_id and any(keyword in lowered for keyword in STATUS_KEYWORDS):
        return RouteDecision(route="status_diagnosis", reason="status_keyword_with_user", risk_level="low")
    if payload.platform_user_id and any(keyword in lowered for keyword in STATUS_ENTITY_KEYWORDS) and any(
        phrase in lowered for phrase in ("还缺", "缺什么", "审核", "进度", "驳回", "补件")
    ):
        return RouteDecision(route="status_diagnosis", reason="status_phrase_with_user", risk_level="low")
    if any(keyword in lowered for keyword in KNOWLEDGE_KEYWORDS):
        return RouteDecision(route="knowledge_qa", reason="knowledge_keyword", risk_level="low")
    if any(keyword in lowered for keyword in STATUS_ENTITY_KEYWORDS):
        return RouteDecision(route="status_diagnosis", reason="status_entity_keyword", risk_level="low")
    if any(keyword in lowered for keyword in STATUS_KEYWORDS):
        return RouteDecision(route="status_diagnosis", reason="status_keyword", risk_level="low")
    return RouteDecision(route="knowledge_qa", reason="default_knowledge", risk_level="low")

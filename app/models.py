from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SupportSession(Base):
    __tablename__ = "support_sessions"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    platform_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    platform_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locale: Mapped[str] = mapped_column(String(32), default="zh-CN", nullable=False)
    last_route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    turns_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clarification_turns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    events: Mapped[list["MessageEvent"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    handoffs: Mapped[list["HandoffSummary"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    reviews: Mapped[list["ReviewCase"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class MessageEvent(Base):
    __tablename__ = "message_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("support_sessions.session_id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    session: Mapped[SupportSession] = relationship(back_populates="events")


class HandoffSummary(Base):
    __tablename__ = "handoff_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("support_sessions.session_id"), nullable=False)
    message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    route: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_type: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    missing_items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    session: Mapped[SupportSession] = relationship(back_populates="handoffs")


class ReviewCase(Base):
    __tablename__ = "review_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("support_sessions.session_id"), nullable=False)
    message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    route: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    session: Mapped[SupportSession] = relationship(back_populates="reviews")

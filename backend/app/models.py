from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchSession(Base):
    __tablename__ = "research_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    depth: Mapped[str] = mapped_column(String(20), default="standard")
    max_sources: Mapped[int] = mapped_column(Integer, default=6)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    sources: Mapped[list["Source"]] = relationship(cascade="all, delete-orphan")
    events: Mapped[list["ResearchEvent"]] = relationship(cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(255))
    snippet: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    credibility: Mapped[float] = mapped_column(Float, default=0.0)
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    citation_id: Mapped[int] = mapped_column(Integer)


class ResearchEvent(Base):
    __tablename__ = "research_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

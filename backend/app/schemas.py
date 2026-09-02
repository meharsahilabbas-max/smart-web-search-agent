from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class ResearchCreate(BaseModel):
    question: str = Field(min_length=10, max_length=2000)
    depth: Literal["quick", "standard", "deep"] = "standard"
    max_sources: int = Field(default=6, ge=3, le=20)


class SourceOut(BaseModel):
    id: int
    title: str
    url: HttpUrl
    domain: str
    snippet: str
    credibility: float
    relevance: float
    citation_id: int

    class Config:
        from_attributes = True


class ResearchOut(BaseModel):
    id: str
    question: str
    depth: str
    status: str
    confidence: float | None
    report: dict | None
    created_at: datetime
    sources: list[SourceOut] = []

    class Config:
        from_attributes = True


class EventOut(BaseModel):
    event_type: str
    message: str
    payload: dict
    created_at: datetime

    class Config:
        from_attributes = True

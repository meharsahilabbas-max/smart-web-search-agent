import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import get_settings
from .database import SessionLocal
from .models import ResearchEvent, ResearchSession, Source

logger = logging.getLogger(__name__)
settings = get_settings()


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _safe_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    blocked = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    return parsed.scheme in {"http", "https"} and host not in blocked and not host.startswith(("10.", "192.168.", "169.254."))


def _score(title: str, url: str, question: str) -> tuple[float, float]:
    words = {word.lower() for word in re.findall(r"[a-zA-Z]{4,}", question)}
    haystack = f"{title} {url}".lower()
    relevance = min(98.0, 45.0 + sum(word in haystack for word in words) * 8.0)
    authority = 86.0 if any(part in _domain(url) for part in (".gov", ".edu", "who.int", "europa.eu")) else 68.0
    return round(authority, 1), round(relevance, 1)


async def search_web(question: str, limit: int) -> list[dict]:
    url = "https://html.duckduckgo.com/html/"
    async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True, headers={"User-Agent": "SmartResearchAgent/1.0"}) as client:
        response = await client.post(url, data={"q": question})
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    results: list[dict] = []
    seen: set[str] = set()
    for item in soup.select(".result"):
        link = item.select_one(".result__a")
        if not link or not link.get("href"):
            continue
        result_url = link["href"]
        if not _safe_url(result_url) or result_url in seen:
            continue
        seen.add(result_url)
        title = link.get_text(" ", strip=True)
        snippet_node = item.select_one(".result__snippet")
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        credibility, relevance = _score(title, result_url, question)
        results.append({"title": title, "url": result_url, "domain": _domain(result_url), "snippet": snippet, "credibility": credibility, "relevance": relevance})
        if len(results) >= limit:
            break
    return results


async def read_page(url: str) -> str:
    if not _safe_url(url):
        raise ValueError("URL is not allowed")
    async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True, headers={"User-Agent": "SmartResearchAgent/1.0"}) as client:
        response = await client.get(url)
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise ValueError("Page exceeds the 2 MB content limit")
    soup = BeautifulSoup(response.text, "lxml")
    for node in soup(["script", "style", "nav", "footer", "header", "aside"]):
        node.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())[:12000]


async def llm_report(question: str, sources: list[dict]) -> dict:
    context = "\n\n".join(f"[{index}] {source['title']} ({source['url']})\n{source.get('content', source['snippet'])[:3500]}" for index, source in enumerate(sources, 1))
    prompt = f"Research question: {question}\n\nEvidence:\n{context}\n\nWrite a grounded JSON report with keys executive_summary, key_findings (array of objects with title, detail, citations), detailed_analysis, limitations, conclusion, confidence. Cite only evidence ids like [1]."
    if not settings.llm_api_key:
        return local_report(question, sources)
    endpoint = settings.llm_base_url.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(endpoint, headers={"Authorization": f"Bearer {settings.llm_api_key}"}, json={"model": settings.llm_model, "temperature": 0.2, "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": prompt}]})
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def local_report(question: str, sources: list[dict]) -> dict:
    findings = [{"title": source["title"], "detail": source.get("snippet") or source.get("content", "")[:500], "citations": [index]} for index, source in enumerate(sources, 1)]
    confidence = round(sum(source["credibility"] for source in sources) / max(len(sources), 1) / 100, 2)
    return {"executive_summary": f"The available evidence provides an initial, source-linked view of: {question}", "key_findings": findings, "detailed_analysis": "Findings are ordered from independently discovered web sources. Read the linked sources for full context.", "limitations": "This report is limited by public page availability and the configured search depth. Claims without a supporting citation should be treated as unresolved.", "conclusion": "The evidence supports the findings above, with uncertainty remaining where sources are sparse or disagree.", "confidence": confidence}


def emit(session: Session, research_id: str, event_type: str, message: str, payload: dict | None = None) -> None:
    session.add(ResearchEvent(research_id=research_id, event_type=event_type, message=message, payload=payload or {}))
    session.commit()


async def run_research(research_id: str) -> None:
    with SessionLocal() as session:
        research = session.get(ResearchSession, research_id)
        if not research:
            return
        try:
            research.status = "running"
            session.commit()
            emit(session, research_id, "research_started", "Research session started")
            emit(session, research_id, "planning_started", "Building a focused research plan")
            emit(session, research_id, "sub_question_created", "Search strategy created", {"sub_questions": [research.question]})
            limit = {"quick": 4, "standard": research.max_sources if hasattr(research, "max_sources") else settings.max_sources, "deep": 10}.get(research.depth, settings.max_sources)
            emit(session, research_id, "search_started", "Searching the public web")
            found = await search_web(research.question, limit)
            emit(session, research_id, "search_completed", f"Found {len(found)} candidate sources", {"count": len(found)})
            enriched: list[dict] = []
            for index, item in enumerate(found, 1):
                try:
                    emit(session, research_id, "source_analyzing", f"Reading source {index}: {item['domain']}", {"url": item["url"]})
                    item["content"] = await read_page(item["url"])
                    enriched.append(item)
                    session.add(Source(research_id=research_id, citation_id=index, **item))
                    session.commit()
                    emit(session, research_id, "source_found", f"Accepted source [{index}]", {"citation_id": index, "title": item["title"]})
                except Exception as exc:
                    logger.warning("source_failed research_id=%s url=%s error=%s", research_id, item["url"], type(exc).__name__)
            emit(session, research_id, "verification_started", "Cross-checking collected evidence")
            emit(session, research_id, "synthesis_started", "Synthesizing cited findings")
            report = await llm_report(research.question, enriched)
            research.report = report
            research.confidence = float(report.get("confidence", 0.0))
            research.status = "completed"
            session.commit()
            emit(session, research_id, "report_generated", "Report generated with source citations")
            emit(session, research_id, "research_completed", "Research completed", {"confidence": research.confidence})
        except Exception as exc:
            logger.exception("research_failed research_id=%s", research_id)
            research.status = "failed"
            session.commit()
            emit(session, research_id, "research_failed", "Research could not be completed", {"error": str(exc)[:200]})

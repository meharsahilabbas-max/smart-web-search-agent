import asyncio
import json
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_db
from .models import ResearchEvent, ResearchSession, Source
from .research import run_research
from .schemas import EventOut, ResearchCreate, ResearchOut, SourceOut

router = APIRouter()


@router.post("/research", response_model=ResearchOut, status_code=201)
async def create_research(payload: ResearchCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    research = ResearchSession(id=str(uuid.uuid4()), question=payload.question.strip(), depth=payload.depth, max_sources=payload.max_sources, status="queued")
    db.add(research)
    db.commit()
    db.refresh(research)
    background_tasks.add_task(run_research, research.id)
    return research


@router.get("/research", response_model=list[ResearchOut])
def list_research(db: Session = Depends(get_db)):
    return list(db.scalars(select(ResearchSession).order_by(ResearchSession.created_at.desc())))


@router.get("/research/{research_id}", response_model=ResearchOut)
def get_research(research_id: str, db: Session = Depends(get_db)):
    research = db.get(ResearchSession, research_id)
    if not research:
        raise HTTPException(404, "Research session not found")
    return research


@router.delete("/research/{research_id}", status_code=204)
def delete_research(research_id: str, db: Session = Depends(get_db)):
    research = db.get(ResearchSession, research_id)
    if not research:
        raise HTTPException(404, "Research session not found")
    db.delete(research)
    db.commit()


@router.get("/research/{research_id}/sources", response_model=list[SourceOut])
def sources(research_id: str, db: Session = Depends(get_db)):
    return list(db.scalars(select(Source).where(Source.research_id == research_id).order_by(Source.citation_id)))


@router.get("/research/{research_id}/report")
def report(research_id: str, db: Session = Depends(get_db)):
    research = db.get(ResearchSession, research_id)
    if not research:
        raise HTTPException(404, "Research session not found")
    return research.report or {"status": research.status}


@router.get("/research/{research_id}/events")
async def events(research_id: str, db: Session = Depends(get_db)):
    if not db.get(ResearchSession, research_id):
        raise HTTPException(404, "Research session not found")

    async def stream():
        sent = 0
        idle = 0
        while idle < 30:
            with next(get_db()) as current:
                items = list(current.scalars(select(ResearchEvent).where(ResearchEvent.research_id == research_id).order_by(ResearchEvent.id)))
                status = current.get(ResearchSession, research_id).status
            for event in items[sent:]:
                yield f"data: {json.dumps({'type': event.event_type, 'message': event.message, 'payload': event.payload})}\n\n"
            sent = len(items)
            if status in {"completed", "failed", "cancelled"} and sent == len(items):
                break
            idle += 1
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@router.post("/research/{research_id}/cancel")
def cancel_research(research_id: str, db: Session = Depends(get_db)):
    research = db.get(ResearchSession, research_id)
    if not research:
        raise HTTPException(404, "Research session not found")
    research.status = "cancelled"
    db.commit()
    return {"status": research.status}


@router.post("/research/{research_id}/continue", response_model=ResearchOut)
async def continue_research(research_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    research = db.get(ResearchSession, research_id)
    if not research:
        raise HTTPException(404, "Research session not found")
    research.status = "queued"
    db.commit()
    background_tasks.add_task(run_research, research.id)
    return research


@router.get("/research/{research_id}/export")
def export_research(research_id: str, format: str = "json", db: Session = Depends(get_db)):
    research = db.get(ResearchSession, research_id)
    if not research:
        raise HTTPException(404, "Research session not found")
    if format == "json":
        return {"question": research.question, "report": research.report, "sources": [SourceOut.model_validate(source).model_dump(mode="json") for source in research.sources]}
    if format == "markdown":
        report = research.report or {}
        lines = [f"# Research Report\n\n## Research Question\n\n{research.question}", f"## Executive Summary\n\n{report.get('executive_summary', '')}", "## Key Findings"]
        lines.extend(f"\n### {finding.get('title', 'Finding')}\n\n{finding.get('detail', '')}" for finding in report.get("key_findings", []))
        lines.append(f"\n## Limitations\n\n{report.get('limitations', '')}\n\n## Conclusion\n\n{report.get('conclusion', '')}")
        return Response("\n".join(lines), media_type="text/markdown", headers={"Content-Disposition": "attachment; filename=research-report.md"})
    raise HTTPException(400, "format must be json or markdown")

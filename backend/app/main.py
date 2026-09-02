from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .database import Base, engine
from .logging_config import configure_logging
from .routes import router

settings = get_settings()
configure_logging()
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Smart Research Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "smart-research-agent"}


@app.get("/api/config/status")
def config_status() -> dict:
    return {"llm_configured": bool(settings.llm_api_key), "search_provider": settings.search_provider, "search_ready": True}

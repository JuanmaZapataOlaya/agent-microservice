import logging
import json
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from supabase import acreate_client
from app.api.routes import build_router
from app.core.config import get_settings
from app.ingest.ingestion_pipeline import IngestionPipeline
from app.agent.orchestrator import AgentOrchestrator
from app.providers.portkey_provider import PortkeyProvider
from app.repositories.supabase_repository import SupabaseRepository
from app.services.session_service import SessionService

settings = get_settings()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"level": record.levelname, "message": record.getMessage()})


logging.basicConfig(stream=sys.stdout, level=settings.log_level)
for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())
logger = logging.getLogger("agent")
app = FastAPI(title="FindMyPet Agent", version="1.0.0")


@app.middleware("http")
async def correlation(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id", "generated")
    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def register_routes() -> None:
    client = await acreate_client(settings.supabase_url, settings.supabase_service_role_key)
    repository = SupabaseRepository(client)
    provider = PortkeyProvider(settings)
    sessions = SessionService(repository, settings.session_ttl_minutes)
    agent = AgentOrchestrator(repository, provider, settings.top_k_results, settings.similarity_threshold)
    ingestion = IngestionPipeline(repository, provider, settings.chunk_size, settings.chunk_overlap)
    app.include_router(build_router(sessions, agent, ingestion))


@app.exception_handler(Exception)
async def unhandled(_: Request, __: Exception) -> JSONResponse:
    logger.exception("unhandled_error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

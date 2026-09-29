from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.api.dependencies import verify_edge, verify_ingest
from app.models.schemas import ChatRequest, ChatResponse, IngestResponse, SessionResponse, SessionStartRequest
from app.models.schemas import RealtimeSessionRequest, RealtimeSessionResponse
from app.agent.realtime import REALTIME_INSTRUCTIONS, REALTIME_TOOLS
from app.providers.portkey_provider import PortkeyProvider
from app.services.session_service import SessionService
from app.agent.orchestrator import AgentOrchestrator
from app.ingest.ingestion_pipeline import IngestionPipeline


def build_router(
    sessions: SessionService,
    agent: AgentOrchestrator,
    ingestion: IngestionPipeline,
    realtime_model: str,
) -> APIRouter:
    router = APIRouter()

    @router.post("/session/start", response_model=SessionResponse, dependencies=[Depends(verify_edge)])
    async def start(request: SessionStartRequest) -> SessionResponse:
        row = await sessions.start(request.user_id)
        return SessionResponse(session_id=row["id"], expires_at=row["expires_at"])

    @router.post("/session/end", status_code=204, dependencies=[Depends(verify_edge)])
    async def end(session_id: UUID) -> None:
        await sessions.repository.end_session(session_id)

    @router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_edge)])
    async def chat(request: ChatRequest) -> ChatResponse:
        correlation_id = str(uuid4())
        try:
            await sessions.require_active(request.session_id)
            message, action, payload = await agent.respond(request.session_id, request.message)
            return ChatResponse(session_id=request.session_id, message=message, action=action,
                                payload=payload, correlation_id=correlation_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post(
        "/realtime/session",
        response_model=RealtimeSessionResponse,
        dependencies=[Depends(verify_edge)],
    )
    async def realtime_session(request: RealtimeSessionRequest) -> RealtimeSessionResponse:
        try:
            await sessions.require_active(request.session_id)
            if not isinstance(agent.provider, PortkeyProvider):
                raise HTTPException(status_code=503, detail="Realtime provider is unavailable")
            session = await agent.provider.create_realtime_session(
                model=realtime_model,
                instructions=REALTIME_INSTRUCTIONS,
                tools=REALTIME_TOOLS,
            )
            client_secret = session.get("client_secret")
            if not isinstance(client_secret, dict):
                raise HTTPException(status_code=502, detail="Invalid realtime provider response")
            return RealtimeSessionResponse(
                session_id=request.session_id,
                model=realtime_model,
                client_secret=client_secret,
                tools=REALTIME_TOOLS,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(verify_ingest)])
    async def ingest(file: UploadFile = File(...)) -> IngestResponse:
        if file.content_type not in {"text/markdown", "text/plain"}:
            raise HTTPException(status_code=415, detail="Only Markdown files are accepted")
        content = (await file.read(2_000_001)).decode("utf-8", errors="strict")
        count = await ingestion.ingest(file.filename or "document.md", content)
        return IngestResponse(document_name=file.filename or "document.md", chunks=count)

    return router

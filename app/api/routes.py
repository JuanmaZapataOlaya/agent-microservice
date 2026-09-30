import logging
from functools import partial
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, WebSocket
from app.api.dependencies import verify_edge, verify_ingest
from app.models.schemas import ChatRequest, ChatResponse, IngestResponse, SessionResponse, SessionStartRequest
from app.models.schemas import RealtimeSessionRequest, RealtimeSessionResponse
from app.agent.realtime import build_session_update
from app.core.config import Settings
from app.providers.portkey_provider import PortkeyProvider
from app.services.realtime_proxy import RealtimeTicketStore, proxy_realtime
from app.services.session_service import SessionService
from app.agent.orchestrator import AgentOrchestrator
from app.ingest.ingestion_pipeline import IngestionPipeline

logger = logging.getLogger("agent.realtime")


def _public_ws_base(request: Request, public_url: str | None) -> str:
    if public_url:
        base = public_url.rstrip("/")
    else:
        proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        base = f"{proto}://{host}"
    if base.startswith("https://"):
        return "wss://" + base.removeprefix("https://")
    if base.startswith("http://"):
        return "ws://" + base.removeprefix("http://")
    return base


def build_router(
    sessions: SessionService,
    agent: AgentOrchestrator,
    ingestion: IngestionPipeline,
    settings: Settings,
) -> APIRouter:
    router = APIRouter()
    tickets = RealtimeTicketStore()

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
    async def realtime_session(
        request: RealtimeSessionRequest, http_request: Request
    ) -> RealtimeSessionResponse:
        if not isinstance(agent.provider, PortkeyProvider):
            raise HTTPException(status_code=503, detail="Realtime provider is unavailable")
        try:
            await sessions.require_active(request.session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        ticket = tickets.issue(request.session_id)
        ws_base = _public_ws_base(http_request, settings.agent_public_url)
        return RealtimeSessionResponse(
            session_id=request.session_id,
            model=settings.portkey_realtime_model,
            ws_url=f"{ws_base}/realtime/ws?ticket={ticket}",
            expires_in=tickets.ttl_seconds,
        )

    @router.websocket("/realtime/ws")
    async def realtime_ws(websocket: WebSocket, ticket: str = "") -> None:
        session_id = tickets.redeem(ticket)
        if session_id is None or not isinstance(agent.provider, PortkeyProvider):
            await websocket.close(code=1008)
            return
        try:
            await sessions.require_active(session_id)
        except ValueError:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        upstream_url, upstream_headers = agent.provider.realtime_connection(
            settings.portkey_realtime_model
        )
        try:
            await proxy_realtime(
                websocket,
                upstream_url,
                upstream_headers,
                partial(
                    build_session_update,
                    turn_detection=settings.realtime_turn_detection,
                ),
                settings.realtime_max_session_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - relay boundary, report to client
            logger.error("realtime_upstream_error session=%s error=%r", session_id, exc)
            await websocket.send_json(
                {"type": "error", "error": {"message": "Realtime service unavailable"}}
            )
        finally:
            if websocket.client_state.name == "CONNECTED":
                await websocket.close()

    @router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(verify_ingest)])
    async def ingest(file: UploadFile = File(...)) -> IngestResponse:
        if file.content_type not in {"text/markdown", "text/plain"}:
            raise HTTPException(status_code=415, detail="Only Markdown files are accepted")
        content = (await file.read(2_000_001)).decode("utf-8", errors="strict")
        count = await ingestion.ingest(file.filename or "document.md", content)
        return IngestResponse(document_name=file.filename or "document.md", chunks=count)

    return router

import asyncio
import json
import logging
import secrets
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

import websockets
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("agent.realtime")

# Events the browser may send upstream. Session configuration (instructions, tools)
# is owned by the server, so client-side ``session.update`` is dropped.
ALLOWED_CLIENT_EVENTS = frozenset({
    "input_audio_buffer.append",
    "input_audio_buffer.commit",
    "input_audio_buffer.clear",
    "conversation.item.create",
    "response.create",
    "response.cancel",
})
CLIENT_MAX_MESSAGE_BYTES = 512 * 1024


class RealtimeTicketStore:
    """Short-lived, single-use tickets that authorize one browser WebSocket.

    Tickets live in process memory, so the service must run with a single worker.
    """

    def __init__(self, ttl_seconds: int = 60) -> None:
        self._ttl = ttl_seconds
        self._tickets: dict[str, tuple[UUID, float]] = {}

    @property
    def ttl_seconds(self) -> int:
        return self._ttl

    def issue(self, session_id: UUID) -> str:
        self._purge()
        ticket = secrets.token_urlsafe(32)
        self._tickets[ticket] = (session_id, time.monotonic() + self._ttl)
        return ticket

    def redeem(self, ticket: str) -> UUID | None:
        entry = self._tickets.pop(ticket, None)
        if entry is None or entry[1] < time.monotonic():
            return None
        return entry[0]

    def _purge(self) -> None:
        now = time.monotonic()
        for ticket in [t for t, (_, exp) in self._tickets.items() if exp < now]:
            del self._tickets[ticket]


async def proxy_realtime(
    client: WebSocket,
    upstream_url: str,
    upstream_headers: dict[str, str],
    build_session_update: Callable[[dict[str, Any]], dict[str, Any]],
    max_duration_seconds: int,
) -> None:
    """Relay events between an accepted browser WebSocket and the Portkey realtime API."""
    async with websockets.connect(
        upstream_url,
        additional_headers=upstream_headers,
        open_timeout=15,
        max_size=None,
    ) as upstream:
        first = await asyncio.wait_for(upstream.recv(), timeout=15)
        await client.send_text(first if isinstance(first, str) else first.decode())
        event = json.loads(first)
        if event.get("type") != "session.created":
            logger.warning("realtime_unexpected_first_event type=%s", event.get("type"))
            return
        await upstream.send(json.dumps(build_session_update(event.get("session") or {})))

        async def client_to_upstream() -> None:
            while True:
                raw = await client.receive_text()
                if len(raw) > CLIENT_MAX_MESSAGE_BYTES:
                    continue
                try:
                    event_type = json.loads(raw).get("type")
                except (ValueError, AttributeError):
                    continue
                if event_type in ALLOWED_CLIENT_EVENTS:
                    await upstream.send(raw)

        async def upstream_to_client() -> None:
            async for message in upstream:
                await client.send_text(message if isinstance(message, str) else message.decode())

        tasks = {
            asyncio.create_task(client_to_upstream()),
            asyncio.create_task(upstream_to_client()),
        }
        done, pending = await asyncio.wait(
            tasks, timeout=max_duration_seconds, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, (WebSocketDisconnect, websockets.ConnectionClosed)):
                logger.error("realtime_relay_error error=%r", exc)

import asyncio
from collections.abc import Sequence
from typing import Any

import httpx
from portkey_ai import Portkey

from app.core.config import Settings

from .base_llm_provider import LLMProvider
from .models import LLMResponse


class PortkeyProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Portkey(
            base_url=settings.base_url,
            api_key=settings.portkey_api_key,
        )

    async def complete(
        self, messages: Sequence[dict[str, str]], *, temperature: float | None = 0.2,
        max_tokens: int = 1200, response_format: dict[str, Any] | None = None,
        model: str | None = None, reasoning_effort: str | None = None,
        max_completion_tokens: int | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": model or self._settings.portkey_model,
            "messages": list(messages),
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_completion_tokens is not None:
            kwargs["max_completion_tokens"] = max_completion_tokens
        else:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        response = await asyncio.to_thread(
            self._client.chat.completions.create, **kwargs
        )
        return LLMResponse(content=response.choices[0].message.content or "", raw=response)

    async def embed(self, text: str) -> list[float]:
        response = await asyncio.to_thread(
            self._client.embeddings.create,
            model="@azure-openai/text-embedding-3-small",
            input=text,
            encoding_format="float",
        )
        return list(response.data[0].embedding)

    async def create_realtime_session(
        self, *, model: str, instructions: str, tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        ws_base = (
            self._settings.base_url.rstrip("/")
            .replace("https://", "wss://")
            .replace("http://", "ws://")
        )
        ws_url = f"{ws_base}/realtime?model={model}"
        return {
            "model": model,
            "ws_url": ws_url,
            "instructions": instructions,
            "tools": tools,
            "client_secret": {
                "value": self._settings.portkey_api_key,
                "expires_at": 0,
            },
        }

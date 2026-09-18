import asyncio
from typing import Any, Sequence
from portkey_ai import AsyncPortkey
from .base_llm_provider import LLMProvider
from .models import LLMResponse
from app.core.config import Settings


class PortkeyProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncPortkey(
            api_key=settings.portkey_api_key,
            virtual_key=settings.portkey_virtual_key,
        )

    async def complete(
        self, messages: Sequence[dict[str, str]], *, temperature: float = 0.2,
        max_tokens: int = 1200, response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._settings.portkey_model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        response = await self._client.chat.completions.create(**kwargs)
        return LLMResponse(content=response.choices[0].message.content or "", raw=response)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._settings.embedding_model, input=text
        )
        return list(response.data[0].embedding)

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from .models import LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self, messages: Sequence[dict[str, str]], *, temperature: float | None = 0.2,
        max_tokens: int = 1200, response_format: dict[str, Any] | None = None,
        model: str | None = None, reasoning_effort: str | None = None,
        max_completion_tokens: int | None = None,
    ) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError

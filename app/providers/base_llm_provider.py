from abc import ABC, abstractmethod
from typing import Any, Sequence
from .models import LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self, messages: Sequence[dict[str, str]], *, temperature: float = 0.2,
        max_tokens: int = 1200, response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError

"""DeepAgents boundary.

The application deliberately exposes only LLMProvider to the agent layer. This
keeps Portkey and the selected Gemini model replaceable and prevents backend
tools from being registered. The orchestration contract is compatible with a
DeepAgents runtime; frontend actions remain a validated output protocol.
"""

from collections.abc import Sequence
from typing import Any
from app.providers.base_llm_provider import LLMProvider
from app.providers.models import LLMResponse


class DeepAgent:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def run(self, messages: Sequence[dict[str, str]], **kwargs: Any) -> LLMResponse:
        return await self.provider.complete(messages, **kwargs)

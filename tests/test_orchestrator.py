from uuid import uuid4

import pytest

from app.agent.orchestrator import AgentOrchestrator
from app.providers.models import LLMResponse


class FakeRepository:
    def __init__(self, chunks: list[dict]) -> None:
        self.chunks = chunks
        self.search_calls: list[tuple[int, float]] = []
        self.messages: list[tuple[str, str]] = []

    async def history(self, session_id):
        return []

    async def search_chunks(self, embedding, top_k, threshold):
        self.search_calls.append((top_k, threshold))
        return self.chunks if len(self.search_calls) == 2 else []

    async def add_message(self, session_id, role, content):
        self.messages.append((role, content))


class FakeProvider:
    def __init__(self) -> None:
        self.embedded_text: str | None = None

    async def embed(self, text):
        self.embedded_text = text
        return [0.1]

    async def complete(self, messages, **kwargs):
        if kwargs.get("model") == "guardrail-model":
            return LLMResponse('{"intent":"IN_SCOPE"}')
        raise AssertionError("not needed for retrieval fallback test")


@pytest.mark.asyncio
async def test_retries_retrieval_with_lower_threshold() -> None:
    repository = FakeRepository([{"chunk_text": "La app permite reportar mascotas."}])
    provider = FakeProvider()
    orchestrator = AgentOrchestrator(repository, provider, 5, 0.72, "guardrail-model")

    with pytest.raises(AssertionError, match="not needed"):
        await orchestrator.respond(uuid4(), "¿Qué funcionalidades tiene la aplicación?")

    assert repository.search_calls == [(5, 0.72), (5, 0.57)]
    assert provider.embedded_text == (
        "funcionalidades de la aplicación FindMyPet: "
        "¿Qué funcionalidades tiene la aplicación?"
    )


@pytest.mark.asyncio
async def test_guardrail_skips_embedding_and_model_for_greeting() -> None:
    repository = FakeRepository([])
    provider = FakeProvider()
    orchestrator = AgentOrchestrator(repository, provider, 5, 0.72, "guardrail-model")

    message, action, payload = await orchestrator.respond(uuid4(), "hola")

    assert message.startswith("¡Hola!")
    assert action is None
    assert payload == {}
    assert repository.search_calls == []

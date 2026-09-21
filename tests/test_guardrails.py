import pytest

from app.agent.guardrails import (
    GuardrailKind,
    classify_intent,
    classify_message,
    retrieval_query,
)
from app.providers.models import LLMResponse


def test_greeting_is_handled_without_rag() -> None:
    decision = classify_message("hola, como estas?")

    assert decision.kind is GuardrailKind.GREETING
    assert decision.response


def test_application_question_is_in_scope() -> None:
    decision = classify_message("cuales son las funcionalidades de la aplicacion?")

    assert decision is None


def test_unrelated_question_is_rejected() -> None:
    decision = classify_message("¿Cómo preparo una receta de pasta?")

    assert decision is None


def test_retrieval_query_removes_greeting_and_anchors_app_intent() -> None:
    assert retrieval_query("hola me gustaria saber que se puede hacer en la app") == (
        "funcionalidades de la aplicación FindMyPet: "
        "me gustaria saber que se puede hacer en la app"
    )


class ClassifierProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.kwargs = {}

    async def complete(self, messages, **kwargs):
        self.kwargs = kwargs
        return LLMResponse(self.response)


@pytest.mark.asyncio
async def test_classifier_uses_low_luna_model_for_mixed_greeting_request() -> None:
    provider = ClassifierProvider('{"intent":"OUT_OF_SCOPE"}')

    assert classify_message("hola, tengo un perrito pero escribe una función en Python") is None
    decision = await classify_intent(provider, "hola, tengo un perrito pero escribe una función en Python", "luna")

    assert decision.kind is GuardrailKind.OUT_OF_SCOPE
    assert provider.kwargs["model"] == "luna"
    assert provider.kwargs["reasoning_effort"] == "low"
    assert provider.kwargs["temperature"] is None
    assert provider.kwargs["max_completion_tokens"] == 20

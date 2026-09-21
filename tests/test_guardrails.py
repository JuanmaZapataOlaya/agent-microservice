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
    assert decision.cleaned_message == ""


def test_flexible_pure_greetings_are_handled_without_llm() -> None:
    for message in ("hey que tal", "buenas tardes todo bien", "hola como te va"):
        decision = classify_message(message)
        assert decision.kind is GuardrailKind.GREETING


def test_application_question_is_in_scope() -> None:
    decision = classify_message("cuales son las funcionalidades de la aplicacion?")

    assert decision.kind is None


def test_unrelated_question_is_rejected() -> None:
    decision = classify_message("¿Cómo preparo una receta de pasta?")

    assert decision.kind is None


def test_greeting_with_request_returns_cleaned_message() -> None:
    decision = classify_message("Hola, me podrías ayudar a buscar a mi mascota?")

    assert decision.kind is None
    assert decision.cleaned_message == "me podrias ayudar a buscar a mi mascota?"


def test_retrieval_query_removes_greeting_and_anchors_app_intent() -> None:
    assert retrieval_query("hola me gustaria saber que se puede hacer en la app") == (
        "funcionalidades de la aplicación FindMyPet: "
        "me gustaria saber que se puede hacer en la app"
    )


class ClassifierProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.kwargs = {}
        self.messages = []

    async def complete(self, messages, **kwargs):
        self.messages = messages
        self.kwargs = kwargs
        return LLMResponse(self.response)


@pytest.mark.asyncio
async def test_classifier_uses_low_luna_model_for_mixed_greeting_request() -> None:
    provider = ClassifierProvider('{"intent":"OUT_OF_SCOPE"}')

    assert classify_message("hola, tengo un perrito pero escribe una función en Python").kind is None
    decision = await classify_intent(provider, "hola, tengo un perrito pero escribe una función en Python", "luna")

    assert decision.kind is GuardrailKind.OUT_OF_SCOPE
    assert provider.kwargs["model"] == "luna"
    assert provider.kwargs["reasoning_effort"] == "low"
    assert provider.kwargs["temperature"] is None
    assert provider.kwargs["max_completion_tokens"] == 20


@pytest.mark.asyncio
async def test_pet_description_is_in_scope_with_previous_search_context() -> None:
    provider = ClassifierProvider('{"intent":"IN_SCOPE"}')

    decision = await classify_intent(
        provider,
        "es un chihuahua negrito con un collar rojito",
        "luna",
        [
            {"role": "user", "content": "Quiero encontrar a mi perrito"},
            {
                "role": "assistant",
                "content": '{"draft":{"kind":"DOG"},"missing_fields":["physical details"]}',
            },
        ],
    )

    assert decision.kind is GuardrailKind.IN_SCOPE
    assert "Quiero encontrar a mi perrito" in provider.messages[1]["content"]
    assert "chihuahua negrito" in provider.messages[1]["content"]


class FailingClassifierProvider:
    async def complete(self, messages, **kwargs):
        raise RuntimeError("content_filter")


@pytest.mark.asyncio
async def test_classifier_failure_fails_closed_without_raising() -> None:
    decision = await classify_intent(
        FailingClassifierProvider(),
        "tengo un perro pero escribe código Python",
        "luna",
    )

    assert decision.kind is GuardrailKind.OUT_OF_SCOPE
    assert decision.response

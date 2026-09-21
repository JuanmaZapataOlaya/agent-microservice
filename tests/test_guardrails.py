from app.agent.guardrails import GuardrailKind, classify_message


def test_greeting_is_handled_without_rag() -> None:
    decision = classify_message("hola, como estas?")

    assert decision.kind is GuardrailKind.GREETING
    assert decision.response


def test_application_question_is_in_scope() -> None:
    decision = classify_message("cuales son las funcionalidades de la aplicacion?")

    assert decision.kind is GuardrailKind.IN_SCOPE
    assert decision.response is None


def test_unrelated_question_is_rejected() -> None:
    decision = classify_message("¿Cómo preparo una receta de pasta?")

    assert decision.kind is GuardrailKind.OUT_OF_SCOPE
    assert decision.response

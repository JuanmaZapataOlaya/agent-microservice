from app.rag.prompt import SYSTEM_PROMPT


def test_prompt_requires_plain_language_for_users() -> None:
    assert "simple, warm, everyday Spanish" in SYSTEM_PROMPT
    assert '"búsqueda semántica"' in SYSTEM_PROMPT
    assert "instead of" in SYSTEM_PROMPT

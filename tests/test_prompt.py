from app.rag.prompt import SYSTEM_PROMPT


def test_prompt_requires_plain_language_for_users() -> None:
    assert "same language as the user's latest message: English or Spanish" in SYSTEM_PROMPT
    assert "the language from both typed text and speech/transcription" in SYSTEM_PROMPT
    assert "Use simple, warm, everyday language in either English or Spanish" in SYSTEM_PROMPT
    assert '"búsqueda semántica"' in SYSTEM_PROMPT
    assert "instead of" in SYSTEM_PROMPT


def test_prompt_transitions_failed_search_to_report_flow() -> None:
    assert "none of the search options or results matched" in SYSTEM_PROMPT
    assert "Do not emit REPORT_PET until type, kind, breed, color, and description are all present" in SYSTEM_PROMPT


def test_prompt_emits_tutorial_action_for_app_functionality_questions() -> None:
    assert "Use RUN_TUTORIAL when the user asks about the app's functionalities" in SYSTEM_PROMPT
    assert '"RUN_TUTORIAL"' in SYSTEM_PROMPT

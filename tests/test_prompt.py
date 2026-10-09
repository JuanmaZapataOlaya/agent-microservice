from app.agent.realtime import REALTIME_INSTRUCTIONS
from app.rag.prompt import SYSTEM_PROMPT, build_messages


def test_prompt_requires_plain_language_for_users() -> None:
    assert "`response_language`, set to `ENGLISH` or `SPANISH`" in SYSTEM_PROMPT
    assert "translate their relevant content into `response_language`" in SYSTEM_PROMPT
    assert "Use simple, warm, everyday language in either English or Spanish" in SYSTEM_PROMPT
    assert '"búsqueda semántica"' in SYSTEM_PROMPT
    assert "instead of" in SYSTEM_PROMPT


def test_text_prompt_passes_explicit_response_language() -> None:
    messages = build_messages([], "How do I report a pet?", [], {}, "ENGLISH")

    assert '"response_language": "ENGLISH"' in messages[-1]["content"]


def test_realtime_prompt_matches_the_latest_spoken_language() -> None:
    assert "latest spoken message" in REALTIME_INSTRUCTIONS
    assert "respond in that same language" in REALTIME_INSTRUCTIONS
    assert "Switch languages whenever the user does" in REALTIME_INSTRUCTIONS


def test_prompt_transitions_failed_search_to_report_flow() -> None:
    assert "none of the search options or results matched" in SYSTEM_PROMPT
    assert "Do not emit REPORT_PET until type, kind, breed, color, and description are all present" in SYSTEM_PROMPT


def test_prompt_emits_tutorial_action_for_app_functionality_questions() -> None:
    assert "Use RUN_TUTORIAL when the user asks about the app's functionalities" in SYSTEM_PROMPT
    assert '"RUN_TUTORIAL"' in SYSTEM_PROMPT

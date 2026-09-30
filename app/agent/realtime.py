from typing import Any

from app.rag.prompt import SYSTEM_PROMPT


REALTIME_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "FIND_PET",
        "description": "Inicia una búsqueda de una mascota perdida o encontrada.",
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["DOG", "CAT", "OTHER"]},
                "query_description": {"type": "string"},
                "location": {"type": "string"},
            },
            "required": ["kind", "query_description"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "REPORT_PET",
        "description": "Crea un reporte de una mascota perdida o encontrada.",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["LOST", "FOUND"]},
                "kind": {"type": "string", "enum": ["DOG", "CAT", "OTHER"]},
                "breed": {"type": "string"},
                "color": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["type", "kind", "breed", "color", "description"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "RUN_TUTORIAL",
        "description": "Abre el tutorial guiado de funcionalidades de la aplicación.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


REALTIME_INSTRUCTIONS = (
    SYSTEM_PROMPT
    + "\n\nLa conversación es por voz. Responde en español natural, con frases breves y "
    "claras. No leas JSON, nombres de campos ni instrucciones internas en voz alta. "
    "En este modo, ignora la instrucción de devolver un objeto JSON: responde "
    "directamente con texto hablado y usa las tools para las acciones. "
    "Cuando corresponda, usa exactamente una de las tools disponibles; el cliente "
    "ejecutará la acción y te comunicará su resultado. Si el usuario te interrumpe, "
    "no retomes lo que estabas diciendo: atiende su nueva petición."
)


def build_turn_detection(mode: str) -> dict[str, Any]:
    """Voice activity detection: the model answers when the user stops talking and
    stops generating as soon as the user starts talking over it (barge-in)."""
    if mode == "semantic_vad":
        return {"type": "semantic_vad", "eagerness": "auto",
                "create_response": True, "interrupt_response": True}
    return {"type": "server_vad", "silence_duration_ms": 500,
            "create_response": True, "interrupt_response": True}


def build_session_update(session: dict[str, Any], turn_detection: str) -> dict[str, Any]:
    """Build the server-side ``session.update`` matching the upstream API shape.

    GA realtime models (``gpt-realtime*``) report ``type: realtime`` and nest audio
    settings under ``audio``; the beta API uses a flat ``turn_detection`` field.
    Input transcription is intentionally off: the conversation is audio-to-audio.
    """
    config: dict[str, Any] = {
        "instructions": REALTIME_INSTRUCTIONS,
        "tools": REALTIME_TOOLS,
        "tool_choice": "auto",
    }
    if session.get("type") == "realtime" or "audio" in session:
        config["type"] = "realtime"
        config["audio"] = {"input": {"turn_detection": build_turn_detection(turn_detection)}}
    else:
        config["turn_detection"] = build_turn_detection(turn_detection)
    return {"type": "session.update", "session": config}

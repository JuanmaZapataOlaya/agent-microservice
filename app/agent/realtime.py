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
                "type": {"type": "string", "enum": ["LOST", "FOUND"],
                         "description": "Si busca mascotas perdidas o encontradas. Omítelo si no lo dijo."},
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
    {
        "type": "function",
        "name": "NAVIGATE",
        "description": "Lleva al usuario a una sección de la aplicación.",
        "parameters": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": ["SUMMARY", "EXPLORE", "MATCHES", "MY_REPORTS",
                             "NOTIFICATIONS", "PET_HISTORY", "PERSONAL_INFO"],
                },
            },
            "required": ["section"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "SCROLL",
        "description": "Desplaza la página actual hacia arriba, abajo, al inicio o al final.",
        "parameters": {
            "type": "object",
            "properties": {"direction": {"type": "string", "enum": ["UP", "DOWN", "TOP", "BOTTOM"]}},
            "required": ["direction"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "OPEN_MODAL",
        "description": "Abre una ventana: el formulario vacío para reportar una mascota o la "
                       "confirmación del tutorial.",
        "parameters": {
            "type": "object",
            "properties": {"modal": {"type": "string", "enum": ["REPORT_FORM", "TUTORIAL"]}},
            "required": ["modal"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "CLOSE_MODAL",
        "description": "Cierra la ventana o diálogo que esté abierto en pantalla.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "MANAGE_NOTIFICATION",
        "description": "Consulta o gestiona las notificaciones del usuario. Usa LIST para conocerlas "
                       "antes de actuar sobre una. position es la posición (desde 1) en esa lista. "
                       "REPORT abre el formulario de reporte; reason lo rellena si el usuario dio un motivo.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string",
                           "enum": ["LIST", "MARK_READ", "MARK_UNREAD", "FINALIZE", "REPORT"]},
                "position": {"type": "integer", "minimum": 1},
                "reason": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    },
]


REALTIME_INSTRUCTIONS = (
    SYSTEM_PROMPT
    + "\n\nThis is a voice conversation. Identify whether the user's latest spoken message "
    "is in English or Spanish and respond in that same language. Switch languages whenever "
    "the user does. Keep spoken replies brief and clear. Do not read JSON, field names, or "
    "internal instructions aloud. Ignore the JSON-output requirement in this voice mode: "
    "reply directly with spoken text and use the tools for actions. "
    "Cuando corresponda, usa exactamente una de las tools disponibles; el cliente "
    "ejecutará la acción y te comunicará su resultado; si el resultado indica un error, "
    "explícaselo al usuario en pocas palabras. Antes de marcar como finalizada una "
    "notificación, confirma con el usuario porque la quita de la lista. Si el usuario te interrumpe, "
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

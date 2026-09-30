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
    "ejecutará la acción y te comunicará su resultado."
)


def build_session_update(session: dict[str, Any], transcription_model: str) -> dict[str, Any]:
    """Build the server-side ``session.update`` matching the upstream API shape.

    GA realtime models (``gpt-realtime*``) report ``type: realtime`` and nest audio
    settings under ``audio``; the beta API uses flat ``input_audio_*`` fields.
    """
    config: dict[str, Any] = {
        "instructions": REALTIME_INSTRUCTIONS,
        "tools": REALTIME_TOOLS,
        "tool_choice": "auto",
    }
    if session.get("type") == "realtime" or "audio" in session:
        config["type"] = "realtime"
        config["audio"] = {
            "input": {
                "transcription": {"model": transcription_model},
                "turn_detection": {"type": "server_vad"},
            }
        }
    else:
        config["input_audio_transcription"] = {"model": transcription_model}
        config["turn_detection"] = {"type": "server_vad"}
    return {"type": "session.update", "session": config}

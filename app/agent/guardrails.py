import json
import re
import unicodedata
from enum import Enum

from app.providers.base_llm_provider import LLMProvider


class GuardrailKind(Enum):
    IN_SCOPE = "in_scope"
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"


class GuardrailDecision:
    def __init__(self, kind: GuardrailKind, response: str | None = None) -> None:
        self.kind = kind
        self.response = response


_GREETING_PATTERN = re.compile(
    r"^(?:hola[,\s]+como\s+estas|hola|holi|hello|hey|buen(?:os|as)\s+dias|buenas(?:\s+tardes|\s+noches)?"
    r"|que\s+tal|como\s+estas|gracias|muchas\s+gracias|adios"
    r"|hasta\s+luego)[!,.?\s]*$",
    re.IGNORECASE,
)
_LEADING_GREETING_PATTERN = re.compile(
    r"^\s*(?:hola|holi|hello|hey|buenos?\s+dias|buenas(?:\s+tardes|\s+noches)?)"
    r"(?:[\s,!.:;-]+|$)",
    re.IGNORECASE,
)
_APP_INTENT_PATTERN = re.compile(
    r"\b(?:app|aplicacion\w*|plataform\w*|funcionalidad\w*|funcion\w*)\b",
    re.IGNORECASE,
)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower().strip()


def classify_message(message: str) -> GuardrailDecision | None:
    normalized = _normalize(message)
    if _GREETING_PATTERN.fullmatch(normalized):
        return GuardrailDecision(
            GuardrailKind.GREETING,
            "¡Hola! Soy el asistente de FindMyPet. Puedo ayudarte con mascotas y con las funcionalidades de la aplicación.",
        )
    return None


CLASSIFIER_SYSTEM_PROMPT = """Classify the user's overall intent for the FindMyPet assistant.
Return only valid JSON with exactly one key: {"intent":"IN_SCOPE"} or {"intent":"OUT_OF_SCOPE"}.
IN_SCOPE means the user wants help with FindMyPet, lost/found pets, pet reports, searching pets,
or the application's features.
OUT_OF_SCOPE means code, programming, homework, academic tasks, cybersecurity, general knowledge,
writing tasks, or any unrelated request, even if it mentions a dog, cat, pet, or FindMyPet.
Judge the complete request, not isolated keywords. When uncertain, return OUT_OF_SCOPE."""


async def classify_intent(
    provider: LLMProvider,
    message: str,
    model: str,
) -> GuardrailDecision:
    try:
        response = await provider.complete(
            [
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=None,
            max_completion_tokens=20,
            response_format={"type": "json_object"},
            model=model,
            reasoning_effort="low",
        )
        intent = json.loads(response.content).get("intent")
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        intent = "OUT_OF_SCOPE"

    if intent == GuardrailKind.IN_SCOPE.name:
        return GuardrailDecision(GuardrailKind.IN_SCOPE)
    return GuardrailDecision(
        GuardrailKind.OUT_OF_SCOPE,
        "Puedo ayudarte únicamente con mascotas y con las funcionalidades de FindMyPet. ¿Qué necesitas?",
    )


def retrieval_query(message: str) -> str:
    """Remove conversational noise and anchor app questions to the knowledge domain."""
    query = _LEADING_GREETING_PATTERN.sub("", message).strip()
    if _APP_INTENT_PATTERN.search(query):
        return f"funcionalidades de la aplicación FindMyPet: {query}"
    return query or message

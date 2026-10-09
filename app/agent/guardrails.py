import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from portkey_ai._vendor.openai import APIError

from app.providers.base_llm_provider import LLMProvider

logger = logging.getLogger("agent.guardrails")


class GuardrailKind(Enum):
    IN_SCOPE = "in_scope"
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True)
class GuardrailDecision:
    kind: GuardrailKind | None
    response: str | None = None
    cleaned_message: str = ""
    language: str | None = None


_GREETING_UNIT = (
    r"(?:hola|holi|hey|hello|hi|"
    r"good\s+(?:morning|afternoon|evening)|how\s+are\s+you|"
    r"thanks|thank\s+you|bye|goodbye|"
    r"que\s+tal|que\s+mas|"
    r"buenas?(?:\s+(?:dias|tardes|noches))?|"
    r"como\s+estas|como\s+te\s+va|como\s+andas|todo\s+bien|"
    r"que\s+haces|que\s+pasa|gracias|muchas\s+gracias|"
    r"chao|adios|hasta\s+luego)"
)
_GREETING_SEPARATOR = r"[\s,!.?:;-]+"
_PURE_GREETING_PATTERN = re.compile(
    rf"^{_GREETING_UNIT}(?:{_GREETING_SEPARATOR}{_GREETING_UNIT})*[\s,!.?:;-]*$",
    re.IGNORECASE,
)
_LEADING_GREETING_PATTERN = re.compile(
    rf"^\s*{_GREETING_UNIT}(?:{_GREETING_SEPARATOR}{_GREETING_UNIT})*"
    rf"{_GREETING_SEPARATOR}+",
    re.IGNORECASE,
)
_APP_INTENT_PATTERN = re.compile(
    r"\b(?:app|aplicacion\w*|plataform\w*|funcionalidad\w*|funcion\w*)\b",
    re.IGNORECASE,
)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower().strip()


def detect_language(message: str) -> str:
    """Return ENGLISH or SPANISH for short guardrail and fallback responses."""
    normalized = _normalize(message)
    english_markers = {
        "a", "about", "and", "are", "can", "do", "find", "for", "found", "good",
        "hello", "help", "hi", "how", "i", "is", "it", "looking", "lost", "my",
        "of", "please", "the", "there", "thanks", "thank", "what", "where", "with",
        "you",
    }
    spanish_markers = {
        "ayuda", "busco", "buscar", "como", "de", "donde", "el", "es", "esta",
        "hola", "la", "mascota", "mi", "necesito", "perdida", "perro", "que",
        "quiero", "una", "un",
    }
    words = set(re.findall(r"[a-z]+", normalized))
    return "ENGLISH" if len(words & english_markers) > len(words & spanish_markers) else "SPANISH"


def classify_message(message: str) -> GuardrailDecision:
    normalized = _normalize(message)
    if _PURE_GREETING_PATTERN.fullmatch(normalized):
        if detect_language(normalized) == "ENGLISH":
            return GuardrailDecision(
                kind=GuardrailKind.GREETING,
                response="Hi! I'm the FindMyPet assistant. I can help you with pets and the app's features.",
                cleaned_message="",
            )
        return GuardrailDecision(
            kind=GuardrailKind.GREETING,
            response="¡Hola! Soy el asistente de FindMyPet. Puedo ayudarte con mascotas y con las funcionalidades de la aplicación.",
            cleaned_message="",
        )
    cleaned = _LEADING_GREETING_PATTERN.sub("", normalized, count=1).strip()
    return GuardrailDecision(kind=None, cleaned_message=cleaned or normalized)


CLASSIFIER_SYSTEM_PROMPT = """Classify the user's overall intent for the FindMyPet assistant.
Return only valid JSON with exactly these keys: "intent" (IN_SCOPE or OUT_OF_SCOPE) and
"language" (ENGLISH or SPANISH, based on the latest user message).
IN_SCOPE means the user wants help with FindMyPet, lost/found pets, pet reports, searching pets,
or the application's features. Pet descriptions and follow-up answers are also IN_SCOPE even
when they do not repeat the word pet: breed names (chihuahua, husky, labrador), species,
colors, sizes, collars, accessories, markings, locations, or phrases such as "es negro",
"tiene un collar rojo", "es pequeño" or "lo vi en el parque" are valid pet-search/report details.
If the recent conversation is already about finding or reporting a pet, interpret a short
description as a continuation of that same pet flow.
OUT_OF_SCOPE means code, programming, homework, academic tasks, cybersecurity, general knowledge,
writing tasks, or any unrelated request, even if it mentions a dog, cat, pet, or FindMyPet.
Judge the complete request and recent conversation, not isolated keywords. Reject only when the
overall intent is clearly unrelated. When there is no useful context and the request is ambiguous,
return OUT_OF_SCOPE."""


async def classify_intent(
    provider: LLMProvider,
    message: str,
    model: str,
    history: list[dict] | None = None,
) -> GuardrailDecision:
    conversation = ""
    if history:
        recent = history[-10:]
        conversation = "\n".join(
            f"{item.get('role', 'unknown')}: {item.get('content', '')}"
            for item in recent
        )
    user_content = (
        f"Recent conversation:\n{conversation}\n\nLatest user message:\n{message}"
        if conversation
        else message
    )
    try:
        response = await provider.complete(
            [
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=None,
            max_completion_tokens=20,
            response_format={"type": "json_object"},
            model=model,
            reasoning_effort="low",
        )
        result = json.loads(response.content)
        intent = result.get("intent")
        language = result.get("language")
        if language not in {"ENGLISH", "SPANISH"}:
            language = detect_language(message)
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        intent = "OUT_OF_SCOPE"
        language = detect_language(message)
    except (APIError, TimeoutError, RuntimeError) as exc:
        logger.warning(
            "guardrail_provider_error model=%s error_type=%s",
            model,
            type(exc).__name__,
        )
        intent = "OUT_OF_SCOPE"
        language = detect_language(message)

    if intent == GuardrailKind.IN_SCOPE.name:
        return GuardrailDecision(GuardrailKind.IN_SCOPE, language=language)
    return GuardrailDecision(
        GuardrailKind.OUT_OF_SCOPE,
        (
            "I can only help with pets and FindMyPet features. What do you need?"
            if language == "ENGLISH"
            else "Puedo ayudarte únicamente con mascotas y con las funcionalidades de FindMyPet. ¿Qué necesitas?"
        ),
        language=language,
    )


def retrieval_query(message: str) -> str:
    """Remove conversational noise and anchor app questions to the knowledge domain."""
    query = _LEADING_GREETING_PATTERN.sub("", message).strip()
    if _APP_INTENT_PATTERN.search(_normalize(query)):
        return f"funcionalidades de la aplicación FindMyPet: {query}"
    return query or message

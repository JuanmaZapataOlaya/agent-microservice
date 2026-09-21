import re
import unicodedata
from enum import Enum


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
_DOMAIN_PATTERN = re.compile(
    r"\b(?:mascot\w*|perr\w*|gat\w*|animal\w*|app|aplicacion\w*|plataform\w*"
    r"|funcionalidad\w*|report\w*|perdid\w*|encontrad\w*|busc\w*|hallad\w*"
    r"|contact\w*|evidenci\w*|fotograf\w*|duen\w*|reclam\w*|notificacion\w*"
    r"|historial\w*|usuari\w*|ayud\w*|informacion\w*|funcion\w*)\b",
    re.IGNORECASE,
)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower().strip()


def classify_message(message: str) -> GuardrailDecision:
    normalized = _normalize(message)
    if _GREETING_PATTERN.fullmatch(normalized):
        return GuardrailDecision(
            GuardrailKind.GREETING,
            "¡Hola! Soy el asistente de FindMyPet. Puedo ayudarte con mascotas y con las funcionalidades de la aplicación.",
        )
    if not _DOMAIN_PATTERN.search(normalized):
        return GuardrailDecision(
            GuardrailKind.OUT_OF_SCOPE,
            "Puedo ayudarte únicamente con mascotas y con las funcionalidades de FindMyPet. ¿Qué necesitas saber?",
        )
    return GuardrailDecision(GuardrailKind.IN_SCOPE)

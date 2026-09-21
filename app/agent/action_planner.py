import json
import re
from typing import Any

from app.models.schemas import ActionPlan

ALLOWED_ACTIONS = {"FIND_PET", "REPORT_PET"}
VALID_KINDS = {"DOG", "CAT", "OTHER"}
VALID_REPORT_TYPES = {"LOST", "FOUND"}
FIND_PHYSICAL_FIELDS = ("breed", "color", "features", "accessories", "description", "note")


def parse_action_plan(content: str) -> ActionPlan:
    try:
        raw: Any = json.loads(_extract_json(content))
        raw = _normalize_plan(raw)
        plan = ActionPlan.model_validate(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("LLM returned an invalid action plan") from exc
    if plan.action is not None and plan.action not in ALLOWED_ACTIONS:
        raise ValueError("Action is not in the allowlist")
    return apply_slot_filling(plan)


def apply_slot_filling(plan: ActionPlan) -> ActionPlan:
    if plan.action == "FIND_PET":
        return _validate_find_pet(plan)
    if plan.action == "REPORT_PET":
        return _validate_report_pet(plan)
    return plan


def _validate_find_pet(plan: ActionPlan) -> ActionPlan:
    payload = dict(plan.payload)
    missing: list[str] = []
    if payload.get("kind") not in VALID_KINDS:
        missing.append("kind")
    if not any(_has_value(payload.get(field)) for field in FIND_PHYSICAL_FIELDS):
        missing.append("breed_or_color_or_features")

    if missing:
        return _request_missing(
            plan,
            payload,
            missing,
            "¿De qué raza o color es, o tiene alguna marca o accesorio distintivo?",
        )

    query_description = payload.get("query_description")
    if not _has_value(query_description):
        physical_values = [
            str(payload[field]) for field in FIND_PHYSICAL_FIELDS if _has_value(payload.get(field))
        ]
        payload["query_description"] = _limit_words(" ".join(physical_values), 10)
    elif len(str(query_description).split()) > 10:
        return _request_missing(
            plan,
            payload,
            ["query_description"],
            "¿Puedes resumir las características físicas en máximo 10 palabras?",
        )
    return plan.model_copy(update={"payload": payload})


def _validate_report_pet(plan: ActionPlan) -> ActionPlan:
    payload = dict(plan.payload)
    missing = [
        field for field in ("type", "kind", "description")
        if not _has_value(payload.get(field))
    ]
    if payload.get("type") not in VALID_REPORT_TYPES and "type" not in missing:
        missing.append("type")
    if payload.get("kind") not in VALID_KINDS and "kind" not in missing:
        missing.append("kind")
    if missing:
        next_field = missing[0]
        questions = {
            "type": "¿La mascota está perdida o fue encontrada?",
            "kind": "¿Qué especie es: perro, gato u otra?",
            "description": "¿De qué color, raza o características físicas es?",
        }
        return _request_missing(plan, payload, missing, questions[next_field])
    return plan.model_copy(update={"payload": payload})


def _request_missing(
    plan: ActionPlan,
    payload: dict[str, Any],
    missing: list[str],
    message: str,
) -> ActionPlan:
    return plan.model_copy(
        update={
            "message": message,
            "action": None,
            "payload": {"draft": payload, "missing_fields": missing},
        }
    )


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _limit_words(value: str, limit: int) -> str:
    return " ".join(re.findall(r"\S+", value)[:limit])


def _normalize_plan(raw: Any) -> Any:
    if not isinstance(raw, dict):
        return raw

    if isinstance(raw.get("response"), dict):
        raw = raw["response"]
    elif isinstance(raw.get("result"), dict):
        raw = raw["result"]

    normalized = dict(raw)
    if normalized.get("action") == "":
        normalized["action"] = None
    if normalized.get("payload") is None:
        normalized["payload"] = {}
    return normalized


def _extract_json(content: str) -> str:
    normalized = content.strip()
    if normalized.startswith("```") and normalized.endswith("```"):
        lines = normalized.splitlines()
        if len(lines) < 3:
            raise ValueError("LLM returned an empty JSON code block")
        normalized = "\n".join(lines[1:-1]).strip()

    try:
        json.loads(normalized)
        return normalized
    except json.JSONDecodeError:
        start = normalized.find("{")
        end = normalized.rfind("}")
        if start < 0 or end <= start:
            raise
        candidate = normalized[start:end + 1]
        json.loads(candidate)
        return candidate

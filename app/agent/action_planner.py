import json
from typing import Any
from app.models.schemas import ActionPlan

ALLOWED_ACTIONS = {"OPEN_HOTEL_MODULE", "OPEN_PET_PROFILE", "CONTACT_SUPPORT"}


def parse_action_plan(content: str) -> ActionPlan:
    try:
        raw: Any = json.loads(_extract_json(content))
        raw = _normalize_plan(raw)
        plan = ActionPlan.model_validate(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("LLM returned an invalid action plan") from exc
    if plan.action is not None and plan.action not in ALLOWED_ACTIONS:
        raise ValueError("Action is not in the allowlist")
    if plan.action is None:
        plan.payload = {}
    return plan


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

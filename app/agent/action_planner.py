import json
from typing import Any
from app.models.schemas import ActionPlan

ALLOWED_ACTIONS = {"OPEN_HOTEL_MODULE", "OPEN_PET_PROFILE", "CONTACT_SUPPORT"}


def parse_action_plan(content: str) -> ActionPlan:
    try:
        raw: Any = json.loads(content)
        plan = ActionPlan.model_validate(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("LLM returned an invalid action plan") from exc
    if plan.action is not None and plan.action not in ALLOWED_ACTIONS:
        raise ValueError("Action is not in the allowlist")
    if plan.action is None:
        plan.payload = {}
    return plan

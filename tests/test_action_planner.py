import json

import pytest

from app.agent.action_planner import parse_action_plan


def test_parser_accepts_find_pet_action() -> None:
    plan = parse_action_plan(json.dumps({
        "message": "Voy a buscar mascotas con esos datos.",
        "action": "FIND_PET",
        "payload": {"kind": "DOG", "location": "Bogotá"},
    }))

    assert plan.action == "FIND_PET"
    assert plan.payload == {"kind": "DOG", "location": "Bogotá"}


def test_parser_accepts_report_pet_action_with_partial_payload() -> None:
    plan = parse_action_plan(json.dumps({
        "message": "Puedo ayudarte a crear el reporte.",
        "action": "REPORT_PET",
        "payload": {"color": "blanco"},
    }))

    assert plan.action == "REPORT_PET"
    assert plan.payload == {"color": "blanco"}


def test_parser_rejects_unknown_actions_and_internal_identifiers() -> None:
    with pytest.raises(ValueError, match="LLM returned an invalid action plan"):
        parse_action_plan(json.dumps({
            "message": "ok",
            "action": "OPEN_PET_PROFILE",
            "payload": {},
        }))

    with pytest.raises(ValueError, match="LLM returned an invalid action plan"):
        parse_action_plan(json.dumps({
            "message": "ok",
            "action": None,
            "payload": {},
            "session_id": "invented",
        }))

import json

import pytest

from app.agent.action_planner import parse_action_plan


def test_parser_accepts_find_pet_action() -> None:
    plan = parse_action_plan(json.dumps({
        "message": "Voy a buscar mascotas con esos datos.",
        "action": "FIND_PET",
        "payload": {"kind": "DOG", "location": "Bogotá", "color": "blanco"},
    }))

    assert plan.action == "FIND_PET"
    assert plan.payload["query_description"] == "blanco"


def test_parser_accepts_report_pet_action_with_partial_payload() -> None:
    plan = parse_action_plan(json.dumps({
        "message": "Puedo ayudarte a crear el reporte.",
        "action": "REPORT_PET",
        "payload": {"color": "blanco"},
    }))

    assert plan.action is None
    assert plan.payload == {
        "draft": {"color": "blanco"},
        "missing_fields": ["type", "kind", "description"],
    }


def test_find_pet_without_physical_detail_becomes_slot_question() -> None:
    plan = parse_action_plan(json.dumps({
        "message": "Voy a buscar tu perro.",
        "action": "FIND_PET",
        "payload": {"kind": "DOG"},
    }))

    assert plan.action is None
    assert plan.payload["draft"] == {"kind": "DOG"}
    assert plan.payload["missing_fields"] == ["breed_or_color_or_features"]


def test_report_pet_is_emitted_only_when_required_slots_are_complete() -> None:
    plan = parse_action_plan(json.dumps({
        "message": "Abriré el reporte.",
        "action": "REPORT_PET",
        "payload": {
            "type": "FOUND",
            "kind": "CAT",
            "description": "Gato gris con collar rojo",
        },
    }))

    assert plan.action == "REPORT_PET"


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

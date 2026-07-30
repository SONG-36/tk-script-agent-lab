from tk_script_agent_lab.langgraph_app.nodes import (
    generate_creative_ideas,
    validate_creative_ideas,
    validate_input,
    validate_manual_insights,
)
from tk_script_agent_lab.workflow import WorkflowStatus

from phase_1c_helpers import load_studio_input


def test_validate_input_converts_studio_input_to_workflow_input() -> None:
    state = validate_input(load_studio_input())

    assert state["status"] == WorkflowStatus.READY
    assert state["workflow_input"].run_id == "run_car_vacuum_phase_1c_studio"
    assert state["step_records"][0].step_name == "validate_input"


def test_validate_input_rejects_invalid_product_fact() -> None:
    graph_input = load_studio_input()
    graph_input["product_facts"][0]["product_id"] = "other_product"

    state = validate_input(graph_input)

    assert state["status"] == WorkflowStatus.INPUT_INVALID
    assert "WORKFLOW_INPUT_INVALID" in [error.code for error in state["validation_errors"]]
    assert "PRODUCT_ID_MISMATCH" in [error.code for error in state["validation_errors"]]


def test_validate_manual_insights_rejects_missing_reference_video() -> None:
    state = validate_input(load_studio_input())
    state["reference_insights"][0].reference_video_id = "missing_video"

    checked = validate_manual_insights(state)

    assert checked["status"] == WorkflowStatus.FAILED
    assert "REFERENCE_VIDEO_NOT_FOUND" in [
        error.code for error in checked["validation_errors"]
    ]


def test_generate_and_validate_creative_ideas_returns_two_fixed_ideas() -> None:
    state = validate_input(load_studio_input())
    state.update(validate_manual_insights(state))
    state.update(generate_creative_ideas(state))

    assert [idea.creative_idea_id for idea in state["creative_ideas"]] == [
        "idea_before_after_cleanup",
        "idea_driver_cleanup_moment",
    ]

    state.update(validate_creative_ideas(state))
    assert state["status"] == WorkflowStatus.AWAITING_IDEA_SELECTION
    assert state["validation_errors"] == []


def test_step_records_are_continuous_after_creative_validation() -> None:
    state = validate_input(load_studio_input())
    state.update(validate_manual_insights(state))
    state.update(generate_creative_ideas(state))
    state.update(validate_creative_ideas(state))

    assert [record.sequence for record in state["step_records"]] == list(
        range(1, len(state["step_records"]) + 1)
    )

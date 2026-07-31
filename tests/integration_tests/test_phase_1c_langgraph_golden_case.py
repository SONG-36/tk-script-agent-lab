import json

from langgraph.types import Command

from tk_script_agent_lab.workflow import WorkflowStatus, start_workflow
from tk_script_agent_lab.golden_case import load_golden_case
from tk_script_agent_lab.providers import FakeContentProvider

from tests.unit_tests.phase_1c_helpers import (
    approved_resume,
    load_studio_input,
    make_graph,
    studio_input_path,
    thread_config,
)


def test_phase_1c_studio_input_end_to_end() -> None:
    graph = make_graph()
    config = thread_config("phase-1c-e2e")
    first = graph.invoke(load_studio_input(), config=config)

    payload = first["__interrupt__"][0].value
    assert payload["type"] == "IDEA_SELECTION_REQUIRED"
    selected_id = payload["creative_ideas"][0]["creative_idea_id"]

    completed = graph.invoke(Command(resume=approved_resume(selected_id)), config=config)

    assert completed["status"] == WorkflowStatus.COMPLETED
    assert completed["script_draft"].creative_idea_id == selected_id
    assert completed["script_draft"].product_id == "prod_car_vacuum_schema_fixture"
    assert completed["validation_errors"] == []
    json.dumps(_jsonable(completed))
    assert "provider" not in completed


def test_phase_1c_uses_manual_reference_insight_from_studio_input() -> None:
    graph_input = load_studio_input()

    assert graph_input["reference_insights"][0]["insight_id"] == "insight_car_mess_hook"
    assert "creative_ideas" not in graph_input
    assert "script_draft" not in graph_input
    assert studio_input_path().name == "studio_input.json"


def test_phase_1b_python_workflow_still_runs() -> None:
    case_dir = studio_input_path().parent
    workflow_input, fixtures, _reviews = load_golden_case(case_dir)
    state = start_workflow(workflow_input, FakeContentProvider(fixtures))

    assert state.status == WorkflowStatus.AWAITING_IDEA_SELECTION
    assert state.script_draft is None


def test_phase_1c_step_records_explain_full_chain() -> None:
    graph = make_graph()
    config = thread_config("phase-1c-step-records")
    first = graph.invoke(load_studio_input(), config=config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]
    completed = graph.invoke(Command(resume=approved_resume(selected_id)), config=config)

    assert [record.step_name for record in completed["step_records"]] == [
        "validate_input",
        "validate_manual_insights",
        "select_creative_knowledge",
        "generate_creative_ideas",
        "validate_creative_ideas",
        "human_select_idea",
        "apply_human_review",
        "generate_script",
        "validate_script",
        "finalize_result",
    ]


def _jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items() if key != "__interrupt__"}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value

from tk_script_agent_lab.langgraph_app.state import GraphInputState, GraphOutputState
from tk_script_agent_lab.workflow import WorkflowStatus

from phase_1c_helpers import load_studio_input


def test_graph_input_state_accepts_studio_input() -> None:
    graph_input = GraphInputState.model_validate(load_studio_input())

    assert graph_input.run_id == "run_car_vacuum_phase_1c_studio"
    assert len(graph_input.reference_insights) == 1


def test_graph_output_state_is_json_serializable() -> None:
    output = GraphOutputState(
        run_id="run_1",
        status=WorkflowStatus.FAILED,
        creative_ideas=[],
        selected_idea_id=None,
        idea_review=None,
        script_draft=None,
        validation_errors=[],
        step_records=[],
    )

    assert output.model_dump(mode="json")["status"] == "FAILED"

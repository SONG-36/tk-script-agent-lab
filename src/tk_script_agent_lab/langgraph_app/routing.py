from langgraph.graph import END

from tk_script_agent_lab.langgraph_app.state import GraphState
from tk_script_agent_lab.workflow import WorkflowStatus


def route_after_validate_input(state: GraphState) -> str:
    if state.get("status") == WorkflowStatus.INPUT_INVALID:
        return END
    return "validate_manual_insights"


def route_after_validate_manual_insights(state: GraphState) -> str:
    if state.get("status") == WorkflowStatus.FAILED:
        return END
    return "generate_creative_ideas"


def route_after_validate_creative_ideas(state: GraphState) -> str:
    if state.get("status") == WorkflowStatus.FAILED:
        return END
    return "human_select_idea"


def route_after_apply_human_review(state: GraphState) -> str:
    status = state.get("status")
    if status == WorkflowStatus.READY:
        return "generate_script"
    if status == WorkflowStatus.AWAITING_IDEA_SELECTION:
        return "human_select_idea"
    return "finalize_result"

from typing import Literal

from tk_script_agent_lab.langgraph_app.state import GraphState
from tk_script_agent_lab.workflow import WorkflowStatus


def route_after_validate_input(
    state: GraphState,
) -> Literal["input_valid", "input_invalid"]:
    if state.get("status") == WorkflowStatus.INPUT_INVALID:
        return "input_invalid"
    return "input_valid"


def route_after_validate_manual_insights(
    state: GraphState,
) -> Literal["manual_insights_valid", "manual_insights_invalid"]:
    if state.get("status") == WorkflowStatus.FAILED:
        return "manual_insights_invalid"
    return "manual_insights_valid"


def route_after_validate_creative_ideas(
    state: GraphState,
) -> Literal["creative_ideas_valid", "creative_ideas_invalid"]:
    if state.get("status") == WorkflowStatus.FAILED:
        return "creative_ideas_invalid"
    return "creative_ideas_valid"


def route_after_generate_creative_ideas(
    state: GraphState,
) -> Literal["generation_valid", "generation_failed"]:
    if state.get("status") == WorkflowStatus.FAILED:
        return "generation_failed"
    return "generation_valid"


def route_after_apply_human_review(
    state: GraphState,
) -> Literal["approved", "pending", "terminal"]:
    status = state.get("status")
    if status == WorkflowStatus.READY:
        return "approved"
    if status == WorkflowStatus.AWAITING_IDEA_SELECTION:
        return "pending"
    return "terminal"

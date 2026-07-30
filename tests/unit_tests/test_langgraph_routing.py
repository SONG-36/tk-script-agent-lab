import json

from tk_script_agent_lab.langgraph_app.graph import build_graph
from tk_script_agent_lab.langgraph_app.routing import (
    route_after_apply_human_review,
    route_after_validate_creative_ideas,
    route_after_validate_input,
    route_after_validate_manual_insights,
)
from tk_script_agent_lab.workflow import WorkflowStatus


def test_graph_imports_and_compiles() -> None:
    graph = build_graph()

    assert graph is not None


def test_graph_nodes_match_expected_names() -> None:
    graph = build_graph()
    nodes = set(graph.builder.nodes)

    assert {
        "validate_input",
        "validate_manual_insights",
        "generate_creative_ideas",
        "validate_creative_ideas",
        "human_select_idea",
        "apply_human_review",
        "generate_script",
        "validate_script",
        "finalize_result",
    }.issubset(nodes)


def test_conditional_edges_exist() -> None:
    graph = build_graph()

    assert set(graph.builder.branches) == {
        "validate_input",
        "validate_manual_insights",
        "validate_creative_ideas",
        "apply_human_review",
    }


def test_langgraph_json_points_to_real_graph() -> None:
    with open("langgraph.json", encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["graphs"]["agent"] == "./src/tk_script_agent_lab/langgraph_app/graph.py:graph"


def test_routing_functions_return_expected_targets() -> None:
    assert route_after_validate_input({"status": WorkflowStatus.INPUT_INVALID}) == "__end__"
    assert route_after_validate_input({"status": WorkflowStatus.READY}) == "validate_manual_insights"
    assert route_after_validate_manual_insights({"status": WorkflowStatus.FAILED}) == "__end__"
    assert route_after_validate_creative_ideas({"status": WorkflowStatus.FAILED}) == "__end__"
    assert route_after_apply_human_review({"status": WorkflowStatus.READY}) == "generate_script"
    assert route_after_apply_human_review({"status": WorkflowStatus.AWAITING_IDEA_SELECTION}) == "human_select_idea"

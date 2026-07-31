import json

from tk_script_agent_lab.langgraph_app.graph import build_graph
from tk_script_agent_lab.langgraph_app.routing import (
    route_after_apply_human_review,
    route_after_generate_creative_ideas,
    route_after_select_creative_knowledge,
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
        "select_creative_knowledge",
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
        "select_creative_knowledge",
        "generate_creative_ideas",
        "validate_creative_ideas",
        "apply_human_review",
    }


def test_compiled_graph_static_topology_contains_expected_edges() -> None:
    graph = build_graph()
    edges = {
        (edge.source, edge.target, edge.data, edge.conditional)
        for edge in graph.get_graph().edges
    }

    assert {
        ("__start__", "validate_input", None, False),
        ("validate_input", "__end__", "input_invalid", True),
        ("validate_input", "validate_manual_insights", "input_valid", True),
        ("validate_manual_insights", "__end__", "manual_insights_invalid", True),
        (
            "validate_manual_insights",
            "select_creative_knowledge",
            "manual_insights_valid",
            True,
        ),
        ("select_creative_knowledge", "__end__", "knowledge_selection_failed", True),
        (
            "select_creative_knowledge",
            "generate_creative_ideas",
            "knowledge_selected",
            True,
        ),
        ("generate_creative_ideas", "__end__", "generation_failed", True),
        (
            "generate_creative_ideas",
            "validate_creative_ideas",
            "generation_valid",
            True,
        ),
        ("validate_creative_ideas", "__end__", "creative_ideas_invalid", True),
        (
            "validate_creative_ideas",
            "human_select_idea",
            "creative_ideas_valid",
            True,
        ),
        ("human_select_idea", "apply_human_review", None, False),
        ("apply_human_review", "human_select_idea", "pending", True),
        ("apply_human_review", "generate_script", "approved", True),
        ("apply_human_review", "finalize_result", "terminal", True),
        ("generate_script", "validate_script", None, False),
        ("validate_script", "finalize_result", None, False),
        ("finalize_result", "__end__", None, False),
    }.issubset(edges)
    assert ("validate_input", "__end__", None, False) not in edges


def test_langgraph_json_points_to_real_graph() -> None:
    with open("langgraph.json", encoding="utf-8") as file:
        payload = json.load(file)

    assert payload["graphs"]["agent"] == "./src/tk_script_agent_lab/langgraph_app/graph.py:graph"


def test_routing_functions_return_expected_targets() -> None:
    assert route_after_validate_input({"status": WorkflowStatus.INPUT_INVALID}) == "input_invalid"
    assert route_after_validate_input({"status": WorkflowStatus.READY}) == "input_valid"
    assert (
        route_after_validate_manual_insights({"status": WorkflowStatus.FAILED})
        == "manual_insights_invalid"
    )
    assert (
        route_after_validate_manual_insights({"status": WorkflowStatus.READY})
        == "manual_insights_valid"
    )
    assert (
        route_after_select_creative_knowledge({"status": WorkflowStatus.FAILED})
        == "knowledge_selection_failed"
    )
    assert (
        route_after_select_creative_knowledge({"status": WorkflowStatus.READY})
        == "knowledge_selected"
    )
    assert (
        route_after_generate_creative_ideas({"status": WorkflowStatus.FAILED})
        == "generation_failed"
    )
    assert (
        route_after_generate_creative_ideas({"status": WorkflowStatus.READY})
        == "generation_valid"
    )
    assert (
        route_after_validate_creative_ideas({"status": WorkflowStatus.FAILED})
        == "creative_ideas_invalid"
    )
    assert (
        route_after_validate_creative_ideas({"status": WorkflowStatus.READY})
        == "creative_ideas_valid"
    )
    assert route_after_apply_human_review({"status": WorkflowStatus.READY}) == "approved"
    assert (
        route_after_apply_human_review({"status": WorkflowStatus.AWAITING_IDEA_SELECTION})
        == "pending"
    )
    assert route_after_apply_human_review({"status": WorkflowStatus.FAILED}) == "terminal"

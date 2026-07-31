from langgraph.graph import END, START, StateGraph

from tk_script_agent_lab.configuration import GraphConfiguration
from tk_script_agent_lab.langgraph_app.nodes import (
    apply_human_review,
    finalize_result,
    generate_creative_ideas,
    generate_script,
    human_select_idea,
    select_creative_knowledge,
    validate_creative_ideas,
    validate_input,
    validate_manual_insights,
    validate_script,
)
from tk_script_agent_lab.langgraph_app.routing import (
    route_after_apply_human_review,
    route_after_generate_creative_ideas,
    route_after_select_creative_knowledge,
    route_after_validate_creative_ideas,
    route_after_validate_input,
    route_after_validate_manual_insights,
)
from tk_script_agent_lab.langgraph_app.state import (
    GraphInputState,
    GraphOutputState,
    GraphState,
)


def build_graph(checkpointer=None):
    workflow = StateGraph(
        GraphState,
        context_schema=GraphConfiguration,
        input_schema=GraphInputState,
        output_schema=GraphOutputState,
    )
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("validate_manual_insights", validate_manual_insights)
    workflow.add_node("select_creative_knowledge", select_creative_knowledge)
    workflow.add_node("generate_creative_ideas", generate_creative_ideas)
    workflow.add_node("validate_creative_ideas", validate_creative_ideas)
    workflow.add_node("human_select_idea", human_select_idea)
    workflow.add_node("apply_human_review", apply_human_review)
    workflow.add_node("generate_script", generate_script)
    workflow.add_node("validate_script", validate_script)
    workflow.add_node("finalize_result", finalize_result)

    workflow.add_edge(START, "validate_input")
    workflow.add_conditional_edges(
        "validate_input",
        route_after_validate_input,
        {
            "input_valid": "validate_manual_insights",
            "input_invalid": END,
        },
    )
    workflow.add_conditional_edges(
        "validate_manual_insights",
        route_after_validate_manual_insights,
        {
            "manual_insights_valid": "select_creative_knowledge",
            "manual_insights_invalid": END,
        },
    )
    workflow.add_conditional_edges(
        "select_creative_knowledge",
        route_after_select_creative_knowledge,
        {
            "knowledge_selected": "generate_creative_ideas",
            "knowledge_selection_failed": END,
        },
    )
    workflow.add_conditional_edges(
        "generate_creative_ideas",
        route_after_generate_creative_ideas,
        {
            "generation_valid": "validate_creative_ideas",
            "generation_failed": END,
        },
    )
    workflow.add_conditional_edges(
        "validate_creative_ideas",
        route_after_validate_creative_ideas,
        {
            "creative_ideas_valid": "human_select_idea",
            "creative_ideas_invalid": END,
        },
    )
    workflow.add_edge("human_select_idea", "apply_human_review")
    workflow.add_conditional_edges(
        "apply_human_review",
        route_after_apply_human_review,
        {
            "approved": "generate_script",
            "pending": "human_select_idea",
            "terminal": "finalize_result",
        },
    )
    workflow.add_edge("generate_script", "validate_script")
    workflow.add_edge("validate_script", "finalize_result")
    workflow.add_edge("finalize_result", END)

    return workflow.compile(checkpointer=checkpointer)


graph = build_graph()

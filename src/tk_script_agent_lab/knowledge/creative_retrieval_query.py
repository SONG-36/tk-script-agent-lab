from tk_script_agent_lab.configuration import GraphConfiguration
from tk_script_agent_lab.domain import ReferenceInsight, SellingPoint
from tk_script_agent_lab.knowledge.contracts import RetrievalRequest
from tk_script_agent_lab.workflow import WorkflowInput


def build_creative_retrieval_request(
    workflow_input: WorkflowInput,
    reference_insights: list[ReferenceInsight],
    configuration: GraphConfiguration,
) -> RetrievalRequest:
    profile = workflow_input.product_profile
    query = "\n".join(
        _non_empty_lines(
            [
                f"Product name: {profile.product_name}",
                f"Product category: {profile.category}",
                f"Target market: {profile.target_market}",
                _list_line("Target audience", profile.target_audiences),
                _list_line("Usage scenarios", profile.usage_scenarios),
                _selling_points_line(workflow_input.selling_points),
                _reference_patterns_line(reference_insights),
                "Task: generate distinct, shootable creative ideas.",
            ]
        )
    )
    return RetrievalRequest(
        stage="creative",
        target_market=profile.target_market,
        product_category=profile.category,
        query=query,
        limit=configuration.creative_knowledge_limit,
        filters={"query_version": configuration.creative_retrieval_query_version},
    )


def _non_empty_lines(lines: list[str | None]) -> list[str]:
    return [line for line in lines if line]


def _list_line(label: str, values: list[str]) -> str | None:
    return f"{label}: {'; '.join(values)}" if values else None


def _selling_points_line(selling_points: list[SellingPoint]) -> str | None:
    if not selling_points:
        return None
    values = [
        f"{item.title}: {item.description}"
        for item in sorted(selling_points, key=lambda value: (value.priority, value.selling_point_id))
    ]
    return "Selling points: " + " | ".join(values)


def _reference_patterns_line(reference_insights: list[ReferenceInsight]) -> str | None:
    if not reference_insights:
        return None
    values = []
    for insight in sorted(reference_insights, key=lambda value: value.insight_id):
        evidence = f" Evidence: {insight.evidence_text}" if insight.evidence_text else ""
        values.append(f"{insight.insight_type}: {insight.description}{evidence}")
    return "Reference patterns: " + " | ".join(values)

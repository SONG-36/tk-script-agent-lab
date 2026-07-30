import json
from pathlib import Path

from tk_script_agent_lab.domain import ReviewDecision, ReviewDecisionType, VerificationStatus
from tk_script_agent_lab.golden_case import load_golden_case
from tk_script_agent_lab.providers import FakeContentProvider
from tk_script_agent_lab.workflow import (
    WorkflowStatus,
    export_completed_workflow,
    resume_with_review,
    start_workflow,
)


def golden_case_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "golden_cases" / "car_vacuum_v1"


def approved_review(target_id: str) -> ReviewDecision:
    return ReviewDecision(
        review_id=f"integration_approve_{target_id}",
        target_type="creative_idea",
        target_id=target_id,
        decision=ReviewDecisionType.APPROVED,
        reviewer="integration-reviewer",
        comment=None,
    )


def test_phase_1b_golden_case_end_to_end(tmp_path) -> None:  # type: ignore[no-untyped-def]
    workflow_input, fixtures, _reviews = load_golden_case(golden_case_dir())
    provider = FakeContentProvider(fixtures)

    waiting = start_workflow(workflow_input, provider)
    assert waiting.status == WorkflowStatus.AWAITING_IDEA_SELECTION
    assert waiting.script_draft is None

    selected_id = waiting.creative_ideas[1].creative_idea_id
    completed = resume_with_review(waiting, approved_review(selected_id), provider)
    assert completed.status == WorkflowStatus.COMPLETED
    assert completed.script_draft is not None
    assert completed.script_draft.creative_idea_id == selected_id
    assert all(fact.status != VerificationStatus.REJECTED for fact in workflow_input.product_facts)

    used_fact_ids = {
        usage.source_id
        for idea in completed.creative_ideas
        for usage in idea.source_usages
        if usage.source_type == "product_fact"
    } | {
        usage.source_id
        for usage in completed.script_draft.source_usages
        if usage.source_type == "product_fact"
    }
    unverified_fact_ids = {
        fact.fact_id
        for fact in workflow_input.product_facts
        if fact.status == VerificationStatus.UNVERIFIED
    }
    assert used_fact_ids.isdisjoint(unverified_fact_ids)

    json_path, markdown_path = export_completed_workflow(completed, tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["status"] == WorkflowStatus.COMPLETED
    assert payload["selected_idea_id"] == selected_id
    assert markdown_path.exists()
    assert [record["sequence"] for record in payload["step_records"]] == list(
        range(1, len(payload["step_records"]) + 1)
    )
    assert [record["step_name"] for record in payload["step_records"]] == [
        "validate_input",
        "analyze_references",
        "validate_reference_insights",
        "generate_creative_ideas",
        "validate_creative_ideas",
        "await_human_selection",
        "apply_human_review",
        "generate_script",
        "validate_script",
        "export_result",
    ]

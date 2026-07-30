from pathlib import Path

from tk_script_agent_lab.domain import (
    CreativeIdea,
    ProductFact,
    ReferenceInsight,
    ReviewDecision,
    ReviewDecisionType,
    ScriptDraft,
    SourceUsage,
    VerificationStatus,
)
from tk_script_agent_lab.golden_case import load_golden_case
from tk_script_agent_lab.providers import FakeContentProvider, FakeProviderFixtures
from tk_script_agent_lab.workflow import WorkflowInput, WorkflowState, start_workflow


def golden_case_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "golden_cases" / "car_vacuum_v1"


def load_phase_1b() -> tuple[WorkflowInput, FakeProviderFixtures, list[ReviewDecision]]:
    return load_golden_case(golden_case_dir())


def make_provider(fixtures: FakeProviderFixtures | None = None) -> FakeContentProvider:
    _workflow_input, loaded_fixtures, _reviews = load_phase_1b()
    return FakeContentProvider(fixtures or loaded_fixtures)


def start_golden_workflow() -> tuple[WorkflowState, FakeContentProvider, list[ReviewDecision]]:
    workflow_input, fixtures, reviews = load_phase_1b()
    provider = FakeContentProvider(fixtures)
    return start_workflow(workflow_input, provider), provider, reviews


def approved_review(target_id: str) -> ReviewDecision:
    return ReviewDecision(
        review_id=f"review_approve_{target_id}",
        target_type="creative_idea",
        target_id=target_id,
        decision=ReviewDecisionType.APPROVED,
        reviewer="test-reviewer",
        comment=None,
    )


def rejected_review(target_id: str) -> ReviewDecision:
    return ReviewDecision(
        review_id=f"review_reject_{target_id}",
        target_type="creative_idea",
        target_id=target_id,
        decision=ReviewDecisionType.REJECTED,
        reviewer="test-reviewer",
        comment="Rejected in test.",
    )


def revision_required_review(target_id: str) -> ReviewDecision:
    return ReviewDecision(
        review_id=f"review_revision_{target_id}",
        target_type="creative_idea",
        target_id=target_id,
        decision=ReviewDecisionType.REVISION_REQUIRED,
        reviewer="test-reviewer",
        comment="Needs revision in test.",
    )


def pending_review(target_id: str) -> ReviewDecision:
    return ReviewDecision(
        review_id=f"review_pending_{target_id}",
        target_type="creative_idea",
        target_id=target_id,
        decision=ReviewDecisionType.PENDING,
        reviewer=None,
        comment=None,
    )


def with_bad_reference_insight(fixtures: FakeProviderFixtures) -> FakeProviderFixtures:
    bad = fixtures.model_copy(deep=True)
    bad.reference_insights = [
        ReferenceInsight(
            insight_id="insight_missing_video",
            reference_video_id="missing_video",
            insight_type="HOOK",
            description="Invalid provider fixture.",
            evidence_text=None,
            start_second=None,
            end_second=None,
        )
    ]
    return bad


def with_bad_creative_idea(fixtures: FakeProviderFixtures) -> FakeProviderFixtures:
    bad = fixtures.model_copy(deep=True)
    first = bad.creative_ideas[0]
    bad.creative_ideas = [
        first.model_copy(
            update={
                "source_usages": [
                    SourceUsage(
                        source_usage_id="bad_usage",
                        source_type="product_fact",
                        source_id="missing_fact",
                        usage_purpose="Invalid source.",
                    )
                ]
            },
            deep=True,
        )
    ]
    return bad


def with_unverified_fact_idea(
    workflow_input: WorkflowInput,
    fixtures: FakeProviderFixtures,
) -> FakeProviderFixtures:
    bad = fixtures.model_copy(deep=True)
    idea = bad.creative_ideas[0].model_copy(
        update={
            "source_usages": [
                SourceUsage(
                    source_usage_id="usage_unverified_fact",
                    source_type="product_fact",
                    source_id="fact_power_watts_unknown",
                    usage_purpose="Invalid unverified fact usage.",
                )
            ]
        },
        deep=True,
    )
    assert any(
        fact.fact_id == "fact_power_watts_unknown"
        and fact.status == VerificationStatus.UNVERIFIED
        for fact in workflow_input.product_facts
    )
    bad.creative_ideas = [idea]
    return bad


def fixtures_with_script(fixtures: FakeProviderFixtures, script: ScriptDraft) -> FakeProviderFixtures:
    updated = fixtures.model_copy(deep=True)
    updated.script_drafts = [script]
    return updated


def rejected_fact() -> ProductFact:
    return ProductFact(
        fact_id="fact_rejected_for_phase_1b",
        product_id="prod_car_vacuum_schema_fixture",
        field_name="bad_claim",
        value="rejected claim",
        unit=None,
        status=VerificationStatus.REJECTED,
        source_ids=["fixture"],
        notes=None,
    )


def idea_with_rejected_fact(idea: CreativeIdea) -> CreativeIdea:
    return idea.model_copy(
        update={
            "source_usages": [
                SourceUsage(
                    source_usage_id="usage_rejected_fact",
                    source_type="product_fact",
                    source_id="fact_rejected_for_phase_1b",
                    usage_purpose="Invalid rejected fact usage.",
                )
            ]
        },
        deep=True,
    )

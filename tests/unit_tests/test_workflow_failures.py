from tk_script_agent_lab.domain import ProductFact, VerificationStatus
from tk_script_agent_lab.providers import FakeContentProvider
from tk_script_agent_lab.workflow import WorkflowStatus, start_workflow

from phase_1b_helpers import (
    idea_with_rejected_fact,
    load_phase_1b,
    rejected_fact,
)


def test_provider_creative_idea_using_rejected_fact_is_blocked() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    rejected = rejected_fact()
    bad_input = workflow_input.model_copy(
        update={"product_facts": [*workflow_input.product_facts, rejected]},
        deep=True,
    )
    bad_fixtures = fixtures.model_copy(
        update={"creative_ideas": [idea_with_rejected_fact(fixtures.creative_ideas[0])]},
        deep=True,
    )

    state = start_workflow(bad_input, FakeContentProvider(bad_fixtures))

    assert state.status == WorkflowStatus.FAILED
    assert "NO_CREATIVE_IDEAS" in [error.code for error in state.validation_errors]


def test_input_unverified_fact_kept_unverified_after_workflow() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    before = [
        fact.model_dump(mode="json")
        for fact in workflow_input.product_facts
        if fact.status == VerificationStatus.UNVERIFIED
    ]

    start_workflow(workflow_input, FakeContentProvider(fixtures))

    after = [
        fact.model_dump(mode="json")
        for fact in workflow_input.product_facts
        if fact.status == VerificationStatus.UNVERIFIED
    ]
    assert after == before


def test_invalid_input_product_fact_mismatch_returns_all_errors() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    bad_fact = ProductFact(
        fact_id="fact_other_product",
        product_id="other_product",
        field_name="category",
        value="car vacuum cleaner",
        unit=None,
        status=VerificationStatus.VERIFIED,
        source_ids=["source"],
        notes=None,
    )
    bad_input = workflow_input.model_copy(
        update={"product_facts": [bad_fact]},
        deep=True,
    )

    state = start_workflow(bad_input, FakeContentProvider(fixtures))

    assert state.status == WorkflowStatus.INPUT_INVALID
    assert "WORKFLOW_INPUT_INVALID" in [error.code for error in state.validation_errors]
    assert "PRODUCT_ID_MISMATCH" in [error.code for error in state.validation_errors]

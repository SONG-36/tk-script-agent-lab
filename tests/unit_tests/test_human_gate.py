import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import ReviewDecision, ReviewDecisionType
from tk_script_agent_lab.workflow import WorkflowStatus, resume_with_review

from phase_1b_helpers import (
    approved_review,
    pending_review,
    rejected_review,
    revision_required_review,
    start_golden_workflow,
)


def test_no_review_decision_means_no_script_at_human_gate() -> None:
    state, _provider, _reviews = start_golden_workflow()

    assert state.status == WorkflowStatus.AWAITING_IDEA_SELECTION
    assert state.script_draft is None


def test_approved_existing_idea_generates_script() -> None:
    state, provider, _reviews = start_golden_workflow()
    selected_id = state.creative_ideas[0].creative_idea_id

    completed = resume_with_review(state, approved_review(selected_id), provider)

    assert completed.status == WorkflowStatus.COMPLETED
    assert completed.script_draft is not None


def test_rejected_review_does_not_generate_script() -> None:
    state, provider, _reviews = start_golden_workflow()

    result = resume_with_review(
        state,
        rejected_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )

    assert result.status == WorkflowStatus.IDEA_REJECTED
    assert result.script_draft is None


def test_revision_required_review_does_not_generate_script() -> None:
    state, provider, _reviews = start_golden_workflow()

    result = resume_with_review(
        state,
        revision_required_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )

    assert result.status == WorkflowStatus.REVISION_REQUIRED
    assert result.script_draft is None


def test_pending_review_keeps_waiting_and_does_not_generate_script() -> None:
    state, provider, _reviews = start_golden_workflow()

    result = resume_with_review(
        state,
        pending_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )

    assert result.status == WorkflowStatus.AWAITING_IDEA_SELECTION
    assert result.script_draft is None


def test_review_missing_idea_returns_stable_error_code() -> None:
    state, provider, _reviews = start_golden_workflow()

    result = resume_with_review(state, approved_review("missing_idea"), provider)

    assert result.status == WorkflowStatus.FAILED
    assert "CREATIVE_IDEA_NOT_FOUND" in [error.code for error in result.validation_errors]


def test_review_target_type_script_draft_returns_stable_error_code() -> None:
    state, provider, _reviews = start_golden_workflow()
    review = ReviewDecision(
        review_id="review_wrong_type",
        target_type="script_draft",
        target_id="script_schema_fixture_1",
        decision=ReviewDecisionType.PENDING,
        reviewer=None,
        comment=None,
    )

    result = resume_with_review(state, review, provider)

    assert result.status == WorkflowStatus.FAILED
    assert "REVIEW_TARGET_TYPE_INVALID" in [
        error.code for error in result.validation_errors
    ]


def test_non_awaiting_state_cannot_resume_again() -> None:
    state, provider, _reviews = start_golden_workflow()
    completed = resume_with_review(
        state,
        approved_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )

    result = resume_with_review(
        completed,
        approved_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )

    assert result.status == WorkflowStatus.FAILED
    assert "INVALID_WORKFLOW_STATE" in [error.code for error in result.validation_errors]


def test_approved_review_without_reviewer_is_rejected_by_pydantic() -> None:
    state, _provider, _reviews = start_golden_workflow()

    with pytest.raises(PydanticValidationError):
        ReviewDecision(
            review_id="review_missing_reviewer",
            target_type="creative_idea",
            target_id=state.creative_ideas[0].creative_idea_id,
            decision=ReviewDecisionType.APPROVED,
            reviewer=None,
            comment=None,
        )

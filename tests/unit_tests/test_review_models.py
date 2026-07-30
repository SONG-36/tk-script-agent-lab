import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import ReviewDecision, ReviewDecisionType


def test_review_decision_pending_can_skip_reviewer() -> None:
    review = ReviewDecision(
        review_id="review_1",
        target_type="script_draft",
        target_id="script_1",
        decision=ReviewDecisionType.PENDING,
        reviewer=None,
        comment=None,
    )

    assert review.reviewer is None


def test_approved_review_requires_reviewer() -> None:
    with pytest.raises(PydanticValidationError):
        ReviewDecision(
            review_id="review_1",
            target_type="script_draft",
            target_id="script_1",
            decision=ReviewDecisionType.APPROVED,
            reviewer=None,
            comment=None,
        )


def test_rejected_review_requires_comment() -> None:
    with pytest.raises(PydanticValidationError):
        ReviewDecision(
            review_id="review_1",
            target_type="script_draft",
            target_id="script_1",
            decision=ReviewDecisionType.REJECTED,
            reviewer="Reviewer",
            comment=None,
        )

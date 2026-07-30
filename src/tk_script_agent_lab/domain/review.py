from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tk_script_agent_lab.domain.enums import ReviewDecisionType
from tk_script_agent_lab.domain.product import _require_non_empty

ReviewTargetType = Literal["creative_idea", "script_draft"]


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    target_type: ReviewTargetType
    target_id: str
    decision: ReviewDecisionType
    reviewer: str | None = None
    comment: str | None = None

    @field_validator("review_id", "target_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_decision_requirements(self) -> "ReviewDecision":
        if self.decision == ReviewDecisionType.APPROVED and not (
            self.reviewer and self.reviewer.strip()
        ):
            raise ValueError("APPROVED reviews must include reviewer")
        if self.decision in {
            ReviewDecisionType.REJECTED,
            ReviewDecisionType.REVISION_REQUIRED,
        } and not (self.comment and self.comment.strip()):
            raise ValueError("REJECTED or REVISION_REQUIRED reviews must include comment")
        return self

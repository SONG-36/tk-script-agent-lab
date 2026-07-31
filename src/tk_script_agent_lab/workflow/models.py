from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain import (
    CreativeIdea,
    ProductFact,
    ProductProfile,
    ReferenceInsight,
    ReferenceVideo,
    ReviewDecision,
    ReviewDecisionType,
    ScriptDraft,
    SellingPoint,
    ValidationError,
)
from tk_script_agent_lab.domain.product import _require_non_empty

StepExecutor = Literal["DETERMINISTIC_CODE", "FAKE_PROVIDER", "HUMAN", "IO", "MODEL"]
StepStatus = Literal["SUCCESS", "FAILED", "WAITING", "SKIPPED"]


class WorkflowStatus(StrEnum):
    READY = "READY"
    INPUT_INVALID = "INPUT_INVALID"
    AWAITING_IDEA_SELECTION = "AWAITING_IDEA_SELECTION"
    IDEA_REJECTED = "IDEA_REJECTED"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowStepRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    step_name: str
    executor: StepExecutor
    status: StepStatus
    input_ids: list[str] = Field(default_factory=list)
    output_ids: list[str] = Field(default_factory=list)
    error_codes: list[str] = Field(default_factory=list)

    @field_validator("step_name")
    @classmethod
    def validate_step_name(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("input_ids", "output_ids", "error_codes", mode="after")
    @classmethod
    def validate_lists(cls, values: list[str]) -> list[str]:
        for value in values:
            _require_non_empty(value)
        return values


class WorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    product_profile: ProductProfile
    product_facts: list[ProductFact]
    selling_points: list[SellingPoint]
    reference_videos: list[ReferenceVideo]
    idea_count: int = Field(default=2, ge=1)

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return _require_non_empty(value)


class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: WorkflowStatus
    workflow_input: WorkflowInput
    reference_insights: list[ReferenceInsight] = Field(default_factory=list)
    creative_ideas: list[CreativeIdea] = Field(default_factory=list)
    idea_review: ReviewDecision | None = None
    selected_idea_id: str | None = None
    script_draft: ScriptDraft | None = None
    validation_errors: list[ValidationError] = Field(default_factory=list)
    step_records: list[WorkflowStepRecord] = Field(default_factory=list)

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_state_consistency(self) -> "WorkflowState":
        sequences = [record.sequence for record in self.step_records]
        if sequences and sequences != list(range(1, len(sequences) + 1)):
            raise ValueError("step_records sequence must start at 1 and be continuous")
        if self.status == WorkflowStatus.AWAITING_IDEA_SELECTION:
            if not self.creative_ideas:
                raise ValueError("AWAITING_IDEA_SELECTION requires creative ideas")
            if self.script_draft is not None:
                raise ValueError("AWAITING_IDEA_SELECTION cannot include a script draft")
        if self.status == WorkflowStatus.COMPLETED:
            if self.idea_review is None:
                raise ValueError("COMPLETED requires idea_review")
            if self.idea_review.decision != ReviewDecisionType.APPROVED:
                raise ValueError("COMPLETED requires approved idea_review")
            if not self.selected_idea_id:
                raise ValueError("COMPLETED requires selected_idea_id")
            if self.script_draft is None:
                raise ValueError("COMPLETED requires script_draft")
            if self.validation_errors:
                raise ValueError("COMPLETED requires empty validation_errors")
        return self

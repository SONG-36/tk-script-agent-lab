from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tk_script_agent_lab.domain import (
    CreativeIdea,
    ProductFact,
    ProductProfile,
    ReferenceInsight,
    ReferenceVideo,
    ReviewDecision,
    ScriptDraft,
    SellingPoint,
    ValidationError,
)
from tk_script_agent_lab.domain.product import _require_non_empty
from tk_script_agent_lab.knowledge import KnowledgeSelectionRecord, RetrievedKnowledge
from tk_script_agent_lab.workflow import (
    WorkflowInput,
    WorkflowStatus,
    WorkflowStepRecord,
)
from tk_script_agent_lab.providers import ModelCallRecord


class GraphInputState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    product_profile: ProductProfile
    product_facts: list[ProductFact]
    selling_points: list[SellingPoint]
    reference_videos: list[ReferenceVideo]
    reference_insights: list[ReferenceInsight]
    idea_count: int = Field(default=2, ge=1)

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return _require_non_empty(value)


class ReviewResumePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    decision: str
    reviewer: str | None = None
    comment: str | None = None
    target_type: str = "creative_idea"

    @field_validator("target_id", "decision")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class GraphState(TypedDict, total=False):
    run_id: str
    status: WorkflowStatus
    product_profile: ProductProfile
    product_facts: list[ProductFact]
    selling_points: list[SellingPoint]
    reference_videos: list[ReferenceVideo]
    idea_count: int
    workflow_input: WorkflowInput
    reference_insights: list[ReferenceInsight]
    creative_ideas: list[CreativeIdea]
    creative_knowledge_items: list[RetrievedKnowledge]
    knowledge_selection_records: list[KnowledgeSelectionRecord]
    selected_idea_id: str | None
    idea_review: ReviewDecision | None
    resume_payload: ReviewResumePayload | None
    script_draft: ScriptDraft | None
    validation_errors: list[ValidationError]
    step_records: list[WorkflowStepRecord]
    model_call_records: list[ModelCallRecord]


class GraphOutputState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: WorkflowStatus
    creative_ideas: list[CreativeIdea] = Field(default_factory=list)
    knowledge_selection_records: list[KnowledgeSelectionRecord] = Field(default_factory=list)
    selected_idea_id: str | None = None
    idea_review: ReviewDecision | None = None
    script_draft: ScriptDraft | None = None
    validation_errors: list[ValidationError] = Field(default_factory=list)
    step_records: list[WorkflowStepRecord] = Field(default_factory=list)
    model_call_records: list[ModelCallRecord] = Field(default_factory=list)

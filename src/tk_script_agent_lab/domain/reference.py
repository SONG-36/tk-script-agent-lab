from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tk_script_agent_lab.domain.enums import InsightType, ReferencePlatform
from tk_script_agent_lab.domain.product import _require_non_empty


class ReferenceVideo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_video_id: str
    platform: ReferencePlatform
    url: str | None = None
    title: str | None = None
    transcript: str | None = None
    creator_name: str | None = None
    published_at: str | None = None
    notes: str | None = None

    @field_validator("reference_video_id")
    @classmethod
    def validate_reference_video_id(cls, value: str) -> str:
        return _require_non_empty(value)


class ReferenceInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insight_id: str
    reference_video_id: str
    insight_type: InsightType
    description: str
    evidence_text: str | None = None
    start_second: float | None = None
    end_second: float | None = None

    @field_validator("insight_id", "reference_video_id", "description")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_time_range(self) -> "ReferenceInsight":
        if self.start_second is not None and self.start_second < 0:
            raise ValueError("start_second must be greater than or equal to 0")
        if self.end_second is not None and self.end_second < 0:
            raise ValueError("end_second must be greater than or equal to 0")
        if (
            self.start_second is not None
            and self.end_second is not None
            and self.start_second > self.end_second
        ):
            raise ValueError("start_second must be less than or equal to end_second")
        return self

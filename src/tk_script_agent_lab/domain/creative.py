from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain.product import _require_non_empty, _require_non_empty_items

SourceType = Literal["product_fact", "selling_point", "reference_insight"]


class SourceUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_usage_id: str
    source_type: SourceType
    source_id: str
    usage_purpose: str

    @field_validator("source_usage_id", "source_id", "usage_purpose")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class CreativeIdea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_idea_id: str
    product_id: str
    title: str
    hook: str
    concept_summary: str
    target_audience: str
    source_usages: list[SourceUsage] = Field(min_length=1)
    risk_notes: list[str] = Field(default_factory=list)

    @field_validator(
        "creative_idea_id",
        "product_id",
        "title",
        "hook",
        "concept_summary",
        "target_audience",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("risk_notes", mode="after")
    @classmethod
    def validate_risk_notes(cls, values: list[str]) -> list[str]:
        return _require_non_empty_items(values)

    @model_validator(mode="after")
    def validate_unique_source_usages(self) -> "CreativeIdea":
        keys = [(usage.source_type, usage.source_id) for usage in self.source_usages]
        if len(keys) != len(set(keys)):
            raise ValueError("source_usages must not repeat source_type/source_id")
        return self

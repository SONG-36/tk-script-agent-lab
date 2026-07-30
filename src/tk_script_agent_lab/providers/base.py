from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from tk_script_agent_lab.domain import (
    CreativeIdea,
    ProductFact,
    ProductProfile,
    ReferenceInsight,
    ReferenceVideo,
    ScriptDraft,
    SellingPoint,
    ValidationError,
)


class ReferenceAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_profile: ProductProfile
    product_facts: list[ProductFact]
    reference_videos: list[ReferenceVideo]


class CreativeGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_profile: ProductProfile
    product_facts: list[ProductFact]
    selling_points: list[SellingPoint]
    reference_insights: list[ReferenceInsight]
    idea_count: int = Field(ge=1)


class ScriptGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_profile: ProductProfile
    product_facts: list[ProductFact]
    selling_points: list[SellingPoint]
    reference_insights: list[ReferenceInsight]
    selected_idea: CreativeIdea


class ProviderOutputError(Exception):
    def __init__(self, error: ValidationError) -> None:
        super().__init__(error.message)
        self.error = error


class ContentProvider(Protocol):
    def analyze_references(
        self,
        request: ReferenceAnalysisRequest,
    ) -> list[ReferenceInsight]:
        ...

    def generate_creative_ideas(
        self,
        request: CreativeGenerationRequest,
    ) -> list[CreativeIdea]:
        ...

    def generate_script(
        self,
        request: ScriptGenerationRequest,
    ) -> ScriptDraft:
        ...

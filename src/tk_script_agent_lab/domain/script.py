from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain.creative import SourceUsage
from tk_script_agent_lab.domain.product import _require_non_empty


class ScriptScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_id: str
    sequence: int = Field(ge=1)
    visual: str
    action: str
    voiceover: str | None = None
    on_screen_text: str | None = None
    duration_seconds: float = Field(gt=0)

    @field_validator("scene_id", "visual", "action")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class ScriptDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_id: str
    product_id: str
    creative_idea_id: str
    title: str
    scenes: list[ScriptScene] = Field(min_length=1)
    caption: str | None = None
    cta: str | None = None
    source_usages: list[SourceUsage] = Field(default_factory=list)

    @field_validator("script_id", "product_id", "creative_idea_id", "title")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_scene_sequence(self) -> "ScriptDraft":
        sequences = [scene.sequence for scene in self.scenes]
        if len(sequences) != len(set(sequences)):
            raise ValueError("scene sequences must be unique")
        expected = list(range(1, len(sequences) + 1))
        if sorted(sequences) != expected:
            raise ValueError("scene sequences must start at 1 and be continuous")
        return self

    @model_validator(mode="after")
    def validate_unique_source_usages(self) -> "ScriptDraft":
        keys = [(usage.source_type, usage.source_id) for usage in self.source_usages]
        if len(keys) != len(set(keys)):
            raise ValueError("source_usages must not repeat source_type/source_id")
        return self

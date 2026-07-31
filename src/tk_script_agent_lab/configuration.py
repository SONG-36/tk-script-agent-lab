from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class GraphConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_provider: Literal["fake", "openai"] = "fake"
    creative_model: str | None = None
    creative_prompt_version: str = "creative_idea_v1"
    script_provider: Literal["fake", "openai"] = "fake"
    script_model: str | None = None
    script_prompt_version: str = "script_draft_v1"

    @field_validator("creative_model", "script_model")
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("model name must not be blank")
        return value

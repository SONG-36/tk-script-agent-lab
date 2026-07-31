from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class GraphConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_provider: Literal["fake", "openai"] = "fake"
    creative_model: str | None = None
    creative_prompt_version: str = "creative_idea_v1"

    @field_validator("creative_model")
    @classmethod
    def validate_creative_model(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("creative_model must not be blank")
        return value

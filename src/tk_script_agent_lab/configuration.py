from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GraphConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_provider: Literal["fake", "openai"] = "fake"
    creative_model: str | None = None
    creative_prompt_version: str = "creative_idea_v1"
    script_provider: Literal["fake", "openai"] = "fake"
    script_model: str | None = None
    script_prompt_version: str = "script_draft_v1"
    knowledge_mode: Literal["off", "static", "vector"] = "off"
    creative_knowledge_pack: str | None = None
    creative_knowledge_limit: int = Field(default=6, ge=1)
    knowledge_selector_version: str = "static_selector_v1"
    creative_embedding_model: str | None = None
    creative_retrieval_query_version: str = "creative_retrieval_query_v1"
    creative_vector_retriever_version: str = "vector_retriever_v1"

    @field_validator(
        "creative_model",
        "script_model",
        "creative_knowledge_pack",
        "knowledge_selector_version",
        "creative_embedding_model",
        "creative_retrieval_query_version",
        "creative_vector_retriever_version",
    )
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("configuration text value must not be blank")
        return value

    @model_validator(mode="after")
    def validate_knowledge_mode_requirements(self) -> "GraphConfiguration":
        if self.knowledge_mode == "static" and self.creative_knowledge_pack is None:
            raise ValueError("creative_knowledge_pack is required when knowledge_mode is static")
        if self.knowledge_mode == "vector":
            if self.creative_knowledge_pack is None:
                raise ValueError("creative_knowledge_pack is required when knowledge_mode is vector")
            if self.creative_embedding_model is None:
                raise ValueError("creative_embedding_model is required when knowledge_mode is vector")
        return self

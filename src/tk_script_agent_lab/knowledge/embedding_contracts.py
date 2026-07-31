from hashlib import sha256
import json
from math import isfinite
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.domain.product import _require_non_empty


class EmbeddingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    text: str

    @field_validator("item_id", "text")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[EmbeddingItem] = Field(min_length=1)
    model: str
    provider_version: str

    @field_validator("model", "provider_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_unique_items(self) -> "EmbeddingRequest":
        item_ids = [item.item_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("item_id values must be unique")
        return self


class EmbeddingVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    values: list[float] = Field(min_length=1)
    dimensions: int = Field(gt=0)

    @field_validator("item_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_vector(self) -> "EmbeddingVector":
        if self.dimensions != len(self.values):
            raise ValueError("dimensions must equal len(values)")
        if any(not isfinite(value) for value in self.values):
            raise ValueError("embedding values must be finite")
        return self


class EmbeddingTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    provider: Literal["openai"]
    provider_version: str
    model: str
    input_ids: list[str]
    output_ids: list[str]
    dimensions: int | None
    status: Literal["SUCCESS", "FAILED"]
    error_code: str | None = None

    @field_validator("request_id", "provider_version", "model")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class EmbeddingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vectors: list[EmbeddingVector] = Field(default_factory=list)
    trace: EmbeddingTrace
    errors: list[ValidationError] = Field(default_factory=list)


class EmbeddingProvider(Protocol):
    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        ...


def stable_embedding_request_id(request: EmbeddingRequest) -> str:
    payload = {
        "items": [
            {
                "item_id": item.item_id,
                "text_sha256": sha256(item.text.encode("utf-8")).hexdigest(),
            }
            for item in request.items
        ],
        "model": request.model,
        "provider_version": request.provider_version,
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"er_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"

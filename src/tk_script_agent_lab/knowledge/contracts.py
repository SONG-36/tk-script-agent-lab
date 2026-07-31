from hashlib import sha256
import json
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.domain.product import _require_non_empty


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Literal["creative", "script"]
    target_market: str
    product_category: str
    query: str
    limit: int = Field(gt=0)
    filters: dict[str, str] = Field(default_factory=dict)

    @field_validator("target_market", "product_category", "query")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("filters", mode="after")
    @classmethod
    def validate_filters(cls, value: dict[str, str]) -> dict[str, str]:
        for key, item in value.items():
            _require_non_empty(key)
            _require_non_empty(item)
        return value

    @model_validator(mode="after")
    def reject_secret_like_filters(self) -> "RetrievalRequest":
        normalized = json.dumps(self.filters, sort_keys=True).casefold()
        if "api_key" in normalized or "apikey" in normalized:
            raise ValueError("RetrievalRequest must not contain API keys")
        return self


class RetrievedKnowledge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_id: str
    title: str
    content: str
    kind: str
    provenance_type: str
    evidence_status: str
    source_reference: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    score: float | None = None

    @field_validator(
        "knowledge_id",
        "title",
        "content",
        "kind",
        "provenance_type",
        "evidence_status",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        for key, item in value.items():
            _require_non_empty(key)
            _require_non_empty(item)
        return value


class RetrievalExclusion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_id: str
    reason: str

    @field_validator("knowledge_id", "reason")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class RetrievalTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retriever_type: Literal["static", "vector"]
    retriever_version: str
    request_id: str
    candidate_ids: list[str]
    selected_ids: list[str]
    excluded: list[RetrievalExclusion]
    filters_applied: dict[str, str] = Field(default_factory=dict)

    @field_validator("retriever_version", "request_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RetrievedKnowledge] = Field(default_factory=list)
    trace: RetrievalTrace
    errors: list[ValidationError] = Field(default_factory=list)


class KnowledgeRetriever(Protocol):
    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RetrievalResult:
        ...


def stable_retrieval_request_id(request: RetrievalRequest) -> str:
    payload = request.model_dump(mode="json")
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"rr_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"

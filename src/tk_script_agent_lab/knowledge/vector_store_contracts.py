from hashlib import sha256
import json
import re
from math import isfinite
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.domain.product import _require_non_empty
from tk_script_agent_lab.knowledge.contracts import RetrievalRequest
from tk_script_agent_lab.knowledge.embedding_contracts import EmbeddingVector
from tk_script_agent_lab.knowledge.ingestion_contracts import KnowledgeChunk


class VectorIndexItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk: KnowledgeChunk
    vector: EmbeddingVector

    @model_validator(mode="after")
    def validate_ids(self) -> "VectorIndexItem":
        if self.chunk.chunk_id != self.vector.item_id:
            raise ValueError("chunk.chunk_id must equal vector.item_id")
        return self


class VectorBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[VectorIndexItem] = Field(min_length=1)
    collection_name: str
    index_version: str

    @field_validator("collection_name", "index_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_items(self) -> "VectorBuildRequest":
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.collection_name):
            raise ValueError("collection_name contains unsafe characters")
        chunk_ids = [item.chunk.chunk_id for item in self.items]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk_id values must be unique")
        dimensions = {item.vector.dimensions for item in self.items}
        if len(dimensions) != 1:
            raise ValueError("all vector dimensions must match")
        return self


class VectorBuildTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    build_id: str
    store_type: Literal["qdrant_local"]
    store_version: str
    collection_name: str
    input_ids: list[str]
    indexed_ids: list[str]
    rejected_ids: list[str]
    dimensions: int | None
    status: Literal["SUCCESS", "FAILED"]


class VectorBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace: VectorBuildTrace
    errors: list[ValidationError] = Field(default_factory=list)


class VectorSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_vector: EmbeddingVector
    retrieval_request: RetrievalRequest
    collection_name: str


class VectorSearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    score: float

    @model_validator(mode="after")
    def validate_hit(self) -> "VectorSearchHit":
        _require_non_empty(self.chunk_id)
        if not isfinite(self.score):
            raise ValueError("score must be finite")
        return self


class VectorSearchTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search_id: str
    collection_name: str
    candidate_ids: list[str]
    selected_ids: list[str]
    filters_applied: dict[str, str]
    status: Literal["SUCCESS", "FAILED"]


class VectorSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hits: list[VectorSearchHit] = Field(default_factory=list)
    trace: VectorSearchTrace
    errors: list[ValidationError] = Field(default_factory=list)


class VectorStore(Protocol):
    def build(self, request: VectorBuildRequest) -> VectorBuildResult:
        ...

    def search(self, request: VectorSearchRequest) -> VectorSearchResult:
        ...

    def get_chunk(self, chunk_id: str) -> KnowledgeChunk | None:
        ...


def stable_vector_build_id(request: VectorBuildRequest) -> str:
    payload = [
        {
            "chunk_id": item.chunk.chunk_id,
            "document_id": item.chunk.document_id,
            "document_version": item.chunk.document_version,
            "dimensions": item.vector.dimensions,
        }
        for item in sorted(request.items, key=lambda value: value.chunk.chunk_id)
    ]
    normalized = json.dumps(
        {"collection": request.collection_name, "index_version": request.index_version, "items": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"vb_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"

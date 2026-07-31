from hashlib import sha256
import json
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.domain.product import _require_non_empty
from tk_script_agent_lab.knowledge.ingestion_contracts import KnowledgeChunk


class IndexBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunks: list[KnowledgeChunk] = Field(min_length=1)
    index_version: str = "in_memory_index_v1"

    @field_validator("index_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class IndexBuildTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    build_id: str
    index_type: Literal["in_memory"]
    index_version: str
    input_chunk_ids: list[str]
    indexed_chunk_ids: list[str]
    rejected_chunk_ids: list[str]
    duplicate_chunk_ids: list[str]
    chunk_count: int = Field(ge=0)

    @field_validator("build_id", "index_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class IndexBuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace: IndexBuildTrace
    errors: list[ValidationError] = Field(default_factory=list)


@runtime_checkable
class KnowledgeIndex(Protocol):
    def build(self, request: IndexBuildRequest) -> IndexBuildResult:
        ...

    def get(self, chunk_id: str) -> KnowledgeChunk | None:
        ...

    def snapshot(self) -> tuple[KnowledgeChunk, ...]:
        ...


def stable_index_build_id(
    *,
    index_version: str,
    chunks: list[KnowledgeChunk],
) -> str:
    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "sequence": chunk.sequence,
            "content_sha256": sha256(chunk.content.encode("utf-8")).hexdigest(),
            "document_version": chunk.document_version,
        }
        for chunk in sorted(chunks, key=lambda item: (item.chunk_id, item.document_id, item.sequence))
    ]
    normalized = json.dumps(
        {"index_version": index_version, "chunks": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"ib_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"

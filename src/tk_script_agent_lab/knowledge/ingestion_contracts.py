from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import PurePosixPath
from typing import Literal, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.domain.product import _require_non_empty, _require_non_empty_items

DocumentSourceType = Literal["internal_file", "manual_entry", "official_url", "experiment_observation"]
KnowledgeProvenanceType = Literal["internal_working_rule", "experiment_observation", "official_policy"]
KnowledgeEvidenceStatus = Literal["hypothesis", "observed", "verified"]
KnowledgeTaskStage = Literal["creative", "script"]


def _reject_secret_like_text(value: str, *, field: str) -> None:
    normalized = value.casefold()
    forbidden = ("api_key", "apikey", "authorization", "bearer ")
    if any(token in normalized for token in forbidden):
        raise ValueError(f"{field} must not contain credentials")


def _validate_metadata(value: dict[str, str]) -> dict[str, str]:
    for key, item in value.items():
        _require_non_empty(key)
        _require_non_empty(item)
        _reject_secret_like_text(key, field="metadata")
        _reject_secret_like_text(item, field="metadata")
    return value


class DocumentSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_type: DocumentSourceType
    source_reference: str
    publisher: str | None = None
    retrieved_at: datetime | None = None

    @field_validator("source_id", "source_reference")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = _require_non_empty(value)
        _reject_secret_like_text(value, field="source_reference")
        return value

    @model_validator(mode="after")
    def validate_source_reference(self) -> "DocumentSource":
        if self.source_type == "official_url":
            parsed = urlparse(self.source_reference)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("official_url source_reference must be http or https")
        if self.source_type == "internal_file":
            normalized = self.source_reference.replace("\\", "/")
            path = PurePosixPath(normalized)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("internal_file source_reference must be relative and local")
        return self


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    title: str
    content: str
    source: DocumentSource
    version: str
    language: str
    provenance_type: KnowledgeProvenanceType
    evidence_status: KnowledgeEvidenceStatus
    target_markets: list[str] = Field(min_length=1)
    product_categories: list[str] = Field(min_length=1)
    task_stages: list[KnowledgeTaskStage] = Field(min_length=1)
    effective_from: date | None = None
    effective_to: date | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("document_id", "title", "content", "version", "language")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = _require_non_empty(value)
        _reject_secret_like_text(value, field="document")
        return value

    @field_validator("target_markets", "product_categories", mode="after")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return _require_non_empty_items(values)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_metadata(value)

    @model_validator(mode="after")
    def validate_document_boundaries(self) -> "KnowledgeDocument":
        if self.provenance_type == "official_policy":
            if self.source.source_type != "official_url":
                raise ValueError("official_policy requires official_url source")
            if not self.source.publisher:
                raise ValueError("official_policy requires publisher")
        if (
            self.provenance_type == "internal_working_rule"
            and self.evidence_status == "verified"
        ):
            raise ValueError("internal_working_rule cannot be verified")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError("effective_to must not be earlier than effective_from")
        return self


class KnowledgeChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    sequence: int = Field(ge=1)
    content: str
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    char_count: int = Field(ge=1)
    title: str
    source: DocumentSource
    document_version: str
    language: str
    provenance_type: KnowledgeProvenanceType
    evidence_status: KnowledgeEvidenceStatus
    target_markets: list[str] = Field(min_length=1)
    product_categories: list[str] = Field(min_length=1)
    task_stages: list[KnowledgeTaskStage] = Field(min_length=1)
    effective_from: date | None = None
    effective_to: date | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    token_count: int | None = None

    @field_validator("chunk_id", "document_id", "content", "title", "document_version", "language")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("target_markets", "product_categories", mode="after")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return _require_non_empty_items(values)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_metadata(value)

    @model_validator(mode="after")
    def validate_chunk_offsets(self) -> "KnowledgeChunk":
        if self.char_end <= self.char_start:
            raise ValueError("char_end must be greater than char_start")
        if self.char_count != len(self.content):
            raise ValueError("char_count must equal len(content)")
        if self.char_count != self.char_end - self.char_start:
            raise ValueError("char_count must equal char_end - char_start")
        if self.token_count is not None:
            raise ValueError("token_count is not available in Phase 4A")
        return self


class ChunkingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: KnowledgeDocument
    max_chars: int = Field(gt=0)
    overlap_chars: int = Field(ge=0)
    chunker_version: str

    @field_validator("chunker_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingRequest":
        if self.overlap_chars >= self.max_chars:
            raise ValueError("overlap_chars must be less than max_chars")
        return self


class ChunkingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    errors: list[ValidationError] = Field(default_factory=list)


class IngestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[KnowledgeDocument] = Field(min_length=1)
    max_chars: int = Field(gt=0)
    overlap_chars: int = Field(ge=0)
    chunker_version: str
    ingestor_version: str

    @field_validator("chunker_version", "ingestor_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_overlap(self) -> "IngestionRequest":
        if self.overlap_chars >= self.max_chars:
            raise ValueError("overlap_chars must be less than max_chars")
        return self


class IngestionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    ingestor_version: str
    chunker_version: str
    input_document_ids: list[str]
    accepted_document_ids: list[str]
    rejected_document_ids: list[str]
    output_chunk_ids: list[str]
    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)

    @field_validator("request_id", "ingestor_version", "chunker_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class IngestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    trace: IngestionTrace
    errors: list[ValidationError] = Field(default_factory=list)


class ChunkingStrategy(Protocol):
    def chunk(self, request: ChunkingRequest) -> ChunkingResult:
        ...


class KnowledgeIngestor(Protocol):
    def ingest(self, request: IngestionRequest) -> IngestionResult:
        ...


def stable_chunk_id(
    *,
    document_id: str,
    document_version: str,
    chunker_version: str,
    sequence: int,
    content: str,
) -> str:
    payload = {
        "document_id": document_id,
        "document_version": document_version,
        "chunker_version": chunker_version,
        "sequence": sequence,
        "content": content,
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"kc_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"


def stable_ingestion_request_id(request: IngestionRequest) -> str:
    payload = {
        "documents": [
            {
                "document_id": document.document_id,
                "version": document.version,
                "content_sha256": sha256(document.content.encode("utf-8")).hexdigest(),
            }
            for document in request.documents
        ],
        "max_chars": request.max_chars,
        "overlap_chars": request.overlap_chars,
        "chunker_version": request.chunker_version,
        "ingestor_version": request.ingestor_version,
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"ir_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.chunking import DeterministicParagraphChunker
from tk_script_agent_lab.knowledge.ingestion_contracts import (
    ChunkingRequest,
    ChunkingStrategy,
    IngestionRequest,
    IngestionResult,
    IngestionTrace,
    KnowledgeChunk,
    stable_ingestion_request_id,
)

DEFAULT_INGESTOR_VERSION = "deterministic_ingestor_v1"


class DeterministicKnowledgeIngestor:
    def __init__(self, chunker: ChunkingStrategy | None = None) -> None:
        self._chunker = chunker or DeterministicParagraphChunker()

    def ingest(self, request: IngestionRequest) -> IngestionResult:
        accepted_document_ids: list[str] = []
        rejected_document_ids: list[str] = []
        chunks: list[KnowledgeChunk] = []
        errors: list[ValidationError] = []
        seen_document_ids: set[str] = set()
        seen_chunk_ids: set[str] = set()

        for document in request.documents:
            if document.document_id in seen_document_ids:
                rejected_document_ids.append(document.document_id)
                errors.append(
                    ValidationError(
                        code="INGESTION_DUPLICATE_DOCUMENT_ID",
                        message="IngestionRequest contains a duplicate document_id.",
                        object_type="KnowledgeDocument",
                        object_id=document.document_id,
                        field="document_id",
                        related_id=document.document_id,
                    )
                )
                continue
            seen_document_ids.add(document.document_id)

            result = self._chunker.chunk(
                ChunkingRequest(
                    document=document,
                    max_chars=request.max_chars,
                    overlap_chars=request.overlap_chars,
                    chunker_version=request.chunker_version,
                )
            )
            if result.errors:
                rejected_document_ids.append(document.document_id)
                errors.extend(
                    _wrap_chunking_error(document.document_id, error)
                    for error in result.errors
                )
                continue

            duplicate_chunk_id = _first_duplicate_chunk_id(result.chunks, seen_chunk_ids)
            if duplicate_chunk_id is not None:
                rejected_document_ids.append(document.document_id)
                errors.append(
                    ValidationError(
                        code="INGESTION_DUPLICATE_CHUNK_ID",
                        message="Chunking produced a duplicate chunk_id.",
                        object_type="KnowledgeChunk",
                        object_id=duplicate_chunk_id,
                        field="chunk_id",
                        related_id=document.document_id,
                    )
                )
                continue

            accepted_document_ids.append(document.document_id)
            chunks.extend(result.chunks)
            seen_chunk_ids.update(chunk.chunk_id for chunk in result.chunks)

        trace = IngestionTrace(
            request_id=stable_ingestion_request_id(request),
            ingestor_version=request.ingestor_version,
            chunker_version=request.chunker_version,
            input_document_ids=[document.document_id for document in request.documents],
            accepted_document_ids=accepted_document_ids,
            rejected_document_ids=rejected_document_ids,
            output_chunk_ids=[chunk.chunk_id for chunk in chunks],
            document_count=len(request.documents),
            chunk_count=len(chunks),
        )
        return IngestionResult(chunks=chunks, trace=trace, errors=errors)


def _wrap_chunking_error(document_id: str, error: ValidationError) -> ValidationError:
    if error.code == "INGESTION_EMPTY_CONTENT":
        return error
    return ValidationError(
        code="INGESTION_CHUNKING_FAILED",
        message=error.message,
        object_type=error.object_type,
        object_id=error.object_id,
        field=error.field,
        related_id=document_id,
    )


def _first_duplicate_chunk_id(
    chunks: list[KnowledgeChunk],
    existing_chunk_ids: set[str],
) -> str | None:
    local_seen: set[str] = set()
    for chunk in chunks:
        if chunk.chunk_id in existing_chunk_ids or chunk.chunk_id in local_seen:
            return chunk.chunk_id
        local_seen.add(chunk.chunk_id)
    return None

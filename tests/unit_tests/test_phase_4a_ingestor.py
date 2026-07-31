import json

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.chunking import DeterministicParagraphChunker
from tk_script_agent_lab.knowledge.ingestion_contracts import (
    ChunkingResult,
    IngestionRequest,
)
from tk_script_agent_lab.knowledge.ingestor import DeterministicKnowledgeIngestor

from tests.unit_tests.test_phase_4a_ingestion_contracts import document


def ingestion_request(documents=None) -> IngestionRequest:
    return IngestionRequest(
        documents=documents or [document()],
        max_chars=80,
        overlap_chars=10,
        chunker_version="deterministic_paragraph_v1",
        ingestor_version="deterministic_ingestor_v1",
    )


def test_ingestor_chunks_documents_and_builds_stable_trace() -> None:
    request = ingestion_request()
    first = DeterministicKnowledgeIngestor().ingest(request)
    second = DeterministicKnowledgeIngestor().ingest(request)

    assert first.errors == []
    assert first.trace.request_id == second.trace.request_id
    assert first.trace.accepted_document_ids == ["doc_internal_notes_v1"]
    assert first.trace.rejected_document_ids == []
    assert first.trace.chunk_count == len(first.chunks)
    assert json.loads(json.dumps(first.model_dump(mode="json")))["trace"]["chunk_count"] > 0


def test_duplicate_document_id_is_reported_without_silent_skip() -> None:
    duplicate = document(title="Duplicate title")
    result = DeterministicKnowledgeIngestor().ingest(
        ingestion_request(documents=[document(), duplicate])
    )

    assert [error.code for error in result.errors] == ["INGESTION_DUPLICATE_DOCUMENT_ID"]
    assert result.trace.accepted_document_ids == ["doc_internal_notes_v1"]
    assert result.trace.rejected_document_ids == ["doc_internal_notes_v1"]


def test_chunking_failure_rejects_document_and_does_not_call_it_success() -> None:
    class FailingChunker:
        def chunk(self, request):
            return ChunkingResult(
                chunks=[],
                errors=[
                    ValidationError(
                        code="INGESTION_SOURCE_INVALID",
                        message="source invalid",
                        object_type="KnowledgeDocument",
                        object_id=request.document.document_id,
                        field="source",
                        related_id=None,
                    )
                ],
            )

    result = DeterministicKnowledgeIngestor(chunker=FailingChunker()).ingest(
        ingestion_request()
    )

    assert [error.code for error in result.errors] == ["INGESTION_CHUNKING_FAILED"]
    assert result.trace.accepted_document_ids == []
    assert result.trace.rejected_document_ids == ["doc_internal_notes_v1"]
    assert result.chunks == []


def test_duplicate_chunk_id_rejects_current_document() -> None:
    class DuplicateChunker:
        def chunk(self, request):
            result = DeterministicParagraphChunker().chunk(request)
            return ChunkingResult(chunks=[result.chunks[0], result.chunks[0]], errors=[])

    result = DeterministicKnowledgeIngestor(chunker=DuplicateChunker()).ingest(
        ingestion_request()
    )

    assert [error.code for error in result.errors] == ["INGESTION_DUPLICATE_CHUNK_ID"]
    assert result.trace.accepted_document_ids == []
    assert result.trace.rejected_document_ids == ["doc_internal_notes_v1"]

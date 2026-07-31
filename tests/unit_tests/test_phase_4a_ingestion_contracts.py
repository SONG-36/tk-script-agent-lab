import json
from datetime import date

import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.knowledge.ingestion_contracts import (
    ChunkingRequest,
    DocumentSource,
    IngestionRequest,
    IngestionTrace,
    KnowledgeChunk,
    KnowledgeDocument,
)


def source(**overrides) -> DocumentSource:
    payload = {
        "source_id": "src_internal_notes_v1",
        "source_type": "internal_file",
        "source_reference": "source_document.md",
        "publisher": None,
        "retrieved_at": None,
    }
    payload.update(overrides)
    return DocumentSource.model_validate(payload)


def document(**overrides) -> KnowledgeDocument:
    payload = {
        "document_id": "doc_internal_notes_v1",
        "title": "Internal creative notes",
        "content": "First paragraph.\n\nSecond paragraph.",
        "source": source(),
        "version": "v1",
        "language": "en",
        "provenance_type": "internal_working_rule",
        "evidence_status": "hypothesis",
        "target_markets": ["US"],
        "product_categories": ["car vacuum cleaner"],
        "task_stages": ["creative"],
        "effective_from": None,
        "effective_to": None,
        "metadata": {"purpose": "contract test"},
    }
    payload.update(overrides)
    return KnowledgeDocument.model_validate(payload)


def test_document_source_validates_url_and_internal_path_boundaries() -> None:
    assert source().source_reference == "source_document.md"
    assert source(
        source_type="official_url",
        source_reference="https://example.com/policy",
        publisher="Example Publisher",
    )

    with pytest.raises(PydanticValidationError):
        source(source_type="official_url", source_reference="ftp://example.com/policy")
    with pytest.raises(PydanticValidationError):
        source(source_reference="/absolute/source_document.md")
    with pytest.raises(PydanticValidationError):
        source(source_reference="../source_document.md")


def test_knowledge_document_validates_provenance_and_dates() -> None:
    with pytest.raises(PydanticValidationError):
        document(evidence_status="verified")
    with pytest.raises(PydanticValidationError):
        document(
            provenance_type="official_policy",
            evidence_status="verified",
            source=source(source_type="manual_entry", source_reference="manual note"),
        )
    with pytest.raises(PydanticValidationError):
        document(effective_from=date(2026, 1, 2), effective_to=date(2026, 1, 1))


def test_ingestion_models_reject_extra_fields_and_secret_like_metadata() -> None:
    with pytest.raises(PydanticValidationError):
        KnowledgeDocument.model_validate({**document().model_dump(), "api_key": "x"})
    with pytest.raises(PydanticValidationError):
        document(metadata={"OPENAI_API_KEY": "secret"})
    with pytest.raises(PydanticValidationError):
        IngestionRequest.model_validate(
            {
                "documents": [document().model_dump()],
                "max_chars": 100,
                "overlap_chars": 100,
                "chunker_version": "deterministic_paragraph_v1",
                "ingestor_version": "deterministic_ingestor_v1",
            }
        )


def test_chunk_contract_preserves_document_provenance_without_vectors() -> None:
    doc = document()
    chunk = KnowledgeChunk(
        chunk_id="kc_test",
        document_id=doc.document_id,
        sequence=1,
        content="First paragraph.",
        char_start=0,
        char_end=16,
        char_count=16,
        title=doc.title,
        source=doc.source,
        document_version=doc.version,
        language=doc.language,
        provenance_type=doc.provenance_type,
        evidence_status=doc.evidence_status,
        target_markets=doc.target_markets,
        product_categories=doc.product_categories,
        task_stages=doc.task_stages,
        effective_from=doc.effective_from,
        effective_to=doc.effective_to,
        metadata=doc.metadata,
    )
    payload = chunk.model_dump(mode="json")

    assert payload["provenance_type"] == "internal_working_rule"
    assert payload["evidence_status"] == "hypothesis"
    assert "embedding" not in json.dumps(payload).casefold()
    assert "source_usages" not in payload


def test_chunking_and_ingestion_traces_are_json_serializable() -> None:
    doc = document()
    request = ChunkingRequest(
        document=doc,
        max_chars=100,
        overlap_chars=10,
        chunker_version="deterministic_paragraph_v1",
    )
    trace = IngestionTrace(
        request_id="ir_test",
        ingestor_version="deterministic_ingestor_v1",
        chunker_version=request.chunker_version,
        input_document_ids=[doc.document_id],
        accepted_document_ids=[doc.document_id],
        rejected_document_ids=[],
        output_chunk_ids=["kc_test"],
        document_count=1,
        chunk_count=1,
    )

    assert json.loads(json.dumps(trace.model_dump(mode="json")))["request_id"] == "ir_test"

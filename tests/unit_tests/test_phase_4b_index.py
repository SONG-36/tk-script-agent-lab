import json

import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.knowledge.index_contracts import (
    IndexBuildRequest,
    IndexBuildResult,
    KnowledgeIndex,
)
from tk_script_agent_lab.knowledge.in_memory_index import InMemoryKnowledgeIndex

from tests.unit_tests.phase_4b_helpers import chunk


def test_index_build_request_contract_and_protocol() -> None:
    request = IndexBuildRequest(chunks=[chunk()], index_version="in_memory_index_v1")

    class StubIndex:
        def build(self, request: IndexBuildRequest):
            raise NotImplementedError

        def get(self, chunk_id: str):
            return None

        def snapshot(self):
            return ()

    assert request.index_version == "in_memory_index_v1"
    assert isinstance(StubIndex(), KnowledgeIndex)
    with pytest.raises(PydanticValidationError):
        IndexBuildRequest.model_validate({"chunks": [], "index_version": "x"})
    with pytest.raises(PydanticValidationError):
        IndexBuildRequest.model_validate(
            {"chunks": [chunk().model_dump(mode="json")], "api_key": "x"}
        )


def test_index_build_result_serializes_without_vectors_or_keys() -> None:
    result = InMemoryKnowledgeIndex().build(IndexBuildRequest(chunks=[chunk()]))
    payload = result.model_dump(mode="json")
    serialized = json.dumps(payload)

    assert json.loads(serialized)["trace"]["chunk_count"] == 1
    assert "embedding" not in serialized.casefold()
    assert "api_key" not in serialized.casefold()
    assert isinstance(result, IndexBuildResult)


def test_in_memory_index_build_snapshot_get_and_order_are_stable() -> None:
    chunks = [
        chunk("kc_b", document_id="doc_b", sequence=2),
        chunk("kc_a", document_id="doc_a", sequence=1),
    ]
    first = InMemoryKnowledgeIndex()
    second = InMemoryKnowledgeIndex()
    first_result = first.build(IndexBuildRequest(chunks=chunks))
    second_result = second.build(IndexBuildRequest(chunks=list(reversed(chunks))))

    assert first_result.trace.build_id == second_result.trace.build_id
    assert [item.chunk_id for item in first.snapshot()] == ["kc_a", "kc_b"]
    assert first.get("kc_a").document_id == "doc_a"
    assert first.get("missing") is None


def test_duplicate_chunk_id_rejects_build_and_keeps_existing_snapshot() -> None:
    index = InMemoryKnowledgeIndex()
    index.build(IndexBuildRequest(chunks=[chunk("kc_original")]))
    before = [item.chunk_id for item in index.snapshot()]
    duplicate = chunk("kc_dup", document_id="doc_a")
    result = index.build(IndexBuildRequest(chunks=[duplicate, duplicate]))

    assert [error.code for error in result.errors] == ["INDEX_DUPLICATE_CHUNK_ID"]
    assert result.trace.duplicate_chunk_ids == ["kc_dup"]
    assert [item.chunk_id for item in index.snapshot()] == before


def test_build_replaces_snapshot_and_returns_defensive_copies() -> None:
    original = chunk("kc_original")
    index = InMemoryKnowledgeIndex()
    index.build(IndexBuildRequest(chunks=[original]))
    original.metadata["topic"] = "mutated"
    returned = index.get("kc_original")
    returned.metadata["topic"] = "mutated_again"

    assert index.get("kc_original").metadata["topic"] == "car_cleanup"
    index.build(IndexBuildRequest(chunks=[chunk("kc_replacement")]))
    assert [item.chunk_id for item in index.snapshot()] == ["kc_replacement"]

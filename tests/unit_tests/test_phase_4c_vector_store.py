from datetime import date
import json

import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.knowledge.contracts import RetrievalRequest
from tk_script_agent_lab.knowledge.embedding_contracts import EmbeddingVector
from tk_script_agent_lab.knowledge.qdrant_vector_store import QdrantLocalVectorStore
from tk_script_agent_lab.knowledge.vector_store_contracts import (
    VectorBuildRequest,
    VectorIndexItem,
    VectorSearchRequest,
)
from tests.unit_tests.phase_4b_helpers import chunk


def vector(item_id: str, values: list[float]) -> EmbeddingVector:
    return EmbeddingVector(item_id=item_id, values=values, dimensions=len(values))


def build_request(items=None) -> VectorBuildRequest:
    items = items or [
        VectorIndexItem(chunk=chunk("kc_a", document_id="doc_a"), vector=vector("kc_a", [1.0, 0.0])),
        VectorIndexItem(chunk=chunk("kc_b", document_id="doc_b"), vector=vector("kc_b", [0.0, 1.0])),
    ]
    return VectorBuildRequest(items=items, collection_name="test_collection", index_version="qdrant_local_v1")


def search_request(**overrides) -> VectorSearchRequest:
    payload = {
        "query_vector": vector("query", [1.0, 0.0]),
        "retrieval_request": RetrievalRequest(
            stage="creative",
            target_market="US",
            product_category="car vacuum cleaner",
            query="cup holder crumbs",
            limit=2,
            filters={"effective_on": "2026-07-31"},
        ),
        "collection_name": "test_collection",
    }
    payload.update(overrides)
    return VectorSearchRequest(**payload)


def test_vector_store_contracts_validate_and_serialize() -> None:
    request = build_request()
    result = QdrantLocalVectorStore().build(request)
    payload = json.dumps(result.model_dump(mode="json"))

    assert result.trace.status == "SUCCESS"
    assert "api_key" not in payload.casefold()
    with pytest.raises(PydanticValidationError):
        VectorIndexItem(chunk=chunk("kc_x"), vector=vector("other", [1.0]))
    with pytest.raises(PydanticValidationError):
        VectorBuildRequest(
            items=[VectorIndexItem(chunk=chunk("kc_a"), vector=vector("kc_a", [1.0]))],
            collection_name="../bad",
            index_version="v",
        )


def test_qdrant_build_search_filter_limit_and_defensive_copy() -> None:
    store = QdrantLocalVectorStore()
    result = store.build(
        build_request(
            [
                VectorIndexItem(chunk=chunk("kc_a", document_id="doc_a"), vector=vector("kc_a", [1.0, 0.0])),
                VectorIndexItem(chunk=chunk("kc_b", document_id="doc_b"), vector=vector("kc_b", [0.0, 1.0])),
                VectorIndexItem(chunk=chunk("kc_jp", target_markets=["JP"]), vector=vector("kc_jp", [1.0, 0.0])),
                VectorIndexItem(chunk=chunk("kc_exp", effective_to=date(2025, 1, 1)), vector=vector("kc_exp", [1.0, 0.0])),
            ]
        )
    )
    search = store.search(search_request())
    returned = store.get_chunk("kc_a")
    returned.metadata["topic"] = "mutated"

    assert result.trace.dimensions == 2
    assert search.trace.candidate_ids == ["kc_a", "kc_b"]
    assert search.trace.selected_ids == ["kc_a", "kc_b"]
    assert search.trace.filters_applied["query_match_mode"] == "vector_similarity_after_metadata_filter"
    assert search.trace.filters_applied["ranking_version"] == "qdrant_cosine_v1"
    assert "exact_rank_v1" not in search.trace.filters_applied.values()
    assert search.hits[0].score >= search.hits[1].score
    assert store.get_chunk("kc_a").metadata["topic"] == "car_cleanup"


def test_qdrant_build_replaces_snapshot_and_failed_build_keeps_old_snapshot(monkeypatch) -> None:
    store = QdrantLocalVectorStore()
    store.build(build_request())
    assert store.get_chunk("kc_a") is not None
    original_upsert = store._client.upsert

    def fail_upsert(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(store._client, "upsert", fail_upsert)
    failed = store.build(build_request([VectorIndexItem(chunk=chunk("kc_new"), vector=vector("kc_new", [1.0, 0.0]))]))
    assert [error.code for error in failed.errors] == ["VECTOR_BUILD_FAILED"]
    assert store.get_chunk("kc_a") is not None
    monkeypatch.setattr(store._client, "upsert", original_upsert)


def test_qdrant_invalid_date_and_metadata_filter() -> None:
    store = QdrantLocalVectorStore()
    store.build(build_request())
    invalid = store.search(search_request(retrieval_request=search_request().retrieval_request.model_copy(update={"filters": {"effective_on": "bad"}})))
    mismatch = store.search(search_request(retrieval_request=search_request().retrieval_request.model_copy(update={"filters": {"topic": "other"}})))

    assert [error.code for error in invalid.errors] == ["RETRIEVAL_FILTER_INVALID"]
    assert mismatch.hits == []

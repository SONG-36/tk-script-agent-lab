from datetime import date
from hashlib import sha256
import json

from qdrant_client import QdrantClient
from qdrant_client.http import models

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.contracts import RetrievalRequest
from tk_script_agent_lab.knowledge.exact_retriever import _metadata_exclusion
from tk_script_agent_lab.knowledge.ingestion_contracts import KnowledgeChunk
from tk_script_agent_lab.knowledge.vector_store_contracts import (
    VectorBuildRequest,
    VectorBuildResult,
    VectorBuildTrace,
    VectorSearchHit,
    VectorSearchRequest,
    VectorSearchResult,
    VectorSearchTrace,
    stable_vector_build_id,
)

QDRANT_STORE_VERSION = "qdrant_local_v1"


class QdrantLocalVectorStore:
    def __init__(self, client: QdrantClient | None = None) -> None:
        self._client = client or QdrantClient(":memory:")
        self._chunks: dict[str, KnowledgeChunk] = {}
        self._point_ids: dict[str, int] = {}
        self._build_trace: VectorBuildTrace | None = None

    @property
    def build_trace(self) -> VectorBuildTrace | None:
        return self._build_trace.model_copy(deep=True) if self._build_trace else None

    def build(self, request: VectorBuildRequest) -> VectorBuildResult:
        build_id = stable_vector_build_id(request)
        dimensions = request.items[0].vector.dimensions if request.items else None
        old_chunks = self._chunks
        old_point_ids = self._point_ids
        old_trace = self._build_trace
        try:
            if self._client.collection_exists(request.collection_name):
                self._client.delete_collection(request.collection_name)
            self._client.create_collection(
                request.collection_name,
                vectors_config=models.VectorParams(size=dimensions, distance=models.Distance.COSINE),
            )
            points = [
                models.PointStruct(
                    id=_point_id(item.chunk.chunk_id),
                    vector=item.vector.values,
                    payload=_payload(item.chunk),
                )
                for item in request.items
            ]
            self._client.upsert(request.collection_name, points=points, wait=True)
        except Exception as exc:  # noqa: BLE001 - adapter boundary maps client failures.
            self._chunks = old_chunks
            self._point_ids = old_point_ids
            self._build_trace = old_trace
            return _build_failed(request, build_id, dimensions, type(exc).__name__)
        self._chunks = {item.chunk.chunk_id: item.chunk.model_copy(deep=True) for item in request.items}
        self._point_ids = {chunk_id: _point_id(chunk_id) for chunk_id in self._chunks}
        trace = VectorBuildTrace(
            build_id=build_id,
            store_type="qdrant_local",
            store_version=QDRANT_STORE_VERSION,
            collection_name=request.collection_name,
            input_ids=[item.chunk.chunk_id for item in request.items],
            indexed_ids=sorted(self._chunks),
            rejected_ids=[],
            dimensions=dimensions,
            status="SUCCESS",
        )
        self._build_trace = trace
        return VectorBuildResult(trace=trace, errors=[])

    def search(self, request: VectorSearchRequest) -> VectorSearchResult:
        filters_applied = _vector_filters_applied(request.retrieval_request)
        if not self._chunks:
            return _search_failed(request, [], filters_applied, "VECTOR_STORE_EMPTY", "Vector store has not been built.")
        effective_date = _effective_date(request)
        if isinstance(effective_date, ValidationError):
            return _search_failed(request, sorted(self._chunks), filters_applied, effective_date.code, effective_date.message, effective_date)
        candidate_ids = [
            chunk_id
            for chunk_id, chunk in sorted(self._chunks.items())
            if _metadata_exclusion(chunk, request.retrieval_request, effective_date) is None
        ]
        if not candidate_ids:
            return VectorSearchResult(
                hits=[],
                trace=_search_trace(request, candidate_ids, [], filters_applied, "SUCCESS"),
                errors=[],
            )
        query_filter = models.Filter(
            must=[models.HasIdCondition(has_id=[self._point_ids[item] for item in candidate_ids])]
        )
        try:
            response = self._client.query_points(
                request.collection_name,
                query=request.query_vector.values,
                query_filter=query_filter,
                limit=request.retrieval_request.limit,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:  # noqa: BLE001
            return _search_failed(request, candidate_ids, filters_applied, "VECTOR_SEARCH_FAILED", type(exc).__name__)
        hits = [
            VectorSearchHit(chunk_id=str(point.payload["chunk_id"]), score=float(point.score))
            for point in response.points
        ]
        return VectorSearchResult(
            hits=hits,
            trace=_search_trace(
                request,
                candidate_ids,
                [hit.chunk_id for hit in hits],
                filters_applied,
                "SUCCESS",
            ),
            errors=[],
        )

    def get_chunk(self, chunk_id: str) -> KnowledgeChunk | None:
        chunk = self._chunks.get(chunk_id)
        return chunk.model_copy(deep=True) if chunk else None


def _effective_date(request: VectorSearchRequest) -> date | ValidationError | None:
    effective_on = request.retrieval_request.filters.get("effective_on")
    if not effective_on:
        return None
    try:
        return date.fromisoformat(effective_on)
    except ValueError:
        return ValidationError(
            code="RETRIEVAL_FILTER_INVALID",
            message="effective_on must use YYYY-MM-DD.",
            object_type="RetrievalRequest",
            object_id=None,
            field="filters.effective_on",
            related_id=None,
        )


def _search_trace(
    request: VectorSearchRequest,
    candidate_ids: list[str],
    selected_ids: list[str],
    filters_applied: dict[str, str],
    status: str,
) -> VectorSearchTrace:
    payload = {
        "query_vector_id": request.query_vector.item_id,
        "retrieval_request": request.retrieval_request.model_dump(mode="json"),
        "collection_name": request.collection_name,
        "candidate_ids": candidate_ids,
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return VectorSearchTrace(
        search_id=f"vs_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}",
        collection_name=request.collection_name,
        candidate_ids=candidate_ids,
        selected_ids=selected_ids,
        filters_applied=filters_applied,
        status=status,
    )


def _vector_filters_applied(request: RetrievalRequest) -> dict[str, str]:
    values = {
        "query": request.query,
        "target_market": request.target_market,
        "product_category": request.product_category,
        "stage": request.stage,
        "effective_on": request.filters.get("effective_on", ""),
        "query_match_mode": "vector_similarity_after_metadata_filter",
        "ranking_version": "qdrant_cosine_v1",
    }
    for key, value in request.filters.items():
        if key != "effective_on":
            values[f"metadata:{key}"] = value
    return values


def _build_failed(
    request: VectorBuildRequest,
    build_id: str,
    dimensions: int | None,
    reason: str,
) -> VectorBuildResult:
    trace = VectorBuildTrace(
        build_id=build_id,
        store_type="qdrant_local",
        store_version=QDRANT_STORE_VERSION,
        collection_name=request.collection_name,
        input_ids=[item.chunk.chunk_id for item in request.items],
        indexed_ids=[],
        rejected_ids=[item.chunk.chunk_id for item in request.items],
        dimensions=dimensions,
        status="FAILED",
    )
    return VectorBuildResult(
        trace=trace,
        errors=[
            ValidationError(
                code="VECTOR_BUILD_FAILED",
                message=f"Qdrant local build failed: {reason}",
                object_type="QdrantLocalVectorStore",
                object_id=request.collection_name,
                field=None,
                related_id=None,
            )
        ],
    )


def _search_failed(
    request: VectorSearchRequest,
    candidate_ids: list[str],
    filters_applied: dict[str, str],
    code: str,
    message: str,
    error: ValidationError | None = None,
) -> VectorSearchResult:
    return VectorSearchResult(
        hits=[],
        trace=_search_trace(request, candidate_ids, [], filters_applied, "FAILED"),
        errors=[
            error
            or ValidationError(
                code=code,
                message=message,
                object_type="QdrantLocalVectorStore",
                object_id=request.collection_name,
                field=None,
                related_id=None,
            )
        ],
    )


def _payload(chunk: KnowledgeChunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "sequence": chunk.sequence,
        "title": chunk.title,
        "content": chunk.content,
        "source_reference": chunk.source.source_reference,
        "provenance_type": chunk.provenance_type,
        "evidence_status": chunk.evidence_status,
        "target_markets": chunk.target_markets,
        "product_categories": chunk.product_categories,
        "task_stages": chunk.task_stages,
        "effective_from": chunk.effective_from.isoformat() if chunk.effective_from else None,
        "effective_to": chunk.effective_to.isoformat() if chunk.effective_to else None,
        "metadata": chunk.metadata,
        "document_version": chunk.document_version,
        "language": chunk.language,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
    }


def _point_id(chunk_id: str) -> int:
    return int(sha256(chunk_id.encode("utf-8")).hexdigest()[:15], 16)

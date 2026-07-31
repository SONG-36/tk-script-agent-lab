from hashlib import sha256
import json

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.contracts import (
    RetrievedKnowledge,
    RetrievalExclusion,
    RetrievalRequest,
    RetrievalResult,
    RetrievalTrace,
)
from tk_script_agent_lab.knowledge.embedding_contracts import (
    EmbeddingItem,
    EmbeddingProvider,
    EmbeddingRequest,
)
from tk_script_agent_lab.knowledge.exact_retriever import RESERVED_METADATA_FIELDS
from tk_script_agent_lab.knowledge.ingestion_contracts import KnowledgeChunk
from tk_script_agent_lab.knowledge.vector_store_contracts import VectorSearchRequest, VectorStore

VECTOR_TRACE_ONLY_FILTERS = {"query_version"}


class VectorKnowledgeRetriever:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        embedding_model: str,
        collection_name: str,
        retriever_version: str = "vector_retriever_v1",
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._embedding_model = embedding_model
        self._collection_name = collection_name
        self._retriever_version = retriever_version

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        embedding_request = EmbeddingRequest(
            items=[EmbeddingItem(item_id=_query_id(request), text=request.query)],
            model=self._embedding_model,
            provider_version="openai_embedding_v1",
        )
        embedding_result = self._embedding_provider.embed(embedding_request)
        build_id = _vector_build_id(self._vector_store)
        if embedding_result.errors:
            return _result(
                request,
                build_id,
                self._embedding_model,
                self._retriever_version,
                [],
                [],
                [],
                _vector_filters_applied(request),
                embedding_result.errors,
            )
        search_result = self._vector_store.search(
            VectorSearchRequest(
                query_vector=embedding_result.vectors[0],
                retrieval_request=request,
                collection_name=self._collection_name,
            )
        )
        if search_result.errors:
            return _result(
                request,
                build_id,
                self._embedding_model,
                self._retriever_version,
                search_result.trace.candidate_ids,
                [],
                [],
                search_result.trace.filters_applied,
                search_result.errors,
            )
        selected: list[RetrievedKnowledge] = []
        errors: list[ValidationError] = []
        for hit in search_result.hits:
            chunk = self._vector_store.get_chunk(hit.chunk_id)
            if chunk is None:
                errors.append(
                    ValidationError(
                        code="VECTOR_CHUNK_NOT_FOUND",
                        message="Vector search hit could not be resolved to a KnowledgeChunk.",
                        object_type="KnowledgeChunk",
                        object_id=hit.chunk_id,
                        field="chunk_id",
                        related_id=None,
                    )
                )
                continue
            selected.append(_to_retrieved(chunk, hit.score))
        selected_ids = {item.knowledge_id for item in selected}
        excluded = [
            RetrievalExclusion(knowledge_id=chunk_id, reason="vector_not_selected")
            for chunk_id in search_result.trace.candidate_ids
            if chunk_id not in selected_ids
        ]
        return _result(
            request,
            build_id,
            self._embedding_model,
            self._retriever_version,
            search_result.trace.candidate_ids,
            selected,
            excluded,
            search_result.trace.filters_applied,
            errors,
        )


def _to_retrieved(chunk: KnowledgeChunk, score: float) -> RetrievedKnowledge:
    reserved = {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "sequence": str(chunk.sequence),
        "document_version": chunk.document_version,
        "char_start": str(chunk.char_start),
        "char_end": str(chunk.char_end),
        "language": chunk.language,
    }
    metadata = {key: value for key, value in chunk.metadata.items() if key not in RESERVED_METADATA_FIELDS}
    metadata.update(reserved)
    return RetrievedKnowledge(
        knowledge_id=chunk.chunk_id,
        title=chunk.title,
        content=chunk.content,
        kind=metadata.get("kind", "knowledge_chunk"),
        provenance_type=chunk.provenance_type,
        evidence_status=chunk.evidence_status,
        source_reference=chunk.source.source_reference,
        metadata=metadata,
        score=score,
    )


def _result(
    request: RetrievalRequest,
    build_id: str,
    embedding_model: str,
    retriever_version: str,
    candidate_ids: list[str],
    selected: list[RetrievedKnowledge],
    excluded: list[RetrievalExclusion],
    filters_applied: dict[str, str],
    errors: list[ValidationError],
) -> RetrievalResult:
    trace = RetrievalTrace(
        retriever_type="vector",
        retriever_version=retriever_version,
        request_id=_stable_vector_request_id(request, build_id, embedding_model, retriever_version),
        candidate_ids=candidate_ids,
        selected_ids=[item.knowledge_id for item in selected],
        excluded=excluded,
        filters_applied=filters_applied,
    )
    return RetrievalResult(items=selected, trace=trace, errors=errors)


def _stable_vector_request_id(
    request: RetrievalRequest,
    build_id: str,
    embedding_model: str,
    retriever_version: str,
) -> str:
    payload = {
        "request": request.model_dump(mode="json"),
        "embedding_model": embedding_model,
        "collection_build_id": build_id,
        "retriever_version": retriever_version,
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"rr_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"


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
            values[key if key in VECTOR_TRACE_ONLY_FILTERS else f"metadata:{key}"] = value
    return values


def _query_id(request: RetrievalRequest) -> str:
    normalized = json.dumps(request.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"query_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"


def _vector_build_id(vector_store: VectorStore) -> str:
    trace = getattr(vector_store, "build_trace", None)
    trace_value = trace() if callable(trace) else trace
    build_id = getattr(trace_value, "build_id", None)
    return build_id or "vb_unbuilt"

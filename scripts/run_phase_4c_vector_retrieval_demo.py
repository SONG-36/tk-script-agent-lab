from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json
import os
import sys

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.chunking import DEFAULT_CHUNKER_VERSION
from tk_script_agent_lab.knowledge.contracts import RetrievalRequest
from tk_script_agent_lab.knowledge.embedding_contracts import (
    EmbeddingItem,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTrace,
    EmbeddingVector,
    stable_embedding_request_id,
)
from tk_script_agent_lab.knowledge.ingestion_contracts import IngestionRequest, KnowledgeDocument
from tk_script_agent_lab.knowledge.ingestor import DEFAULT_INGESTOR_VERSION, DeterministicKnowledgeIngestor
from tk_script_agent_lab.knowledge.openai_embedding import (
    OPENAI_EMBEDDING_PROVIDER_VERSION,
    OpenAIEmbeddingProvider,
)
from tk_script_agent_lab.knowledge.qdrant_vector_store import QdrantLocalVectorStore
from tk_script_agent_lab.knowledge.retrieval_eval import RetrievalEvalCase, RetrievalEvaluator
from tk_script_agent_lab.knowledge.vector_retriever import VectorKnowledgeRetriever
from tk_script_agent_lab.knowledge.vector_store_contracts import VectorBuildRequest, VectorIndexItem

FIXTURE_DIR = Path("data/golden_cases/rag_retrieval_v1")
COLLECTION_NAME = "phase_4c_vector_demo"
PREVIEW_CHARS = 96


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.confirm_live:
        print("Refusing to run live vector demo without --confirm-live.", file=sys.stderr)
        return 2
    embedding_model = args.embedding_model or os.environ.get("OPENAI_EMBEDDING_MODEL")
    if not embedding_model:
        print("Embedding model is required via --embedding-model or OPENAI_EMBEDDING_MODEL.", file=sys.stderr)
        return 2
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required for the Phase 4C vector demo.", file=sys.stderr)
        return 2

    ingestion = _ingest_fixture()
    provider = OpenAIEmbeddingProvider()
    document_calls_before = provider.call_count
    build_embedding = provider.embed(
        EmbeddingRequest(
            items=[EmbeddingItem(item_id=chunk.chunk_id, text=f"{chunk.title}\n{chunk.content}") for chunk in ingestion.chunks],
            model=embedding_model,
            provider_version=OPENAI_EMBEDDING_PROVIDER_VERSION,
        )
    )
    document_embedding_api_calls = provider.call_count - document_calls_before
    store = QdrantLocalVectorStore()
    vector_build = store.build(
        VectorBuildRequest(
            items=[
                VectorIndexItem(chunk=chunk, vector=vector)
                for chunk, vector in zip(ingestion.chunks, build_embedding.vectors, strict=False)
            ],
            collection_name=COLLECTION_NAME,
            index_version="qdrant_local_v1",
        )
    ) if not build_embedding.errors else None
    request = RetrievalRequest(
        stage=args.stage,
        target_market=args.target_market,
        product_category=args.product_category,
        query=args.query,
        limit=args.limit,
        filters={"effective_on": args.effective_on} if args.effective_on else {},
    )
    query_embedding = None
    query_embedding_api_calls = 0
    precomputed_provider = None
    retrieval = None
    if vector_build and not vector_build.errors:
        query_request = EmbeddingRequest(
            items=_query_embedding_items(request, args.run_eval),
            model=embedding_model,
            provider_version=OPENAI_EMBEDDING_PROVIDER_VERSION,
        )
        query_calls_before = provider.call_count
        query_embedding = provider.embed(query_request)
        query_embedding_api_calls = provider.call_count - query_calls_before
        if not query_embedding.errors:
            precomputed_provider = _PrecomputedQueryEmbeddingProvider(
                query_embedding,
                {item.item_id: item.text for item in query_request.items},
            )
            retrieval = VectorKnowledgeRetriever(
                embedding_provider=precomputed_provider,
                vector_store=store,
                embedding_model=embedding_model,
                collection_name=COLLECTION_NAME,
            ).retrieve(request)
    report = {
        "embedding_api_call_count": document_embedding_api_calls + query_embedding_api_calls,
        "document_embedding_api_calls": document_embedding_api_calls,
        "query_embedding_api_calls": query_embedding_api_calls,
        "ingestion": {
            "document_count": ingestion.trace.document_count,
            "chunk_count": ingestion.trace.chunk_count,
            "errors": [error.model_dump(mode="json") for error in ingestion.errors],
        },
        "embedding_build": _embedding_summary(build_embedding),
        "query_embedding": _embedding_summary(query_embedding),
        "vector_index": _vector_build_summary(vector_build),
        "retrieval": _retrieval_summary(retrieval, request),
    }
    if args.run_eval and retrieval and not retrieval.errors and precomputed_provider is not None:
        report["eval"] = _eval_summary(store, embedding_model, precomputed_provider)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    has_errors = (
        ingestion.errors
        or build_embedding.errors
        or (vector_build and vector_build.errors)
        or (query_embedding and query_embedding.errors)
        or (retrieval and retrieval.errors)
    )
    return 1 if has_errors else 0


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the Phase 4C live OpenAI embedding + Qdrant local vector demo.")
    parser.add_argument("--embedding-model")
    parser.add_argument("--query", default="cup holder crumbs")
    parser.add_argument("--target-market", default="US")
    parser.add_argument("--product-category", default="car vacuum cleaner")
    parser.add_argument("--stage", choices=["creative", "script"], default="creative")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--effective-on", default="2026-07-31")
    parser.add_argument("--run-eval", action="store_true")
    parser.add_argument("--confirm-live", action="store_true")
    return parser


def _ingest_fixture():
    documents = [
        KnowledgeDocument.model_validate(item)
        for item in json.loads((FIXTURE_DIR / "retrieval_documents.json").read_text(encoding="utf-8"))
    ]
    return DeterministicKnowledgeIngestor().ingest(
        IngestionRequest(
            documents=documents,
            max_chars=1000,
            overlap_chars=80,
            chunker_version=DEFAULT_CHUNKER_VERSION,
            ingestor_version=DEFAULT_INGESTOR_VERSION,
        )
    )


def _query_embedding_items(main_request: RetrievalRequest, include_eval: bool) -> list[EmbeddingItem]:
    query_texts = [main_request.query]
    if include_eval:
        query_texts.extend(RetrievalRequest.model_validate(payload["request"]).query for payload in _eval_payloads())
    seen: set[str] = set()
    items: list[EmbeddingItem] = []
    for query_text in query_texts:
        if query_text in seen:
            continue
        seen.add(query_text)
        query_id = f"query_{sha256(query_text.encode('utf-8')).hexdigest()[:12]}"
        items.append(EmbeddingItem(item_id=query_id, text=query_text))
    return items


class _PrecomputedQueryEmbeddingProvider:
    def __init__(self, result: EmbeddingResult, text_by_item_id: dict[str, str]) -> None:
        self.calls = 0
        self._vectors_by_text = {
            text_by_item_id[vector.item_id]: vector.model_copy(deep=True)
            for vector in result.vectors
            if vector.item_id in text_by_item_id
        }

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.calls += 1
        vectors = []
        for item in request.items:
            vector = self._vectors_by_text.get(item.text)
            if vector is None:
                return _precomputed_query_embedding_failed(request, item.item_id)
            vectors.append(
                EmbeddingVector(
                    item_id=item.item_id,
                    values=list(vector.values),
                    dimensions=vector.dimensions,
                )
            )
        return EmbeddingResult(
            vectors=vectors,
            trace=EmbeddingTrace(
                request_id=stable_embedding_request_id(request),
                provider="openai",
                provider_version=request.provider_version,
                model=request.model,
                input_ids=[item.item_id for item in request.items],
                output_ids=[vector.item_id for vector in vectors],
                dimensions=vectors[0].dimensions if vectors else None,
                status="SUCCESS",
                error_code=None,
            ),
            errors=[],
        )


def _precomputed_query_embedding_failed(request: EmbeddingRequest, missing_item_id: str) -> EmbeddingResult:
    error_code = "EMBEDDING_OUTPUT_INVALID"
    return EmbeddingResult(
        vectors=[],
        trace=EmbeddingTrace(
            request_id=stable_embedding_request_id(request),
            provider="openai",
            provider_version=request.provider_version,
            model=request.model,
            input_ids=[item.item_id for item in request.items],
            output_ids=[],
            dimensions=None,
            status="FAILED",
            error_code=error_code,
        ),
        errors=[
            ValidationError(
                code=error_code,
                message="Precomputed query embedding is missing for the requested query text.",
                object_type="_PrecomputedQueryEmbeddingProvider",
                object_id=None,
                field="items",
                related_id=missing_item_id,
            )
        ],
    )


def _embedding_summary(result) -> dict:
    if result is None:
        return {"status": "SKIPPED", "errors": []}
    return {
        "model": result.trace.model,
        "request_id": result.trace.request_id,
        "input_count": len(result.trace.input_ids),
        "vector_count": len(result.vectors),
        "dimensions": result.trace.dimensions,
        "status": result.trace.status,
        "errors": [error.model_dump(mode="json") for error in result.errors],
    }


def _vector_build_summary(result) -> dict:
    if result is None:
        return {"status": "SKIPPED", "errors": []}
    return {
        "build_id": result.trace.build_id,
        "collection": result.trace.collection_name,
        "indexed_ids": result.trace.indexed_ids,
        "dimensions": result.trace.dimensions,
        "status": result.trace.status,
        "errors": [error.model_dump(mode="json") for error in result.errors],
    }


def _retrieval_summary(result, request: RetrievalRequest) -> dict:
    if result is None:
        return {"query": request.query, "status": "SKIPPED", "errors": []}
    return {
        "request_id": result.trace.request_id,
        "query": request.query,
        "filters": result.trace.filters_applied,
        "selected_items": [
            {
                "chunk_id": item.knowledge_id,
                "document_id": item.metadata["document_id"],
                "title": item.title,
                "score": item.score,
                "source_reference": item.source_reference,
                "content_preview": _preview(item.content),
                "provenance": item.provenance_type,
                "evidence_status": item.evidence_status,
            }
            for item in result.items
        ],
        "errors": [error.model_dump(mode="json") for error in result.errors],
    }


def _eval_payloads() -> list[dict]:
    return json.loads((FIXTURE_DIR / "eval_cases.json").read_text(encoding="utf-8"))


def _eval_summary(store: QdrantLocalVectorStore, model: str, provider: EmbeddingProvider) -> dict:
    pairs = []
    doc_to_chunk_ids: dict[str, list[str]] = {}
    for chunk_id in store.build_trace.indexed_ids if store.build_trace else []:
        chunk = store.get_chunk(chunk_id)
        if chunk:
            doc_to_chunk_ids.setdefault(chunk.document_id, []).append(chunk.chunk_id)
    retriever = VectorKnowledgeRetriever(
        embedding_provider=provider,
        vector_store=store,
        embedding_model=model,
        collection_name=COLLECTION_NAME,
    )
    for payload in _eval_payloads():
        case = RetrievalEvalCase(
            case_id=payload["case_id"],
            request=RetrievalRequest.model_validate(payload["request"]),
            expected_ids=[chunk_id for doc_id in payload["expected_document_ids"] for chunk_id in doc_to_chunk_ids.get(doc_id, [])],
            forbidden_ids=[chunk_id for doc_id in payload["forbidden_document_ids"] for chunk_id in doc_to_chunk_ids.get(doc_id, [])],
            minimum_recall=payload["minimum_recall"],
            expected_top_id=None,
        )
        pairs.append((case, retriever.retrieve(case.request)))
    summary = RetrievalEvaluator().evaluate_many(pairs)
    return {
        "total_cases": summary.total_cases,
        "passed": summary.passed_cases,
        "failed": summary.failed_cases,
        "mean_recall": summary.mean_recall,
        "cases": [result.model_dump(mode="json") for result in summary.results],
    }


def _preview(content: str) -> str:
    return content if len(content) <= PREVIEW_CHARS else f"{content[:PREVIEW_CHARS].rstrip()}..."


if __name__ == "__main__":
    raise SystemExit(main())

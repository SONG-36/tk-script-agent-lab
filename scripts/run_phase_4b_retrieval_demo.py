from argparse import ArgumentParser
from pathlib import Path
import json

from tk_script_agent_lab.knowledge.chunking import DEFAULT_CHUNKER_VERSION
from tk_script_agent_lab.knowledge.contracts import RetrievalRequest
from tk_script_agent_lab.knowledge.exact_retriever import (
    ExactMetadataKnowledgeRetriever,
    exclusion_reason_counts,
)
from tk_script_agent_lab.knowledge.in_memory_index import InMemoryKnowledgeIndex
from tk_script_agent_lab.knowledge.index_contracts import IndexBuildRequest
from tk_script_agent_lab.knowledge.ingestion_contracts import IngestionRequest, KnowledgeDocument
from tk_script_agent_lab.knowledge.ingestor import (
    DEFAULT_INGESTOR_VERSION,
    DeterministicKnowledgeIngestor,
)
from tk_script_agent_lab.knowledge.retrieval_eval import RetrievalEvalCase, RetrievalEvaluator

FIXTURE_DIR = Path("data/golden_cases/rag_retrieval_v1")
PREVIEW_CHARS = 96


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    documents = _load_documents()
    ingestion = DeterministicKnowledgeIngestor().ingest(
        IngestionRequest(
            documents=documents,
            max_chars=1000,
            overlap_chars=80,
            chunker_version=DEFAULT_CHUNKER_VERSION,
            ingestor_version=DEFAULT_INGESTOR_VERSION,
        )
    )
    index = InMemoryKnowledgeIndex()
    index_result = index.build(
        IndexBuildRequest(chunks=ingestion.chunks, index_version="in_memory_index_v1")
    )
    request = RetrievalRequest(
        stage=args.stage,
        target_market=args.target_market,
        product_category=args.product_category,
        query=args.query,
        limit=args.limit,
        filters=_filters(args.effective_on),
    )
    retrieval = ExactMetadataKnowledgeRetriever(index).retrieve(request)
    report = {
        "ingestion": _ingestion_summary(ingestion),
        "index": _index_summary(index_result),
        "retrieval": _retrieval_summary(retrieval),
    }
    if args.run_eval:
        report["eval"] = _eval_summary(index)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not ingestion.errors and not index_result.errors and not retrieval.errors else 1


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the Phase 4B offline exact retrieval demo.")
    parser.add_argument("--query", default="cup holder crumbs")
    parser.add_argument("--target-market", default="US")
    parser.add_argument("--product-category", default="car vacuum cleaner")
    parser.add_argument("--stage", choices=["creative", "script"], default="creative")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--effective-on", default="2026-07-31")
    parser.add_argument("--run-eval", action="store_true")
    return parser


def _load_documents() -> list[KnowledgeDocument]:
    payload = json.loads((FIXTURE_DIR / "retrieval_documents.json").read_text(encoding="utf-8"))
    return [KnowledgeDocument.model_validate(item) for item in payload]


def _filters(effective_on: str | None) -> dict[str, str]:
    return {"effective_on": effective_on} if effective_on else {}


def _ingestion_summary(result) -> dict:
    return {
        "request_id": result.trace.request_id,
        "accepted_documents": result.trace.accepted_document_ids,
        "rejected_documents": result.trace.rejected_document_ids,
        "chunk_count": result.trace.chunk_count,
        "errors": [error.model_dump(mode="json") for error in result.errors],
    }


def _index_summary(result) -> dict:
    return {
        "build_id": result.trace.build_id,
        "indexed_chunk_ids": result.trace.indexed_chunk_ids,
        "duplicate_chunk_ids": result.trace.duplicate_chunk_ids,
        "errors": [error.model_dump(mode="json") for error in result.errors],
    }


def _retrieval_summary(result) -> dict:
    return {
        "request_id": result.trace.request_id,
        "query": result.trace.filters_applied.get("query", ""),
        "filters": result.trace.filters_applied,
        "candidate_count": len(result.trace.candidate_ids),
        "selected_count": len(result.items),
        "selected_items": [
            {
                "knowledge_id": item.knowledge_id,
                "document_id": item.metadata["document_id"],
                "sequence": item.metadata["sequence"],
                "title": item.title,
                "score": item.score,
                "source_reference": item.source_reference,
                "content_preview": _preview(item.content),
                "provenance": item.provenance_type,
                "evidence_status": item.evidence_status,
            }
            for item in result.items
        ],
        "exclusion_count": len(result.trace.excluded),
        "exclusion_reason_summary": exclusion_reason_counts(result),
        "errors": [error.model_dump(mode="json") for error in result.errors],
    }


def _eval_summary(index: InMemoryKnowledgeIndex) -> dict:
    pairs = []
    retriever = ExactMetadataKnowledgeRetriever(index)
    for payload in json.loads((FIXTURE_DIR / "eval_cases.json").read_text(encoding="utf-8")):
        case = _eval_case_from_payload(payload, index)
        pairs.append((case, retriever.retrieve(case.request)))
    summary = RetrievalEvaluator().evaluate_many(pairs)
    return {
        "total_cases": summary.total_cases,
        "passed": summary.passed_cases,
        "failed": summary.failed_cases,
        "mean_recall": summary.mean_recall,
        "cases": [
            {
                "case_id": result.case_id,
                "selected_ids": result.selected_ids,
                "missing_expected": result.missing_expected_ids,
                "forbidden_hits": result.forbidden_hits,
                "recall": result.recall,
                "passed": result.passed,
            }
            for result in summary.results
        ],
    }


def _eval_case_from_payload(payload: dict, index: InMemoryKnowledgeIndex) -> RetrievalEvalCase:
    doc_to_chunk_ids: dict[str, list[str]] = {}
    for chunk in index.snapshot():
        doc_to_chunk_ids.setdefault(chunk.document_id, []).append(chunk.chunk_id)
    expected_ids = [
        chunk_id
        for document_id in payload["expected_document_ids"]
        for chunk_id in doc_to_chunk_ids.get(document_id, [])
    ]
    forbidden_ids = [
        chunk_id
        for document_id in payload["forbidden_document_ids"]
        for chunk_id in doc_to_chunk_ids.get(document_id, [])
    ]
    expected_top_id = None
    if payload.get("expected_top_document_id"):
        ids = doc_to_chunk_ids.get(payload["expected_top_document_id"], [])
        expected_top_id = ids[0] if ids else None
    return RetrievalEvalCase(
        case_id=payload["case_id"],
        request=RetrievalRequest.model_validate(payload["request"]),
        expected_ids=expected_ids,
        forbidden_ids=forbidden_ids,
        minimum_recall=payload["minimum_recall"],
        expected_top_id=expected_top_id,
    )


def _preview(content: str) -> str:
    return content if len(content) <= PREVIEW_CHARS else f"{content[:PREVIEW_CHARS].rstrip()}..."


if __name__ == "__main__":
    raise SystemExit(main())

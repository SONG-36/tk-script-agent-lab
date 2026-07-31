from argparse import ArgumentParser
from pathlib import Path
import json
import os
import sys

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from tk_script_agent_lab.domain import (
    CreativeIdea,
    ProductFact,
    ProductProfile,
    ReferenceInsight,
    ReferenceVideo,
    ReviewDecision,
    ScriptDraft,
    ScriptScene,
    SellingPoint,
    SourceUsage,
    ValidationError,
)
from tk_script_agent_lab.domain.enums import InsightType, ReferencePlatform, ReviewDecisionType, VerificationStatus
from tk_script_agent_lab.knowledge import CreativeKnowledgeItem, KnowledgeSelectionRecord, RetrievedKnowledge, RetrievalTrace
from tk_script_agent_lab.knowledge.embedding_contracts import EmbeddingTrace
from tk_script_agent_lab.knowledge.loader import load_creative_knowledge_pack
from tk_script_agent_lab.knowledge.vector_store_contracts import VectorBuildTrace
from tk_script_agent_lab.langgraph_app.graph import build_graph
from tk_script_agent_lab.providers import ModelCallRecord
from tk_script_agent_lab.workflow import WorkflowInput, WorkflowStatus, WorkflowStepRecord

DEFAULT_PACK = "tiktok_car_cleaning_v1"
PREVIEW_CHARS = 140


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if _requires_live(args) and not args.confirm_live:
        print(
            "Refusing to run live Phase 4D demo without --confirm-live. "
            "Vector mode can call embeddings; OpenAI creative provider can call chat.",
            file=sys.stderr,
        )
        return 2

    creative_model = args.creative_model
    embedding_model = args.embedding_model
    if args.creative_provider == "openai":
        creative_model = creative_model or os.environ.get("OPENAI_MODEL")
        if not creative_model:
            print("creative model is required via --creative-model or OPENAI_MODEL.", file=sys.stderr)
            return 2
    if args.knowledge_mode == "vector":
        embedding_model = embedding_model or os.environ.get("OPENAI_EMBEDDING_MODEL")
        if not embedding_model:
            print("embedding model is required via --embedding-model or OPENAI_EMBEDDING_MODEL.", file=sys.stderr)
            return 2
    if _requires_live(args) and not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required for selected live Phase 4D mode.", file=sys.stderr)
        return 2

    if args.knowledge_mode in {"static", "vector"} and not args.knowledge_pack:
        print("--knowledge-pack is required for static or vector knowledge mode.", file=sys.stderr)
        return 2

    context = _context(args, creative_model=creative_model, embedding_model=embedding_model)
    result = _run_graph(context)
    report = _report(args, context, result)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["creative"]["interrupt_type"] == "IDEA_SELECTION_REQUIRED" and not report["creative"]["validation_errors"] else 1


def _parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the Phase 4D Creative RAG LangGraph demo.")
    parser.add_argument("--knowledge-mode", choices=["off", "static", "vector"], default="off")
    parser.add_argument("--creative-provider", choices=["fake", "openai"], default="fake")
    parser.add_argument("--creative-model")
    parser.add_argument("--embedding-model")
    parser.add_argument("--knowledge-pack", default=None)
    parser.add_argument("--knowledge-limit", type=int, default=6)
    parser.add_argument("--confirm-live", action="store_true")
    return parser


def _requires_live(args) -> bool:
    return args.creative_provider == "openai" or args.knowledge_mode == "vector"


def _context(args, *, creative_model: str | None, embedding_model: str | None) -> dict:
    return {
        "knowledge_mode": args.knowledge_mode,
        "creative_knowledge_pack": args.knowledge_pack,
        "creative_knowledge_limit": args.knowledge_limit,
        "creative_embedding_model": embedding_model,
        "creative_retrieval_query_version": "creative_retrieval_query_v1",
        "creative_vector_retriever_version": "vector_retriever_v1",
        "creative_provider": args.creative_provider,
        "creative_model": creative_model,
        "creative_prompt_version": "creative_idea_v2",
        "script_provider": "fake",
        "script_model": None,
        "script_prompt_version": "script_draft_v1",
    }


def _run_graph(context: dict) -> dict:
    graph = build_graph(checkpointer=InMemorySaver(serde=_serializer()))
    return graph.invoke(
        json.loads(_studio_input_path().read_text(encoding="utf-8")),
        config={"configurable": {"thread_id": "phase-4d-creative-rag-demo"}},
        context=context,
    )


def _report(args, context: dict, result: dict) -> dict:
    retrieval = result.get("knowledge_retrieval_records", [])
    retrieval_trace = retrieval[0] if retrieval else None
    pack_version = None
    if args.knowledge_pack:
        try:
            pack_version = load_creative_knowledge_pack(args.knowledge_pack).version
        except Exception:  # noqa: BLE001 - config errors are already represented in graph output.
            pack_version = None
    model_records = [_safe_model_record(record) for record in result.get("model_call_records", [])]
    return {
        "config": {
            "knowledge_mode": args.knowledge_mode,
            "pack": args.knowledge_pack,
            "pack_version": pack_version,
            "creative_provider": args.creative_provider,
            "creative_model": context["creative_model"],
            "embedding_model": context["creative_embedding_model"],
            "creative_prompt_version": context["creative_prompt_version"],
            "query_version": context["creative_retrieval_query_version"],
        },
        "runtime": _runtime_summary(result),
        "retrieval": _retrieval_summary(
            retrieval_trace,
            result.get("creative_knowledge_items", []),
            result.get("validation_errors", []),
        ),
        "creative": {
            "ideas": [_idea_summary(idea) for idea in result.get("creative_ideas", [])],
            "source_usages": [
                usage.model_dump(mode="json")
                for idea in result.get("creative_ideas", [])
                for usage in idea.source_usages
            ],
            "risk_notes": [idea.risk_notes for idea in result.get("creative_ideas", [])],
            "model_call_records": model_records,
            "status": str(result.get("status")),
            "interrupt_type": _interrupt_type(result),
            "validation_errors": [error.model_dump(mode="json") for error in result.get("validation_errors", [])],
            "script_draft_is_null": result.get("script_draft") is None,
        },
    }


def _runtime_summary(result: dict) -> dict:
    embeddings = result.get("embedding_records", [])
    builds = result.get("vector_build_records", [])
    filters = result.get("knowledge_retrieval_records", [None])[0].filters_applied if result.get("knowledge_retrieval_records") else {}
    return {
        "runtime_built": result.get("creative_vector_runtime_built", False),
        "runtime_reused": result.get("creative_vector_runtime_reused", False),
        "document_count": int(filters.get("document_count", "0")) if filters else 0,
        "chunk_count": int(filters.get("chunk_count", "0")) if filters else 0,
        "document_embedding_calls": int(filters.get("document_embedding_calls", "0")) if filters else 0,
        "query_embedding_calls": int(filters.get("query_embedding_calls", "0")) if filters else 0,
        "vector_build_id": builds[0].build_id if builds else None,
        "collection": builds[0].collection_name if builds else None,
        "dimensions": builds[0].dimensions if builds else None,
    }


def _retrieval_summary(
    trace: RetrievalTrace | None,
    items: list[RetrievedKnowledge],
    errors: list[ValidationError],
) -> dict:
    if trace is None:
        return {"errors": [error.model_dump(mode="json") for error in errors], "selected_ids": [], "selected_items": []}
    return {
        "request_id": trace.request_id,
        "query_preview": _preview(trace.filters_applied.get("query", "")),
        "retriever_type": trace.retriever_type,
        "candidate_count": len(trace.candidate_ids),
        "selected_ids": trace.selected_ids,
        "selected_items": [
            {
                "knowledge_id": item.knowledge_id,
                "title": item.title,
                "kind": item.kind,
                "score": item.score,
                "provenance": item.provenance_type,
                "evidence_status": item.evidence_status,
                "source_reference": item.source_reference,
                "content_preview": _preview(item.content),
            }
            for item in items
        ],
        "excluded_count": len(trace.excluded),
        "errors": [error.model_dump(mode="json") for error in errors],
    }


def _idea_summary(idea: CreativeIdea) -> dict:
    return {
        "creative_idea_id": idea.creative_idea_id,
        "title": idea.title,
        "hook": idea.hook,
        "concept_summary": idea.concept_summary,
    }


def _safe_model_record(record: ModelCallRecord) -> dict:
    payload = record.model_dump(mode="json")
    payload["response_id_present"] = record.response_id is not None
    payload.pop("response_id", None)
    return payload


def _interrupt_type(result: dict) -> str | None:
    interrupts = result.get("__interrupt__", ())
    return interrupts[0].value.get("type") if interrupts else None


def _preview(value: str) -> str:
    return value if len(value) <= PREVIEW_CHARS else f"{value[:PREVIEW_CHARS].rstrip()}..."


def _studio_input_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "golden_cases" / "car_vacuum_v1" / "studio_input.json"


def _serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=()).with_msgpack_allowlist(
        [
            CreativeIdea,
            CreativeKnowledgeItem,
            EmbeddingTrace,
            InsightType,
            KnowledgeSelectionRecord,
            ModelCallRecord,
            ProductFact,
            ProductProfile,
            ReferenceInsight,
            ReferencePlatform,
            ReferenceVideo,
            RetrievedKnowledge,
            RetrievalTrace,
            ReviewDecision,
            ReviewDecisionType,
            ScriptDraft,
            ScriptScene,
            SellingPoint,
            SourceUsage,
            ValidationError,
            VectorBuildTrace,
            VerificationStatus,
            WorkflowInput,
            WorkflowStatus,
            WorkflowStepRecord,
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())

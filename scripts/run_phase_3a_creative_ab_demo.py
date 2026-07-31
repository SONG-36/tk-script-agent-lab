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
from tk_script_agent_lab.domain.enums import (
    InsightType,
    ReferencePlatform,
    ReviewDecisionType,
    VerificationStatus,
)
from tk_script_agent_lab.knowledge import CreativeKnowledgeItem, KnowledgeSelectionRecord
from tk_script_agent_lab.langgraph_app.graph import build_graph
from tk_script_agent_lab.providers import ModelCallRecord
from tk_script_agent_lab.workflow import WorkflowInput, WorkflowStatus, WorkflowStepRecord


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.confirm_live:
        print(
            "Refusing to run live Phase 3A demo without --confirm-live. "
            "This command can call OpenAI once for control, once for treatment, "
            "or twice for both.",
            file=sys.stderr,
        )
        return 2

    api_key, model = _openai_environment()
    if not api_key:
        print("OPENAI_API_KEY is required for the Phase 3A creative A/B demo.", file=sys.stderr)
        return 1
    if not model:
        print("OPENAI_MODEL is required for the Phase 3A creative A/B demo.", file=sys.stderr)
        return 1

    graph_input = json.loads(_studio_input_path().read_text(encoding="utf-8"))
    report = {
        "input_case": str(_studio_input_path()),
        "model": model,
        "boundary": "No winner is declared by this demo. Use the Phase 3A rubric for human review.",
    }
    results = []
    if args.mode in {"control", "both"}:
        control = _run_variant(
            graph_input,
            thread_id="phase-3a-control",
            context=_control_context(model),
        )
        report["control"] = _summarize(control)
        results.append(control)
    if args.mode in {"treatment", "both"}:
        treatment = _run_variant(
            graph_input,
            thread_id="phase-3a-treatment",
            context=_treatment_context(model),
        )
        report["treatment"] = _summarize(treatment)
        results.append(treatment)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(_is_expected_interrupt(result) for result in results) else 1


def _parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Run the Phase 3A live creative A/B demo. "
            "Requires --confirm-live because it can call OpenAI."
        )
    )
    parser.add_argument(
        "--mode",
        choices=["control", "treatment", "both"],
        default="both",
        help=(
            "Variant to run. control calls OpenAI once, treatment calls OpenAI once, "
            "both calls OpenAI twice. Default: both."
        ),
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="Required confirmation that this command may perform live OpenAI calls.",
    )
    return parser


def _openai_environment() -> tuple[str | None, str | None]:
    return os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_MODEL")


def _control_context(model: str) -> dict:
    return {
        "creative_provider": "openai",
        "creative_model": model,
        "creative_prompt_version": "creative_idea_v2",
        "script_provider": "fake",
        "script_model": None,
        "script_prompt_version": "script_draft_v1",
        "knowledge_mode": "off",
        "creative_knowledge_pack": None,
        "creative_knowledge_limit": 6,
        "knowledge_selector_version": "static_selector_v1",
    }


def _treatment_context(model: str) -> dict:
    return {
        "creative_provider": "openai",
        "creative_model": model,
        "creative_prompt_version": "creative_idea_v2",
        "script_provider": "fake",
        "script_model": None,
        "script_prompt_version": "script_draft_v1",
        "knowledge_mode": "static",
        "creative_knowledge_pack": "tiktok_car_cleaning_v1",
        "creative_knowledge_limit": 6,
        "knowledge_selector_version": "static_selector_v1",
    }


def _run_variant(graph_input: dict, *, thread_id: str, context: dict) -> dict:
    graph = build_graph(checkpointer=InMemorySaver(serde=_serializer()))
    return graph.invoke(
        graph_input,
        config={"configurable": {"thread_id": thread_id}},
        context=context,
    )


def _summarize(result: dict) -> dict:
    records = result.get("knowledge_selection_records", [])
    first_record = records[0] if records else None
    model_records = [
        _safe_model_record(record)
        for record in result.get("model_call_records", [])
        if record.operation == "generate_creative_ideas"
    ]
    knowledge_ids = set(first_record.selected_ids if first_record else [])
    source_ids = [
        usage.source_id
        for idea in result.get("creative_ideas", [])
        for usage in idea.source_usages
    ]
    return {
        "status": str(result.get("status")),
        "interrupt_type": _interrupt_type(result),
        "validation_errors": [error.code for error in result.get("validation_errors", [])],
        "validation_error_details": [
            _validation_error_detail(error)
            for error in result.get("validation_errors", [])
        ],
        "prompt_version": model_records[0]["prompt_version"] if model_records else None,
        "knowledge_mode": first_record.mode if first_record else None,
        "pack_id": first_record.pack_id if first_record else None,
        "pack_version": first_record.pack_version if first_record else None,
        "selected_knowledge_ids": first_record.selected_ids if first_record else [],
        "excluded_count": len(first_record.excluded_items) if first_record else 0,
        "ideas": [
            {
                "creative_idea_id": idea.creative_idea_id,
                "title": idea.title,
                "hook": idea.hook,
                "concept_summary": idea.concept_summary,
                "target_audience": idea.target_audience,
                "source_usages": [
                    {
                        "source_type": usage.source_type,
                        "source_id": usage.source_id,
                        "usage_purpose": usage.usage_purpose,
                    }
                    for usage in idea.source_usages
                ],
                "risk_notes": idea.risk_notes,
            }
            for idea in result.get("creative_ideas", [])
        ],
        "model_call_records": model_records,
        "deterministic_checks": {
            "script_draft_is_null": result.get("script_draft") is None,
            "creative_model_call_count": len(model_records),
            "source_usage_contains_knowledge_id": any(
                source_id in knowledge_ids for source_id in source_ids
            ),
        },
    }


def _safe_model_record(record: ModelCallRecord) -> dict:
    payload = record.model_dump(mode="json")
    payload["response_id_present"] = record.response_id is not None
    payload.pop("response_id", None)
    return payload


def _validation_error_detail(error: ValidationError) -> dict:
    return {
        "code": getattr(error, "code", None),
        "field": getattr(error, "field", None),
        "related_id": getattr(error, "related_id", None),
        "message": getattr(error, "message", None),
    }


def _is_expected_interrupt(result: dict) -> bool:
    return _interrupt_type(result) == "IDEA_SELECTION_REQUIRED" and not result.get("validation_errors")


def _interrupt_type(result: dict) -> str | None:
    interrupts = result.get("__interrupt__", ())
    if not interrupts:
        return None
    return interrupts[0].value.get("type")


def _studio_input_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "golden_cases"
        / "car_vacuum_v1"
        / "studio_input.json"
    )


def _serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=()).with_msgpack_allowlist(
        [
            CreativeIdea,
            CreativeKnowledgeItem,
            InsightType,
            KnowledgeSelectionRecord,
            ModelCallRecord,
            ProductFact,
            ProductProfile,
            ReferenceInsight,
            ReferencePlatform,
            ReferenceVideo,
            ReviewDecision,
            ReviewDecisionType,
            ScriptDraft,
            ScriptScene,
            SellingPoint,
            SourceUsage,
            ValidationError,
            VerificationStatus,
            WorkflowInput,
            WorkflowStatus,
            WorkflowStepRecord,
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())

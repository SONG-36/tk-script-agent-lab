from argparse import ArgumentParser
from pathlib import Path
import json
import os
import sys

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command

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
from tk_script_agent_lab.langgraph_app.graph import build_graph
from tk_script_agent_lab.providers import ModelCallRecord
from tk_script_agent_lab.workflow import WorkflowInput, WorkflowStatus, WorkflowStepRecord


def main() -> int:
    args = _parser().parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    default_model = os.environ.get("OPENAI_MODEL")
    if not api_key:
        print("OPENAI_API_KEY is required for the Phase 2B OpenAI script demo.", file=sys.stderr)
        return 1
    script_model = args.script_model or default_model
    creative_model = args.creative_model or default_model
    if args.script_provider == "openai" and not script_model:
        print("OPENAI_MODEL or --script-model is required for OpenAI script mode.", file=sys.stderr)
        return 1
    if args.creative_provider == "openai" and not creative_model:
        print("OPENAI_MODEL or --creative-model is required for OpenAI creative mode.", file=sys.stderr)
        return 1

    graph_input = json.loads(_studio_input_path().read_text(encoding="utf-8"))
    graph = build_graph(checkpointer=InMemorySaver(serde=_serializer()))
    context = {
        "creative_provider": args.creative_provider,
        "creative_model": creative_model if args.creative_provider == "openai" else None,
        "script_provider": args.script_provider,
        "script_model": script_model if args.script_provider == "openai" else None,
    }
    config = {"configurable": {"thread_id": "phase-2b-openai-script-demo"}}
    first = graph.invoke(graph_input, config=config, context=context)
    if first.get("validation_errors"):
        _print_errors(first)
        return 1
    interrupts = first.get("__interrupt__", ())
    if not interrupts:
        print("Expected IDEA_SELECTION_REQUIRED interrupt but graph did not pause.", file=sys.stderr)
        return 1

    ideas = interrupts[0].value["creative_ideas"]
    selected_idea_id = args.selected_idea_id or ideas[0]["creative_idea_id"]
    result = graph.invoke(
        Command(
            resume={
                "target_id": selected_idea_id,
                "decision": "APPROVED",
                "reviewer": args.reviewer,
                "comment": None,
            }
        ),
        config=config,
        context=context,
    )

    print(f"creative_provider={args.creative_provider}")
    print(f"script_provider={args.script_provider}")
    print(f"selected_idea_id={selected_idea_id}")
    print(f"status={result.get('status')}")
    print(f"validation_errors={[error.code for error in result.get('validation_errors', [])]}")
    for record in result.get("model_call_records", []):
        payload = record.model_dump(mode="json")
        payload["response_id_present"] = record.response_id is not None
        payload.pop("response_id", None)
        print(f"model_call_record={payload}")
    script = result.get("script_draft")
    print(f"script_draft_is_null={script is None}")
    if script is None:
        return 1

    print(f"script_id={script.script_id}")
    print(f"title={script.title}")
    print(f"caption={script.caption}")
    print(f"cta={script.cta}")
    for scene in script.scenes:
        print(
            "scene="
            f"{scene.sequence}:{scene.scene_id}:"
            f"{scene.duration_seconds}:{scene.visual}:{scene.action}:"
            f"{scene.voiceover}:{scene.on_screen_text}"
        )
    for usage in script.source_usages:
        print(
            "source_usage="
            f"{usage.source_type}:{usage.source_id}:{usage.usage_purpose}"
        )
    return 0 if result.get("status") == WorkflowStatus.COMPLETED else 1


def _parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument(
        "--creative-provider",
        choices=["fake", "openai"],
        default="fake",
    )
    parser.add_argument(
        "--script-provider",
        choices=["openai"],
        default="openai",
    )
    parser.add_argument("--creative-model", default=None)
    parser.add_argument("--script-model", default=None)
    parser.add_argument("--selected-idea-id", default=None)
    parser.add_argument("--reviewer", default="phase-2b-reviewer")
    return parser


def _studio_input_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "golden_cases"
        / "car_vacuum_v1"
        / "studio_input.json"
    )


def _print_errors(result: dict) -> None:
    for error in result.get("validation_errors", []):
        print(f"error={error.code}:{error.message}", file=sys.stderr)


def _serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=()).with_msgpack_allowlist(
        [
            CreativeIdea,
            InsightType,
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

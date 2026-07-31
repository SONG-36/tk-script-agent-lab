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
from tk_script_agent_lab.langgraph_app.graph import build_graph
from tk_script_agent_lab.knowledge import CreativeKnowledgeItem, KnowledgeSelectionRecord
from tk_script_agent_lab.providers import ModelCallRecord
from tk_script_agent_lab.workflow import WorkflowInput, WorkflowStatus, WorkflowStepRecord


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL")
    if not api_key:
        print("OPENAI_API_KEY is required for the Phase 2A OpenAI demo.", file=sys.stderr)
        return 1
    if not model:
        print("OPENAI_MODEL is required for the Phase 2A OpenAI demo.", file=sys.stderr)
        return 1

    studio_input_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "golden_cases"
        / "car_vacuum_v1"
        / "studio_input.json"
    )
    graph_input = json.loads(studio_input_path.read_text(encoding="utf-8"))
    graph = build_graph(checkpointer=InMemorySaver(serde=_serializer()))
    result = graph.invoke(
        graph_input,
        config={"configurable": {"thread_id": "phase-2a-openai-demo"}},
        context={
            "creative_provider": "openai",
            "creative_model": model,
        },
    )
    if result.get("validation_errors"):
        for error in result["validation_errors"]:
            print(f"error={error.code}:{error.message}", file=sys.stderr)
        return 1

    interrupts = result.get("__interrupt__", ())
    if not interrupts:
        print("Expected IDEA_SELECTION_REQUIRED interrupt but graph did not pause.", file=sys.stderr)
        return 1

    payload = interrupts[0].value
    print(f"model={model}")
    print(f"status={result.get('status')}")
    print(f"validation_errors={[]}")
    print(f"script_draft_is_null={result.get('script_draft') is None}")
    print(f"selected_idea_id_is_null={result.get('selected_idea_id') is None}")
    print(f"idea_review_is_null={result.get('idea_review') is None}")
    print(f"interrupt_type={payload['type']}")
    print(f"interrupt_run_id={payload['run_id']}")
    print(f"allowed_decisions={payload['allowed_decisions']}")
    for record in result.get("model_call_records", []):
        record_payload = record.model_dump(mode="json")
        record_payload["response_id_present"] = record.response_id is not None
        record_payload.pop("response_id", None)
        print(f"model_call_record={record_payload}")
    print(f"prompt_version={result['model_call_records'][0].prompt_version}")
    print(f"creative_idea_count={len(payload['creative_ideas'])}")
    print(f"step_names={[record.step_name for record in result.get('step_records', [])]}")
    print(f"step_executors={[record.executor for record in result.get('step_records', [])]}")
    for idea in result["creative_ideas"]:
        print(f"creative_idea_id={idea.creative_idea_id}")
        print(f"title={idea.title}")
        print(f"hook={idea.hook}")
        print(f"concept_summary={idea.concept_summary}")
        print(f"target_audience={idea.target_audience}")
        print(f"risk_notes={idea.risk_notes}")
        for usage in idea.source_usages:
            print(
                "source_usage="
                f"{usage.source_type}:{usage.source_id}:{usage.usage_purpose}"
            )
    return 0


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

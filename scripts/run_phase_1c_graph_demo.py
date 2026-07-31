from argparse import ArgumentParser
from pathlib import Path
import json

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
from tk_script_agent_lab.knowledge import CreativeKnowledgeItem, KnowledgeSelectionRecord
from tk_script_agent_lab.langgraph_app.graph import build_graph
from tk_script_agent_lab.workflow import WorkflowInput, WorkflowStatus, WorkflowStepRecord


def main() -> None:
    parser = ArgumentParser(description="Run the Phase 1C LangGraph demo.")
    parser.add_argument("--selected-idea-id")
    parser.add_argument("--reviewer")
    args = parser.parse_args()

    studio_input_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "golden_cases"
        / "car_vacuum_v1"
        / "studio_input.json"
    )
    serde = JsonPlusSerializer(allowed_msgpack_modules=()).with_msgpack_allowlist(
        [
            CreativeIdea,
            CreativeKnowledgeItem,
            InsightType,
            KnowledgeSelectionRecord,
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
    graph = build_graph(checkpointer=InMemorySaver(serde=serde))
    config = {"configurable": {"thread_id": "phase-1c-demo-thread"}}
    graph_input = json.loads(studio_input_path.read_text(encoding="utf-8"))

    first = graph.invoke(graph_input, config=config)
    interrupts = first.get("__interrupt__", ())
    if interrupts:
        payload = interrupts[0].value
        print(f"interrupt_type={payload['type']}")
        for idea in payload["creative_ideas"]:
            print(f"creative_idea_id={idea['creative_idea_id']}")
            print(f"title={idea['title']}")
            print(f"hook={idea['hook']}")
    else:
        print(f"status={first.get('status')}")

    if not args.selected_idea_id:
        return
    if not args.reviewer:
        raise SystemExit("--reviewer is required when --selected-idea-id is provided")

    resumed = graph.invoke(
        Command(
            resume={
                "target_id": args.selected_idea_id,
                "decision": "APPROVED",
                "reviewer": args.reviewer,
                "comment": None,
            }
        ),
        config=config,
    )
    print(f"status={resumed['status']}")
    script = resumed.get("script_draft")
    if script:
        script_payload = (
            script.model_dump(mode="json") if hasattr(script, "model_dump") else script
        )
        print(f"script_id={script_payload['script_id']}")
        print(f"creative_idea_id={script_payload['creative_idea_id']}")
        print(f"title={script_payload['title']}")


if __name__ == "__main__":
    main()

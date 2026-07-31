from pathlib import Path
import json

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
from tk_script_agent_lab.knowledge import (
    CreativeKnowledgeItem,
    KnowledgeSelectionRecord,
    RetrievedKnowledge,
)
from tk_script_agent_lab.providers import ModelCallRecord
from tk_script_agent_lab.workflow import WorkflowInput, WorkflowStatus, WorkflowStepRecord


def studio_input_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "golden_cases"
        / "car_vacuum_v1"
        / "studio_input.json"
    )


def load_studio_input() -> dict:
    return json.loads(studio_input_path().read_text(encoding="utf-8"))


def make_checkpointer() -> InMemorySaver:
    serde = JsonPlusSerializer(allowed_msgpack_modules=()).with_msgpack_allowlist(
        [
            CreativeIdea,
            CreativeKnowledgeItem,
            InsightType,
            KnowledgeSelectionRecord,
            RetrievedKnowledge,
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
    return InMemorySaver(serde=serde)


def make_graph():
    return build_graph(checkpointer=make_checkpointer())


def thread_config(thread_id: str = "phase-1c-test-thread") -> dict:
    return {"configurable": {"thread_id": thread_id}}


def approved_resume(target_id: str) -> dict:
    return {
        "target_id": target_id,
        "decision": "APPROVED",
        "reviewer": "test-reviewer",
        "comment": None,
    }

from langgraph.types import Command

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.langgraph_app import nodes
from tk_script_agent_lab.knowledge import (
    RetrievedKnowledge,
    RetrievalRequest,
    RetrievalResult,
    RetrievalTrace,
)
from tk_script_agent_lab.workflow import WorkflowStatus

from phase_1c_helpers import approved_resume, load_studio_input, make_graph, thread_config
from test_phase_3a_graph_node import Runtime, state_after_manual_insights


class StubKnowledgeRetriever:
    calls = 0

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        type(self).calls += 1
        return RetrievalResult(
            items=[
                RetrievedKnowledge(
                    knowledge_id="ck_stub",
                    title="Stub knowledge",
                    content="Use a simple visible problem.",
                    kind="hook_pattern",
                    provenance_type="internal_working_rule",
                    evidence_status="hypothesis",
                    metadata={"status": "active"},
                    score=None,
                )
            ],
            trace=RetrievalTrace(
                retriever_type="static",
                retriever_version="stub_retriever_v1",
                request_id="ks_stub",
                candidate_ids=["ck_stub"],
                selected_ids=["ck_stub"],
                excluded=[],
                filters_applied={
                    "pack_id": "stub_pack",
                    "pack_version": "test",
                },
            ),
            errors=[],
        )


class FailingKnowledgeRetriever:
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        return RetrievalResult(
            items=[],
            trace=RetrievalTrace(
                retriever_type="static",
                retriever_version="stub_retriever_v1",
                request_id="ks_failed",
                candidate_ids=[],
                selected_ids=[],
                excluded=[],
                filters_applied={},
            ),
            errors=[
                ValidationError(
                    code="KNOWLEDGE_PACK_NOT_FOUND",
                    message="missing",
                    object_type="StaticKnowledgeRetriever",
                    object_id="missing",
                    field="pack_id",
                    related_id=None,
                )
            ],
        )


def test_select_creative_knowledge_can_use_stub_retriever(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    StubKnowledgeRetriever.calls = 0
    monkeypatch.setattr(nodes, "_knowledge_retriever", lambda configuration: StubKnowledgeRetriever())
    state = state_after_manual_insights()

    result = nodes.select_creative_knowledge(
        state,
        Runtime(
            {
                "knowledge_mode": "static",
                "creative_knowledge_pack": "ignored_by_stub",
            }
        ),
    )

    assert StubKnowledgeRetriever.calls == 1
    assert result["creative_knowledge_items"][0].knowledge_id == "ck_stub"
    assert result["knowledge_selection_records"][0].selected_ids == ["ck_stub"]


def test_retriever_failure_does_not_call_creative_provider(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(nodes, "_knowledge_retriever", lambda configuration: FailingKnowledgeRetriever())
    monkeypatch.setattr(
        nodes,
        "OpenAICreativeProvider",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("creative provider should not run")),
    )
    graph = make_graph()

    result = graph.invoke(
        load_studio_input(),
        config=thread_config("phase-3b-retriever-failure"),
        context={
            "knowledge_mode": "static",
            "creative_knowledge_pack": "missing",
            "creative_provider": "openai",
            "creative_model": "stub-model",
        },
    )

    assert result["status"] == WorkflowStatus.FAILED
    assert "__interrupt__" not in result
    assert [error.code for error in result["validation_errors"]] == [
        "KNOWLEDGE_PACK_NOT_FOUND"
    ]


def test_fake_fake_full_graph_still_completes_with_knowledge_off() -> None:
    graph = make_graph()
    config = thread_config("phase-3b-fake-fake")
    first = graph.invoke(load_studio_input(), config=config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]
    completed = graph.invoke(Command(resume=approved_resume(selected_id)), config=config)

    assert completed["status"] == WorkflowStatus.COMPLETED
    assert completed["knowledge_selection_records"][0].mode == "off"

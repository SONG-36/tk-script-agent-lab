import copy

from tk_script_agent_lab.configuration import GraphConfiguration
from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.contracts import RetrievalResult, RetrievalTrace
from tk_script_agent_lab.knowledge.creative_pack_documents import creative_pack_to_documents
from tk_script_agent_lab.knowledge.creative_retrieval_query import build_creative_retrieval_request
from tk_script_agent_lab.knowledge.creative_vector_runtime import (
    CreativeVectorRuntimeBuild,
    get_or_build_creative_vector_runtime,
    reset_creative_vector_runtime_cache,
)
from tk_script_agent_lab.knowledge.embedding_contracts import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTrace,
    EmbeddingVector,
    stable_embedding_request_id,
)
from tk_script_agent_lab.knowledge.loader import load_creative_knowledge_pack
from tk_script_agent_lab.knowledge.vector_store_contracts import VectorBuildTrace
from tk_script_agent_lab.langgraph_app import nodes
from tk_script_agent_lab.prompts.creative_idea_v2 import build_creative_idea_context
from tk_script_agent_lab.providers import CreativeGenerationRequest
from tk_script_agent_lab.workflow import WorkflowStatus

from phase_1c_helpers import load_studio_input, make_graph, thread_config
from test_phase_3a_graph_node import Runtime, state_after_manual_insights


class CountingEmbeddingProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.call_count = 0
        self.requests = []
        self.fail = fail

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.call_count += 1
        self.requests.append(request)
        if self.fail:
            return EmbeddingResult(
                vectors=[],
                trace=_trace(request, [], "FAILED", "EMBEDDING_CALL_FAILED"),
                errors=[
                    ValidationError(
                        code="EMBEDDING_CALL_FAILED",
                        message="stub failure",
                        object_type="CountingEmbeddingProvider",
                        object_id=None,
                        field=None,
                        related_id=None,
                    )
                ],
            )
        vectors = [
            EmbeddingVector(item_id=item.item_id, values=_values(item.text), dimensions=3)
            for item in request.items
        ]
        return EmbeddingResult(vectors=vectors, trace=_trace(request, vectors, "SUCCESS", None), errors=[])


def test_creative_pack_to_documents_maps_active_items_without_mutating_pack() -> None:
    pack = load_creative_knowledge_pack("tiktok_car_cleaning_v1")
    before = pack.model_dump(mode="json")
    documents = creative_pack_to_documents(pack)

    assert len(documents) == 6
    assert pack.model_dump(mode="json") == before
    assert documents[0].source.source_type == "internal_file"
    assert documents[0].source.source_reference.startswith("knowledge/creative/tiktok_car_cleaning_v1.yaml#")
    assert documents[0].provenance_type == "internal_working_rule"
    assert documents[0].evidence_status == "hypothesis"
    assert documents[0].metadata["pack_id"] == "tiktok_car_cleaning_v1"
    assert documents[0].metadata["knowledge_id"].startswith("ck_")
    assert documents[0].product_categories
    assert not hasattr(documents[0], "fact_id")
    assert [item.document_id for item in documents] == [item.document_id for item in creative_pack_to_documents(pack)]


def test_creative_pack_to_documents_excludes_draft_and_disabled_items() -> None:
    pack = load_creative_knowledge_pack("tiktok_car_cleaning_v1")
    draft = pack.items[0].model_copy(update={"knowledge_id": "ck_draft", "status": "draft"})
    disabled = pack.items[1].model_copy(update={"knowledge_id": "ck_disabled", "status": "disabled"})
    modified = pack.model_copy(update={"items": [draft, disabled, *pack.items[2:]]})

    documents = creative_pack_to_documents(modified)

    assert "ck_draft" not in [item.metadata["knowledge_id"] for item in documents]
    assert "ck_disabled" not in [item.metadata["knowledge_id"] for item in documents]


def test_creative_retrieval_query_is_stable_and_omits_unverified_fact_values() -> None:
    state = state_after_manual_insights()
    workflow_input = state["workflow_input"]
    config = GraphConfiguration(
        knowledge_mode="vector",
        creative_knowledge_pack="tiktok_car_cleaning_v1",
        creative_embedding_model="embedding-test",
    )

    first = build_creative_retrieval_request(workflow_input, state["reference_insights"], config)
    second = build_creative_retrieval_request(workflow_input, state["reference_insights"], config)

    assert first == second
    assert "car vacuum cleaner" in first.query
    assert "Schema validation fixture" in first.query
    assert "Car owners" in first.query
    assert "Car interior cleanup context" in first.query
    assert "Open with a visible small car-interior mess" in first.query
    assert "power_watts" not in first.query
    assert "battery_runtime" not in first.query
    assert "reviewer" not in first.query.casefold()
    assert "api_key" not in first.query.casefold()
    assert first.filters == {"query_version": "creative_retrieval_query_v1"}


def test_creative_vector_runtime_builds_once_reuses_and_retrieves() -> None:
    reset_creative_vector_runtime_cache()
    provider = CountingEmbeddingProvider()
    config = GraphConfiguration(
        knowledge_mode="vector",
        creative_knowledge_pack="tiktok_car_cleaning_v1",
        creative_embedding_model="embedding-test",
    )
    state = state_after_manual_insights()
    request = build_creative_retrieval_request(state["workflow_input"], state["reference_insights"], config)

    first = get_or_build_creative_vector_runtime(
        pack_id="tiktok_car_cleaning_v1",
        embedding_model="embedding-test",
        retriever_version="vector_retriever_v1",
        embedding_provider=provider,
    )
    run = first.runtime.retrieve(request)
    second = get_or_build_creative_vector_runtime(
        pack_id="tiktok_car_cleaning_v1",
        embedding_model="embedding-test",
        retriever_version="vector_retriever_v1",
        embedding_provider=CountingEmbeddingProvider(),
    )
    second_run = second.runtime.retrieve(request)

    assert first.runtime_built is True
    assert first.runtime_reused is False
    assert second.runtime_built is False
    assert second.runtime_reused is True
    assert provider.call_count == 3
    assert first.runtime.document_embedding_calls == 1
    assert run.query_embedding_calls == 1
    assert second_run.query_embedding_calls == 1
    assert run.result.trace.retriever_type == "vector"
    assert run.result.trace.filters_applied["query_version"] == "creative_retrieval_query_v1"
    assert run.result.items


def test_creative_vector_runtime_failure_is_not_cached() -> None:
    reset_creative_vector_runtime_cache()
    failed = get_or_build_creative_vector_runtime(
        pack_id="tiktok_car_cleaning_v1",
        embedding_model="embedding-test",
        retriever_version="vector_retriever_v1",
        embedding_provider=CountingEmbeddingProvider(fail=True),
    )
    retry = get_or_build_creative_vector_runtime(
        pack_id="tiktok_car_cleaning_v1",
        embedding_model="embedding-test",
        retriever_version="vector_retriever_v1",
        embedding_provider=CountingEmbeddingProvider(),
    )

    assert [error.code for error in failed.errors] == ["EMBEDDING_CALL_FAILED"]
    assert failed.runtime is None
    assert retry.runtime_built is True
    assert retry.runtime is not None


def test_select_creative_knowledge_vector_mode_writes_trace_and_guidance(monkeypatch) -> None:
    reset_creative_vector_runtime_cache()
    monkeypatch.setattr(nodes, "OpenAICreativeProvider", _forbidden_provider)
    monkeypatch.setattr(
        "tk_script_agent_lab.knowledge.creative_vector_runtime.OpenAIEmbeddingProvider",
        lambda: CountingEmbeddingProvider(),
    )
    result = nodes.select_creative_knowledge(
        state_after_manual_insights(),
        Runtime(
            {
                "knowledge_mode": "vector",
                "creative_knowledge_pack": "tiktok_car_cleaning_v1",
                "creative_embedding_model": "embedding-graph-test",
                "creative_prompt_version": "creative_idea_v2",
            }
        ),
    )

    assert result["validation_errors"] == []
    assert result["knowledge_selection_records"][0].mode == "vector"
    assert result["knowledge_retrieval_records"][0].retriever_type == "vector"
    assert result["embedding_records"][0].status == "SUCCESS"
    assert result["vector_build_records"][0].status == "SUCCESS"
    assert result["creative_knowledge_items"]
    assert "api_key" not in str(result).casefold()


def test_graph_vector_fake_reaches_interrupt_without_script_or_knowledge_sources(monkeypatch) -> None:
    reset_creative_vector_runtime_cache()
    monkeypatch.setattr(
        "tk_script_agent_lab.knowledge.creative_vector_runtime.OpenAIEmbeddingProvider",
        lambda: CountingEmbeddingProvider(),
    )
    result = make_graph().invoke(
        load_studio_input(),
        config=thread_config("phase-4d-vector-fake"),
        context={
            "knowledge_mode": "vector",
            "creative_knowledge_pack": "tiktok_car_cleaning_v1",
            "creative_embedding_model": "embedding-graph-test",
            "creative_prompt_version": "creative_idea_v2",
        },
    )
    knowledge_ids = {item.knowledge_id for item in result["creative_knowledge_items"]}
    source_ids = {
        usage.source_id
        for idea in result["creative_ideas"]
        for usage in idea.source_usages
    }

    assert result["__interrupt__"][0].value["type"] == "IDEA_SELECTION_REQUIRED"
    assert result.get("script_draft") is None
    assert result["knowledge_selection_records"][0].mode == "vector"
    assert not (knowledge_ids & source_ids)


def test_vector_retrieval_failure_stops_before_creative_provider(monkeypatch) -> None:
    monkeypatch.setattr(nodes, "get_or_build_creative_vector_runtime", lambda **kwargs: _failed_runtime_build())
    monkeypatch.setattr(nodes, "OpenAICreativeProvider", _forbidden_provider)

    result = make_graph().invoke(
        load_studio_input(),
        config=thread_config("phase-4d-vector-failure"),
        context={
            "knowledge_mode": "vector",
            "creative_knowledge_pack": "tiktok_car_cleaning_v1",
            "creative_embedding_model": "embedding-graph-test",
            "creative_provider": "openai",
            "creative_model": "model-test",
        },
    )

    assert result["status"] == WorkflowStatus.FAILED
    assert "__interrupt__" not in result
    assert [error.code for error in result["validation_errors"]] == ["VECTOR_BUILD_FAILED"]
    assert result.get("model_call_records", []) == []


def test_vector_no_match_allows_creative_provider(monkeypatch) -> None:
    monkeypatch.setattr(nodes, "get_or_build_creative_vector_runtime", lambda **kwargs: _empty_runtime_build())

    result = make_graph().invoke(
        load_studio_input(),
        config=thread_config("phase-4d-vector-no-match"),
        context={
            "knowledge_mode": "vector",
            "creative_knowledge_pack": "tiktok_car_cleaning_v1",
            "creative_embedding_model": "embedding-graph-test",
        },
    )

    assert result["__interrupt__"][0].value["type"] == "IDEA_SELECTION_REQUIRED"
    assert result["creative_knowledge_items"] == []
    assert result["validation_errors"] == []


def test_vector_guidance_prompt_stays_out_of_business_evidence(monkeypatch) -> None:
    reset_creative_vector_runtime_cache()
    monkeypatch.setattr(
        "tk_script_agent_lab.knowledge.creative_vector_runtime.OpenAIEmbeddingProvider",
        lambda: CountingEmbeddingProvider(),
    )
    selected = nodes.select_creative_knowledge(
        state_after_manual_insights(),
        Runtime(
            {
                "knowledge_mode": "vector",
                "creative_knowledge_pack": "tiktok_car_cleaning_v1",
                "creative_embedding_model": "embedding-prompt-test",
            }
        ),
    )
    state = state_after_manual_insights()
    request = CreativeGenerationRequest(
        product_profile=state["workflow_input"].product_profile,
        product_facts=state["workflow_input"].product_facts,
        selling_points=state["workflow_input"].selling_points,
        reference_insights=state["reference_insights"],
        creative_knowledge_items=selected["creative_knowledge_items"],
        idea_count=state["workflow_input"].idea_count,
    )
    context = build_creative_idea_context(request)
    allowed = context["business_evidence"]["constraints"]["allowed_source_ids"]
    guidance = context["creative_guidance"]

    assert guidance
    assert guidance[0]["score"] is not None
    assert guidance[0]["source_reference"].startswith("knowledge/creative/")
    assert guidance[0]["metadata"]["pack_id"] == "tiktok_car_cleaning_v1"
    assert all(item["knowledge_id"] not in allowed["product_fact"] for item in guidance)
    assert all(item["knowledge_id"] not in allowed["selling_point"] for item in guidance)
    assert all(item["knowledge_id"] not in allowed["reference_insight"] for item in guidance)


def _trace(request: EmbeddingRequest, vectors: list[EmbeddingVector], status: str, error_code: str | None) -> EmbeddingTrace:
    return EmbeddingTrace(
        request_id=stable_embedding_request_id(request),
        provider="openai",
        provider_version=request.provider_version,
        model=request.model,
        input_ids=[item.item_id for item in request.items],
        output_ids=[vector.item_id for vector in vectors],
        dimensions=vectors[0].dimensions if vectors else None,
        status=status,  # type: ignore[arg-type]
        error_code=error_code,
    )


def _values(text: str) -> list[float]:
    normalized = text.casefold()
    return [
        1.0 if "micro-mess" in normalized or "small car-interior mess" in normalized else 0.1,
        1.0 if "claim" in normalized or "unverified" in normalized else 0.1,
        1.0 if "shootable" in normalized or "ordinary car-interior" in normalized else 0.1,
    ]


def _failed_runtime_build() -> CreativeVectorRuntimeBuild:
    return CreativeVectorRuntimeBuild(
        runtime=None,
        errors=[
            ValidationError(
                code="VECTOR_BUILD_FAILED",
                message="stub failure",
                object_type="CreativeVectorRuntime",
                object_id=None,
                field=None,
                related_id=None,
            )
        ],
        runtime_built=False,
        runtime_reused=False,
    )


class _EmptyRuntime:
    pack_id = "tiktok_car_cleaning_v1"
    pack_version = "1.0"
    document_embedding_trace = EmbeddingTrace(
        request_id="er_empty_doc",
        provider="openai",
        provider_version="openai_embedding_v1",
        model="embedding-test",
        input_ids=[],
        output_ids=[],
        dimensions=None,
        status="SUCCESS",
        error_code=None,
    )
    vector_build_trace = VectorBuildTrace(
        build_id="vb_empty",
        store_type="qdrant_local",
        store_version="qdrant_local_v1",
        collection_name="cv_empty",
        input_ids=[],
        indexed_ids=[],
        rejected_ids=[],
        dimensions=None,
        status="SUCCESS",
    )
    ingestion_trace = type("Trace", (), {"document_count": 0, "chunk_count": 0})()
    document_embedding_calls = 0

    def retrieve(self, request):
        return type(
            "Run",
            (),
            {
                "result": RetrievalResult(
                    items=[],
                    trace=RetrievalTrace(
                        retriever_type="vector",
                        retriever_version="vector_retriever_v1",
                        request_id="rr_no_match",
                        candidate_ids=[],
                        selected_ids=[],
                        excluded=[],
                        filters_applied={
                            "query": request.query,
                            "pack_id": "tiktok_car_cleaning_v1",
                            "pack_version": "1.0",
                        },
                    ),
                    errors=[],
                ),
                "query_embedding_trace": None,
                "query_embedding_calls": 0,
            },
        )()


def _empty_runtime_build() -> CreativeVectorRuntimeBuild:
    return CreativeVectorRuntimeBuild(
        runtime=_EmptyRuntime(),
        errors=[],
        runtime_built=False,
        runtime_reused=True,
    )


def _forbidden_provider(*args, **kwargs):  # noqa: ANN002, ANN003
    raise AssertionError("creative provider should not run")

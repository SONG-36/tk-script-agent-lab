from tk_script_agent_lab.knowledge.contracts import RetrievalRequest
from tk_script_agent_lab.knowledge.embedding_contracts import EmbeddingResult, EmbeddingTrace
from tk_script_agent_lab.knowledge.qdrant_vector_store import QdrantLocalVectorStore
from tk_script_agent_lab.knowledge.retrieval_eval import RetrievalEvalCase, RetrievalEvaluator
from tk_script_agent_lab.knowledge.vector_retriever import VectorKnowledgeRetriever
from tk_script_agent_lab.knowledge.vector_store_contracts import VectorBuildRequest, VectorIndexItem
from tests.unit_tests.test_phase_4c_vector_store import build_request, search_request, vector


class StubEmbeddingProvider:
    def __init__(self, values=None, errors=None) -> None:
        self.values = values or [1.0, 0.0]
        self.errors = errors or []
        self.calls = 0

    def embed(self, request):
        self.calls += 1
        return EmbeddingResult(
            vectors=[] if self.errors else [vector(request.items[0].item_id, self.values)],
            trace=EmbeddingTrace(
                request_id="er_stub",
                provider="openai",
                provider_version=request.provider_version,
                model=request.model,
                input_ids=[item.item_id for item in request.items],
                output_ids=[] if self.errors else [request.items[0].item_id],
                dimensions=None if self.errors else len(self.values),
                status="FAILED" if self.errors else "SUCCESS",
                error_code=self.errors[0].code if self.errors else None,
            ),
            errors=self.errors,
        )


def request(**overrides) -> RetrievalRequest:
    payload = search_request().retrieval_request.model_dump(mode="python")
    payload.update(overrides)
    return RetrievalRequest.model_validate(payload)


def test_vector_retriever_maps_result_and_citation_without_reembedding_documents() -> None:
    store = QdrantLocalVectorStore()
    store.build(build_request())
    provider = StubEmbeddingProvider()
    retriever = VectorKnowledgeRetriever(
        embedding_provider=provider,
        vector_store=store,
        embedding_model="embedding-test",
        collection_name="test_collection",
    )
    result = retriever.retrieve(request())
    item = result.items[0]

    assert provider.calls == 1
    assert result.trace.retriever_type == "vector"
    assert result.trace.filters_applied["query_match_mode"] == "vector_similarity_after_metadata_filter"
    assert result.trace.filters_applied["ranking_version"] == "qdrant_cosine_v1"
    assert "exact_rank_v1" not in result.trace.filters_applied.values()
    assert item.knowledge_id == "kc_a"
    assert item.score is not None
    assert item.provenance_type == "internal_working_rule"
    assert item.evidence_status == "hypothesis"
    assert store.get_chunk(item.knowledge_id) is not None
    assert "source_usages" not in item.model_dump(mode="json")


def test_vector_retriever_empty_no_match_invalid_filter_and_eval() -> None:
    empty = VectorKnowledgeRetriever(
        embedding_provider=StubEmbeddingProvider(),
        vector_store=QdrantLocalVectorStore(),
        embedding_model="embedding-test",
        collection_name="test_collection",
    ).retrieve(request())
    assert [error.code for error in empty.errors] == ["VECTOR_STORE_EMPTY"]

    store = QdrantLocalVectorStore()
    store.build(build_request())
    retriever = VectorKnowledgeRetriever(
        embedding_provider=StubEmbeddingProvider(),
        vector_store=store,
        embedding_model="embedding-test",
        collection_name="test_collection",
    )
    no_match = retriever.retrieve(request(target_market="JP"))
    invalid = retriever.retrieve(request(filters={"effective_on": "bad"}))
    assert no_match.errors == []
    assert no_match.items == []
    assert [error.code for error in invalid.errors] == ["RETRIEVAL_FILTER_INVALID"]

    eval_result = RetrievalEvaluator().evaluate_case(
        RetrievalEvalCase(
            case_id="vector_hit",
            request=request(),
            expected_ids=["kc_a"],
            forbidden_ids=[],
            expected_top_id="kc_a",
        ),
        retriever.retrieve(request()),
    )
    assert eval_result.passed

from datetime import date
import json

from tk_script_agent_lab.knowledge.contracts import RetrievalRequest
from tk_script_agent_lab.knowledge.exact_retriever import ExactMetadataKnowledgeRetriever
from tk_script_agent_lab.knowledge.index_contracts import IndexBuildRequest
from tk_script_agent_lab.knowledge.in_memory_index import InMemoryKnowledgeIndex

from tests.unit_tests.phase_4b_helpers import chunk


def built_index(chunks):
    index = InMemoryKnowledgeIndex()
    index.build(IndexBuildRequest(chunks=chunks))
    return index


def request(**overrides) -> RetrievalRequest:
    payload = {
        "stage": "creative",
        "target_market": "US",
        "product_category": "car vacuum cleaner",
        "query": "cup holder crumbs",
        "limit": 3,
        "filters": {"effective_on": "2026-07-31"},
    }
    payload.update(overrides)
    return RetrievalRequest.model_validate(payload)


def retrieve(chunks, **request_overrides):
    return ExactMetadataKnowledgeRetriever(built_index(chunks)).retrieve(request(**request_overrides))


def test_empty_index_is_error_but_no_match_is_valid() -> None:
    empty = ExactMetadataKnowledgeRetriever(InMemoryKnowledgeIndex()).retrieve(request())
    no_match = retrieve([chunk()], query="missing phrase")

    assert [error.code for error in empty.errors] == ["RETRIEVAL_INDEX_EMPTY"]
    assert no_match.errors == []
    assert no_match.items == []
    assert no_match.trace.excluded[0].reason == "query_no_match"


def test_metadata_filters_stage_market_category_wildcard_and_custom_metadata() -> None:
    chunks = [
        chunk("kc_stage", task_stages=["script"]),
        chunk("kc_market", target_markets=["JP"]),
        chunk("kc_category", product_categories=["hair care"]),
        chunk("kc_wildcard", target_markets=["*"], product_categories=["*"]),
        chunk("kc_topic", metadata={"kind": "creative_note", "topic": "other"}),
    ]
    result = retrieve(chunks, filters={"effective_on": "2026-07-31", "topic": "car_cleanup"})
    reasons = {item.knowledge_id: item.reason for item in result.trace.excluded}

    assert result.trace.selected_ids == ["kc_wildcard"]
    assert reasons["kc_stage"] == "stage_mismatch"
    assert reasons["kc_market"] == "market_mismatch"
    assert reasons["kc_category"] == "category_mismatch"
    assert reasons["kc_topic"] == "metadata_mismatch:topic"


def test_effective_date_filters_and_invalid_date_error() -> None:
    result = retrieve(
        [
            chunk("kc_future", effective_from=date(2027, 1, 1)),
            chunk("kc_expired", effective_to=date(2025, 12, 31)),
            chunk("kc_current"),
        ]
    )
    invalid = retrieve([chunk()], filters={"effective_on": "2026-99-99"})
    reasons = {item.knowledge_id: item.reason for item in result.trace.excluded}

    assert result.trace.selected_ids == ["kc_current"]
    assert reasons["kc_future"] == "not_effective"
    assert reasons["kc_expired"] == "not_effective"
    assert [error.code for error in invalid.errors] == ["RETRIEVAL_FILTER_INVALID"]


def test_missing_effective_on_skips_date_filter() -> None:
    result = retrieve([chunk("kc_expired", effective_to=date(2025, 12, 31))], filters={})

    assert result.trace.selected_ids == ["kc_expired"]
    assert result.trace.filters_applied["effective_on"] == ""


def test_exact_retriever_trace_keeps_exact_ranking_labels() -> None:
    result = retrieve([chunk()])

    assert result.trace.filters_applied["query_match_mode"] == "exact_all_terms_or_phrase"
    assert result.trace.filters_applied["ranking_version"] == "exact_rank_v1"


def test_exact_query_phrase_terms_casefold_nfkc_whitespace_ranking_limit() -> None:
    chunks = [
        chunk("kc_title", title="ＣＵＰ holder crumbs", content="plain content", document_id="doc_a"),
        chunk("kc_content", title="Plain", content="cup   holder crumbs in content", document_id="doc_b"),
        chunk("kc_terms", title="Cup detail", content="holder crumbs split terms", document_id="doc_c"),
        chunk("kc_missing", title="Cup detail", content="holder only", document_id="doc_d"),
    ]
    result = retrieve(chunks, query="cup holder crumbs", limit=2)
    reasons = {item.knowledge_id: item.reason for item in result.trace.excluded}
    scores = {item.knowledge_id: item.score for item in result.items}

    assert result.trace.selected_ids == ["kc_title", "kc_content"]
    assert scores["kc_title"] == 130.0
    assert scores["kc_content"] == 59.0
    assert reasons["kc_terms"] == "over_limit"
    assert reasons["kc_missing"] == "query_no_match"


def test_tie_break_mapping_trace_and_no_business_evidence() -> None:
    result = retrieve(
        [
            chunk("kc_b", document_id="doc_b", sequence=1),
            chunk("kc_a", document_id="doc_a", sequence=1),
        ]
    )
    item = result.items[0]
    payload = result.trace.model_dump(mode="json")

    assert result.trace.selected_ids == ["kc_a", "kc_b"]
    assert item.knowledge_id == "kc_a"
    assert item.metadata["document_id"] == "doc_a"
    assert item.metadata["sequence"] == "1"
    assert item.provenance_type == "internal_working_rule"
    assert item.evidence_status == "hypothesis"
    assert item.source_reference == "synthetic.kc_a"
    assert item.score is not None
    assert built_index([chunk("kc_a", document_id="doc_a")]).get(item.knowledge_id)
    assert "source_usages" not in item.model_dump(mode="json")
    assert "embedding" not in json.dumps(payload).casefold()
    assert "api_key" not in json.dumps(payload).casefold()

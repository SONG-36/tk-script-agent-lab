import json

import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge import (
    RetrievedKnowledge,
    RetrievalExclusion,
    RetrievalRequest,
    RetrievalResult,
    RetrievalTrace,
)
from tk_script_agent_lab.knowledge.contracts import stable_retrieval_request_id


def request() -> RetrievalRequest:
    return RetrievalRequest(
        stage="creative",
        target_market="Schema validation fixture",
        product_category="car vacuum cleaner",
        query="Creative guidance for car vacuum.",
        limit=3,
        filters={"product_id": "prod_car_vacuum_schema_fixture"},
    )


def retrieved() -> RetrievedKnowledge:
    return RetrievedKnowledge(
        knowledge_id="ck_test",
        title="Test knowledge",
        content="Use a visible mess hook.",
        kind="hook_pattern",
        provenance_type="internal_working_rule",
        evidence_status="hypothesis",
        source_reference=None,
        metadata={"status": "active"},
        score=None,
    )


def trace() -> RetrievalTrace:
    req = request()
    return RetrievalTrace(
        retriever_type="static",
        retriever_version="static_selector_v1",
        request_id=stable_retrieval_request_id(req),
        candidate_ids=["ck_test"],
        selected_ids=["ck_test"],
        excluded=[],
        filters_applied=req.filters,
    )


def test_retrieval_request_accepts_valid_input() -> None:
    req = request()

    assert req.stage == "creative"
    assert req.limit == 3
    assert req.filters["product_id"] == "prod_car_vacuum_schema_fixture"


def test_retrieval_request_rejects_empty_query_limit_and_extra_fields() -> None:
    with pytest.raises(PydanticValidationError):
        request().model_copy(update={"query": ""}).model_validate(
            {**request().model_dump(mode="json"), "query": ""}
        )
    with pytest.raises(PydanticValidationError):
        RetrievalRequest.model_validate({**request().model_dump(mode="json"), "limit": 0})
    with pytest.raises(PydanticValidationError):
        RetrievalRequest.model_validate({**request().model_dump(mode="json"), "api_key": "x"})


def test_retrieval_request_rejects_secret_like_filters() -> None:
    with pytest.raises(PydanticValidationError):
        RetrievalRequest.model_validate(
            {
                **request().model_dump(mode="json"),
                "filters": {"OPENAI_API_KEY": "secret"},
            }
        )


def test_retrieved_knowledge_requires_identity_and_content() -> None:
    item = retrieved()

    assert item.knowledge_id == "ck_test"
    assert item.content
    assert item.score is None

    with pytest.raises(PydanticValidationError):
        RetrievedKnowledge.model_validate({**item.model_dump(mode="json"), "content": ""})


def test_retrieval_result_is_json_serializable_and_keeps_errors() -> None:
    result = RetrievalResult(
        items=[retrieved()],
        trace=trace(),
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
    payload = result.model_dump(mode="json")

    assert json.loads(json.dumps(payload))["items"][0]["knowledge_id"] == "ck_test"
    assert payload["errors"][0]["code"] == "KNOWLEDGE_PACK_NOT_FOUND"


def test_retrieval_trace_id_is_stable_and_has_no_vectors() -> None:
    first = stable_retrieval_request_id(request())
    second = stable_retrieval_request_id(request())
    payload = trace().model_dump(mode="json")

    assert first == second
    assert "embedding" not in json.dumps(payload).casefold()
    assert RetrievalExclusion(knowledge_id="ck_excluded", reason="over_limit")


def test_knowledge_contract_does_not_make_business_evidence() -> None:
    payload = retrieved().model_dump(mode="json")

    assert "source_usages" not in payload
    assert payload["knowledge_id"].startswith("ck_")

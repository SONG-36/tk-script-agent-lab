import json

import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.contracts import RetrievalResult, RetrievalTrace
from tk_script_agent_lab.knowledge.retrieval_eval import RetrievalEvalCase, RetrievalEvaluator

from tests.unit_tests.test_phase_4b_exact_retriever import request, retrieve
from tests.unit_tests.phase_4b_helpers import chunk


def case(**overrides) -> RetrievalEvalCase:
    payload = {
        "case_id": "case_hit",
        "request": request(),
        "expected_ids": ["kc_hit"],
        "forbidden_ids": [],
        "minimum_recall": 1.0,
        "expected_top_id": "kc_hit",
    }
    payload.update(overrides)
    return RetrievalEvalCase.model_validate(payload)


def test_eval_pass_partial_missing_forbidden_top_and_summary() -> None:
    hit = retrieve([chunk("kc_hit")])
    partial = retrieve([chunk("kc_hit")])
    forbidden = retrieve([chunk("kc_hit"), chunk("kc_forbidden", document_id="doc_forbidden")])
    evaluator = RetrievalEvaluator()

    assert evaluator.evaluate_case(case(), hit).passed
    assert evaluator.evaluate_case(case(expected_ids=["kc_hit", "kc_missing"], minimum_recall=1.0), partial).missing_expected_ids == ["kc_missing"]
    assert not evaluator.evaluate_case(case(forbidden_ids=["kc_forbidden"], expected_top_id=None), forbidden).passed
    assert not evaluator.evaluate_case(case(expected_top_id="kc_other"), hit).passed
    summary = evaluator.evaluate_many([(case(), hit), (case(expected_ids=["missing"]), hit)])
    assert summary.total_cases == 2
    assert summary.passed_cases == 1
    assert summary.failed_cases == 1
    assert summary.mean_recall == 0.5


def test_eval_validation_serialization_and_retrieval_errors_fail() -> None:
    with pytest.raises(PydanticValidationError):
        case(expected_ids=["kc_same"], forbidden_ids=["kc_same"])
    with pytest.raises(PydanticValidationError):
        case(expected_ids=["kc_hit", "kc_hit"])

    error_result = RetrievalResult(
        items=[],
        trace=RetrievalTrace(
            retriever_type="static",
            retriever_version="exact_metadata_v1",
            request_id="rr_error",
            candidate_ids=[],
            selected_ids=[],
            excluded=[],
            filters_applied={},
        ),
        errors=[
            ValidationError(
                code="RETRIEVAL_INDEX_EMPTY",
                message="empty",
                object_type="KnowledgeIndex",
                object_id=None,
                field=None,
                related_id=None,
            )
        ],
    )
    result = RetrievalEvaluator().evaluate_case(case(expected_ids=[]), error_result)

    assert not result.passed
    assert json.loads(json.dumps(result.model_dump(mode="json")))["errors"][0]["code"] == "RETRIEVAL_INDEX_EMPTY"

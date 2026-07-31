import json
import os

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.embedding_contracts import (
    EmbeddingItem,
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTrace,
    EmbeddingVector,
    stable_embedding_request_id,
)

from scripts import run_phase_4c_vector_retrieval_demo as demo


class CountingEmbeddingProvider:
    instances = []
    fail_on_call: int | None = None

    def __init__(self) -> None:
        self.call_count = 0
        self.requests = []
        self.__class__.instances.append(self)

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.call_count += 1
        self.requests.append(request)
        if self.fail_on_call == self.call_count:
            return _failed_embedding(request)
        vectors = [
            EmbeddingVector(item_id=item.item_id, values=_embedding_values(item.text), dimensions=3)
            for item in request.items
        ]
        return EmbeddingResult(
            vectors=vectors,
            trace=EmbeddingTrace(
                request_id=stable_embedding_request_id(request),
                provider="openai",
                provider_version=request.provider_version,
                model=request.model,
                input_ids=[item.item_id for item in request.items],
                output_ids=[vector.item_id for vector in vectors],
                dimensions=3,
                status="SUCCESS",
                error_code=None,
            ),
            errors=[],
        )


def test_phase_4c_help_does_not_read_environment(monkeypatch, capsys) -> None:
    getenv_calls = []

    def record_getenv(name, default=None):
        getenv_calls.append(name)
        return None

    monkeypatch.setattr(os.environ, "get", record_getenv)
    try:
        demo.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    output = capsys.readouterr().out
    assert "--confirm-live" in output
    assert "OPENAI_API_KEY" not in getenv_calls
    assert "OPENAI_EMBEDDING_MODEL" not in getenv_calls


def test_phase_4c_missing_confirm_does_not_read_key(monkeypatch, capsys) -> None:
    getenv_calls = []

    def record_getenv(name, default=None):
        getenv_calls.append(name)
        return None

    monkeypatch.setattr(os.environ, "get", record_getenv)
    assert demo.main([]) == 2
    assert "--confirm-live" in capsys.readouterr().err
    assert "OPENAI_API_KEY" not in getenv_calls
    assert "OPENAI_EMBEDDING_MODEL" not in getenv_calls


def test_phase_4c_missing_model_or_key_exits_before_openai(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert demo.main(["--confirm-live"]) == 2
    assert "Embedding model is required" in capsys.readouterr().err

    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "embedding-test")
    assert demo.main(["--confirm-live"]) == 2
    assert "OPENAI_API_KEY is required" in capsys.readouterr().err


def test_phase_4c_no_eval_batches_document_and_main_query_once(monkeypatch, capsys) -> None:
    _patch_live_provider(monkeypatch)

    assert demo.main(["--confirm-live", "--embedding-model", "embedding-test"]) == 0
    report = json.loads(capsys.readouterr().out)
    provider = CountingEmbeddingProvider.instances[0]

    assert provider.call_count == 2
    assert [len(request.items) for request in provider.requests] == [5, 1]
    assert report["document_embedding_api_calls"] == 1
    assert report["query_embedding_api_calls"] == 1
    assert report["embedding_api_call_count"] == 2
    assert report["retrieval"]["filters"]["query_match_mode"] == "vector_similarity_after_metadata_filter"
    assert report["retrieval"]["filters"]["ranking_version"] == "qdrant_cosine_v1"
    assert "exact_rank_v1" not in report["retrieval"]["filters"].values()


def test_phase_4c_run_eval_dedupes_queries_into_one_batch(monkeypatch, capsys) -> None:
    _patch_live_provider(monkeypatch)

    assert demo.main(["--confirm-live", "--embedding-model", "embedding-test", "--run-eval"]) == 0
    report = json.loads(capsys.readouterr().out)
    provider = CountingEmbeddingProvider.instances[0]
    query_request = provider.requests[1]

    assert provider.call_count == 2
    assert [item.text for item in query_request.items] == [
        "cup holder crumbs",
        "script scene timing",
        "seat seam debris",
    ]
    assert report["document_embedding_api_calls"] == 1
    assert report["query_embedding_api_calls"] == 1
    assert report["embedding_api_call_count"] == 2
    assert report["eval"]["total_cases"] == 3


def test_phase_4c_precomputed_provider_unknown_query_fails_without_openai() -> None:
    source_request = EmbeddingRequest(
        items=[EmbeddingItem(item_id="query_1", text="known query")],
        model="embedding-test",
        provider_version="openai_embedding_v1",
    )
    source_result = CountingEmbeddingProvider().embed(source_request)
    provider = demo._PrecomputedQueryEmbeddingProvider(source_result, {"query_1": "known query"})

    result = provider.embed(
        EmbeddingRequest(
            items=[EmbeddingItem(item_id="query_missing", text="unknown query")],
            model="embedding-test",
            provider_version="openai_embedding_v1",
        )
    )

    assert provider.calls == 1
    assert [error.code for error in result.errors] == ["EMBEDDING_OUTPUT_INVALID"]
    assert result.errors[0].related_id == "query_missing"
    assert result.vectors == []


def test_phase_4c_query_batch_failure_skips_retrieval_and_eval(monkeypatch, capsys) -> None:
    _patch_live_provider(monkeypatch)
    CountingEmbeddingProvider.fail_on_call = 2

    assert demo.main(["--confirm-live", "--embedding-model", "embedding-test", "--run-eval"]) == 1
    report = json.loads(capsys.readouterr().out)
    provider = CountingEmbeddingProvider.instances[0]

    assert provider.call_count == 2
    assert report["document_embedding_api_calls"] == 1
    assert report["query_embedding_api_calls"] == 1
    assert report["embedding_api_call_count"] == 2
    assert [error["code"] for error in report["query_embedding"]["errors"]] == ["EMBEDDING_CALL_FAILED"]
    assert report["retrieval"]["status"] == "SKIPPED"
    assert "eval" not in report


def _patch_live_provider(monkeypatch) -> None:
    CountingEmbeddingProvider.instances = []
    CountingEmbeddingProvider.fail_on_call = None
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "embedding-test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setattr(demo, "OpenAIEmbeddingProvider", CountingEmbeddingProvider)


def _embedding_values(text: str) -> list[float]:
    normalized = text.casefold()
    if "script scene timing" in normalized or "three short beats" in normalized:
        return [0.0, 1.0, 0.0]
    if "seat seam debris" in normalized and ("jp" in normalized or normalized == "seat seam debris"):
        return [0.0, 0.0, 1.0]
    return [1.0, 0.0, 0.0]


def _failed_embedding(request: EmbeddingRequest) -> EmbeddingResult:
    return EmbeddingResult(
        vectors=[],
        trace=EmbeddingTrace(
            request_id=stable_embedding_request_id(request),
            provider="openai",
            provider_version=request.provider_version,
            model=request.model,
            input_ids=[item.item_id for item in request.items],
            output_ids=[],
            dimensions=None,
            status="FAILED",
            error_code="EMBEDDING_CALL_FAILED",
        ),
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

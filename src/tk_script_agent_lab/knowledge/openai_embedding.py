import os
from collections.abc import Callable

from openai import OpenAI

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.embedding_contracts import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTrace,
    EmbeddingVector,
    stable_embedding_request_id,
)

OPENAI_EMBEDDING_PROVIDER_VERSION = "openai_embedding_v1"


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key_getter: Callable[[], str | None] | None = None,
        client_factory: Callable[[str], object] | None = None,
    ) -> None:
        self._api_key_getter = api_key_getter or (lambda: os.environ.get("OPENAI_API_KEY"))
        self._client_factory = client_factory or (lambda api_key: OpenAI(api_key=api_key))
        self.call_count = 0

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        request_id = stable_embedding_request_id(request)
        if not request.model.strip():
            return _failed(request, request_id, "EMBEDDING_CONFIGURATION_MISSING", "Embedding model is required.", "model")
        api_key = self._api_key_getter()
        if not api_key:
            return _failed(request, request_id, "EMBEDDING_CONFIGURATION_MISSING", "OPENAI_API_KEY is required for embeddings.", None)
        try:
            self.call_count += 1
            response = self._client_factory(api_key).embeddings.create(
                model=request.model,
                input=[item.text for item in request.items],
            )
            data = list(response.data)
        except Exception as exc:  # noqa: BLE001 - provider boundary maps SDK failures.
            return _failed(request, request_id, "EMBEDDING_CALL_FAILED", f"OpenAI embedding call failed: {type(exc).__name__}", None)
        if len(data) != len(request.items):
            return _failed(request, request_id, "EMBEDDING_OUTPUT_INVALID", "OpenAI returned a different number of embeddings.", None)
        vectors: list[EmbeddingVector] = []
        dimensions: int | None = None
        try:
            ordered = sorted(data, key=lambda item: item.index)
            for source, item in zip(request.items, ordered, strict=True):
                vector_values = list(item.embedding)
                vector = EmbeddingVector(
                    item_id=source.item_id,
                    values=vector_values,
                    dimensions=len(vector_values),
                )
                if dimensions is None:
                    dimensions = vector.dimensions
                if vector.dimensions != dimensions:
                    return _failed(request, request_id, "EMBEDDING_DIMENSION_MISMATCH", "OpenAI returned inconsistent embedding dimensions.", None)
                vectors.append(vector)
        except Exception:
            return _failed(request, request_id, "EMBEDDING_OUTPUT_INVALID", "OpenAI embedding output could not be parsed.", None)
        return EmbeddingResult(
            vectors=vectors,
            trace=EmbeddingTrace(
                request_id=request_id,
                provider="openai",
                provider_version=request.provider_version,
                model=request.model,
                input_ids=[item.item_id for item in request.items],
                output_ids=[vector.item_id for vector in vectors],
                dimensions=dimensions,
                status="SUCCESS",
                error_code=None,
            ),
            errors=[],
        )


def _failed(
    request: EmbeddingRequest,
    request_id: str,
    code: str,
    message: str,
    field: str | None,
) -> EmbeddingResult:
    return EmbeddingResult(
        vectors=[],
        trace=EmbeddingTrace(
            request_id=request_id,
            provider="openai",
            provider_version=request.provider_version,
            model=request.model,
            input_ids=[item.item_id for item in request.items],
            output_ids=[],
            dimensions=None,
            status="FAILED",
            error_code=code,
        ),
        errors=[
            ValidationError(
                code=code,
                message=message,
                object_type="OpenAIEmbeddingProvider",
                object_id=None,
                field=field,
                related_id=None,
            )
        ],
    )

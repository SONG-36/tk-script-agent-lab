import json
import math

import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.knowledge.embedding_contracts import (
    EmbeddingItem,
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTrace,
    EmbeddingVector,
    stable_embedding_request_id,
)


def request() -> EmbeddingRequest:
    return EmbeddingRequest(
        items=[EmbeddingItem(item_id="kc_one", text="Cup holder crumbs")],
        model="embedding-test",
        provider_version="openai_embedding_v1",
    )


def test_embedding_contracts_validate_and_serialize() -> None:
    vector = EmbeddingVector(item_id="kc_one", values=[0.1, 0.2], dimensions=2)
    result = EmbeddingResult(
        vectors=[vector],
        trace=EmbeddingTrace(
            request_id=stable_embedding_request_id(request()),
            provider="openai",
            provider_version="openai_embedding_v1",
            model="embedding-test",
            input_ids=["kc_one"],
            output_ids=["kc_one"],
            dimensions=2,
            status="SUCCESS",
        ),
        errors=[],
    )
    payload = json.dumps(result.model_dump(mode="json"))

    assert "kc_one" in payload
    assert "api_key" not in payload.casefold()


def test_embedding_contracts_reject_invalid_inputs() -> None:
    with pytest.raises(PydanticValidationError):
        EmbeddingRequest.model_validate({"items": [], "model": "m", "provider_version": "v"})
    with pytest.raises(PydanticValidationError):
        EmbeddingRequest.model_validate(
            {
                "items": [
                    {"item_id": "dup", "text": "a"},
                    {"item_id": "dup", "text": "b"},
                ],
                "model": "m",
                "provider_version": "v",
            }
        )
    with pytest.raises(PydanticValidationError):
        EmbeddingItem(item_id="x", text="")
    with pytest.raises(PydanticValidationError):
        EmbeddingVector(item_id="x", values=[1.0], dimensions=2)
    with pytest.raises(PydanticValidationError):
        EmbeddingVector(item_id="x", values=[math.inf], dimensions=1)
    with pytest.raises(PydanticValidationError):
        EmbeddingItem.model_validate({"item_id": "x", "text": "y", "api_key": "z"})

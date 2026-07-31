from types import SimpleNamespace

from tk_script_agent_lab.knowledge.embedding_contracts import EmbeddingItem, EmbeddingRequest
from tk_script_agent_lab.knowledge.openai_embedding import OpenAIEmbeddingProvider


class StubEmbeddings:
    def __init__(self, response_data=None, error: Exception | None = None) -> None:
        self.calls = []
        self.response_data = (
            [
                SimpleNamespace(index=0, embedding=[1.0, 0.0]),
                SimpleNamespace(index=1, embedding=[0.0, 1.0]),
            ]
            if response_data is None
            else response_data
        )
        self.error = error

    def create(self, *, model, input):
        self.calls.append({"model": model, "input": input})
        if self.error:
            raise self.error
        return SimpleNamespace(data=self.response_data)


class StubClient:
    def __init__(self, embeddings: StubEmbeddings) -> None:
        self.embeddings = embeddings


def request(model: str = "embedding-test") -> EmbeddingRequest:
    return EmbeddingRequest(
        items=[
            EmbeddingItem(item_id="kc_one", text="one"),
            EmbeddingItem(item_id="kc_two", text="two"),
        ],
        model=model,
        provider_version="openai_embedding_v1",
    )


def test_openai_embedding_provider_batches_and_maps_order() -> None:
    embeddings = StubEmbeddings(
        response_data=[
            SimpleNamespace(index=1, embedding=[0.0, 1.0]),
            SimpleNamespace(index=0, embedding=[1.0, 0.0]),
        ]
    )
    provider = OpenAIEmbeddingProvider(
        api_key_getter=lambda: "test-key",
        client_factory=lambda key: StubClient(embeddings),
    )
    original = request()
    result = provider.embed(original)

    assert len(embeddings.calls) == 1
    assert embeddings.calls[0]["input"] == ["one", "two"]
    assert [vector.item_id for vector in result.vectors] == ["kc_one", "kc_two"]
    assert result.trace.dimensions == 2
    assert provider.call_count == 1
    assert original.items[0].text == "one"


def test_openai_embedding_provider_errors_are_stable_and_no_retry() -> None:
    missing_key = OpenAIEmbeddingProvider(api_key_getter=lambda: None).embed(request())
    assert [error.code for error in missing_key.errors] == ["EMBEDDING_CONFIGURATION_MISSING"]

    embeddings = StubEmbeddings(error=RuntimeError("boom"))
    failed = OpenAIEmbeddingProvider(
        api_key_getter=lambda: "test-key",
        client_factory=lambda key: StubClient(embeddings),
    ).embed(request())
    assert len(embeddings.calls) == 1
    assert [error.code for error in failed.errors] == ["EMBEDDING_CALL_FAILED"]

    wrong_count = OpenAIEmbeddingProvider(
        api_key_getter=lambda: "test-key",
        client_factory=lambda key: StubClient(StubEmbeddings(response_data=[])),
    ).embed(request())
    assert [error.code for error in wrong_count.errors] == ["EMBEDDING_OUTPUT_INVALID"]

    mismatch = OpenAIEmbeddingProvider(
        api_key_getter=lambda: "test-key",
        client_factory=lambda key: StubClient(
            StubEmbeddings(
                response_data=[
                    SimpleNamespace(index=0, embedding=[1.0]),
                    SimpleNamespace(index=1, embedding=[1.0, 2.0]),
                ]
            )
        ),
    ).embed(request())
    assert [error.code for error in mismatch.errors] == ["EMBEDDING_DIMENSION_MISMATCH"]

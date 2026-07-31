# RAG Embedding Contract V1

Phase 4C introduces text-to-vector contracts for future vector retrieval.

## EmbeddingItem

`EmbeddingItem` contains only `item_id` and `text`. It does not contain a full
`KnowledgeChunk`, API key, prompt, or graph state.

## EmbeddingRequest

`EmbeddingRequest` contains a non-empty list of unique items, an explicit model,
and a provider version. It does not contain vector store configuration or API
keys.

## EmbeddingVector

`EmbeddingVector` stores `item_id`, finite float values, and dimensions. The
dimension count must equal vector length.

## EmbeddingTrace

`EmbeddingTrace` records stable request ID, provider, model, input IDs, output
IDs, dimensions, status, and error code. It does not store original text,
vectors, headers, API keys, or SDK objects.

## EmbeddingProvider

```python
class EmbeddingProvider(Protocol):
    def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...
```

V1 has no async, streaming, cache, retry, model discovery, or batch scheduler.

## OpenAIEmbeddingProvider

`OpenAIEmbeddingProvider` performs one OpenAI embeddings API call for one
`EmbeddingRequest`. It reads `OPENAI_API_KEY` only at execution time, never from
contracts, trace, state, logs, or demo output. It does not call Chat Completions.

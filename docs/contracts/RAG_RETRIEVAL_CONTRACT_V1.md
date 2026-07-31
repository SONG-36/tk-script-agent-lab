# RAG Retrieval Contract V1

Phase 3B defines the retrieval contract for future RAG without implementing vector RAG.

## RetrievalRequest

Fields:

- `stage`: `creative` or `script`
- `target_market`
- `product_category`
- `query`
- `limit`
- `filters`

Rules:

- extra fields are rejected;
- `query` must be non-empty;
- `limit` must be greater than zero;
- request must not contain API keys, model config, Graph state, review decisions, or model call records.

## RetrievedKnowledge

Fields:

- `knowledge_id`
- `title`
- `content`
- `kind`
- `provenance_type`
- `evidence_status`
- `source_reference`
- `metadata`
- `score`

Rules:

- `knowledge_id` and `content` must be non-empty;
- `score` may be `null` for static retrieval;
- retrieved knowledge is not automatically converted into `ProductFact`;
- retrieved knowledge cannot become `CreativeIdea.source_usages`.

## RetrievalTrace

Fields:

- `retriever_type`: `static` or `vector`
- `retriever_version`
- `request_id`
- `candidate_ids`
- `selected_ids`
- `excluded`
- `filters_applied`

Rules:

- IDs are stable;
- no random UUID or current time is used;
- trace must not store prompt text, API keys, embedding vectors, or adapter clients.

## RetrievalResult

Fields:

- `items`
- `trace`
- `errors`

Rules:

- result is JSON serializable;
- same input produces stable static results;
- non-empty errors mean retrieval failed for workflow purposes;
- no adapter-private objects are included.

## KnowledgeRetriever

```python
class KnowledgeRetriever(Protocol):
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        ...
```

No async, batch, streaming, reranking, upsert, delete, index rebuild, or health-check API is part of V1.

## Static Adapter

`StaticKnowledgeRetriever`:

- receives a fixed `pack_id`;
- reuses the safe YAML loader;
- reuses the deterministic selector;
- maps `CreativeKnowledgeItem` to `RetrievedKnowledge`;
- maps selection information to `RetrievalTrace`;
- never calls a model or network.

## Future Vector Adapter

A future vector adapter should implement `KnowledgeRetriever`. It may add embeddings and vector search internally in a later phase, but it must still return `RetrievalResult` and keep knowledge separate from business evidence.

## Ingestion Relationship

Phase 4A introduces ingestion-side contracts and Phase 4B connects them to this retrieval contract through an in-memory index:

```text
IngestionResult.chunks
    -> InMemoryKnowledgeIndex
    -> KnowledgeRetriever
    -> RetrievalResult
```

Chunks remain knowledge guidance. They do not become business evidence and they must not appear as `CreativeIdea.SourceUsage`.

Phase 4B exact retrieval remains deterministic and offline. It does not add embeddings, vector search, semantic retrieval, reranking, or prompt injection.

## JSON Example

```json
{
  "items": [
    {
      "knowledge_id": "ck_hook_visible_micro_mess",
      "title": "Open on a visible micro-mess",
      "content": "Start the idea with a small, easy-to-recognize car mess.",
      "kind": "hook_pattern",
      "provenance_type": "internal_working_rule",
      "evidence_status": "hypothesis",
      "source_reference": null,
      "metadata": {
        "status": "active"
      },
      "score": null
    }
  ],
  "trace": {
    "retriever_type": "static",
    "retriever_version": "static_selector_v1",
    "request_id": "ks_example",
    "candidate_ids": ["ck_hook_visible_micro_mess"],
    "selected_ids": ["ck_hook_visible_micro_mess"],
    "excluded": [],
    "filters_applied": {
      "pack_id": "tiktok_car_cleaning_v1"
    }
  },
  "errors": []
}
```

This contract does not mean full RAG has been implemented.

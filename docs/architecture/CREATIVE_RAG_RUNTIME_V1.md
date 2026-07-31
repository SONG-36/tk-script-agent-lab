# Creative RAG Runtime V1

Phase 4D connects vector retrieval to Creative generation through the existing
`select_creative_knowledge` LangGraph node.

## Scope

The runtime:

- loads the registered Creative Knowledge Pack;
- maps active pack items to `KnowledgeDocument`;
- ingests documents into deterministic chunks;
- embeds document chunks once per process-local runtime key;
- builds an in-memory Qdrant Local collection;
- exposes `VectorKnowledgeRetriever` behind the existing retrieval boundary.

The runtime key is based on pack id, pack version, embedding model, and vector
retriever version.

## Lifecycle

The runtime is process-local and non-persistent. A matching runtime is reused in
the same Python process. Process restart rebuilds the index.

This is a development runtime, not a production index lifecycle design. There is
no TTL, LRU, database, Redis, background refresh, distributed lock, or persistent
Qdrant path.

## Boundaries

The runtime does not enter Graph State. State may contain safe traces:

- `RetrievalTrace`;
- `EmbeddingTrace`;
- `VectorBuildTrace`.

State must not contain raw vectors, Qdrant clients, API keys, raw OpenAI
responses, full prompts, or runtime objects.

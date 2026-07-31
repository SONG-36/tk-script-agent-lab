# RAG Vector Store Contract V1

Phase 4C introduces a minimal vector store boundary for local Qdrant retrieval.

## VectorIndexItem

`VectorIndexItem` pairs one `KnowledgeChunk` with one `EmbeddingVector`.
`chunk.chunk_id` must equal `vector.item_id`.

## VectorBuildRequest

`VectorBuildRequest` contains index items, a safe collection name, and an index
version. It rejects duplicate chunks and inconsistent dimensions.

## VectorBuildTrace

`VectorBuildTrace` records build ID, store type, collection, input IDs, indexed
IDs, rejected IDs, dimensions, and status. It does not store vectors, chunk
text, client objects, API keys, or prompts.

## VectorSearchRequest

`VectorSearchRequest` contains a query vector, a `RetrievalRequest`, and a
collection name. It does not contain graph state or prompts.

## VectorSearchResult

`VectorSearchResult` contains scored chunk IDs, trace, and errors. Hits do not
include full chunks; citation is recovered through `VectorStore.get_chunk()`.

## VectorStore

```python
class VectorStore(Protocol):
    def build(self, request: VectorBuildRequest) -> VectorBuildResult: ...
    def search(self, request: VectorSearchRequest) -> VectorSearchResult: ...
    def get_chunk(self, chunk_id: str) -> KnowledgeChunk | None: ...
```

V1 has no delete, persistence, remote connection management, async API,
collection registry, health check, backup, or replication.

## QdrantLocalVectorStore

`QdrantLocalVectorStore` uses `QdrantClient(":memory:")`. It does not start
Docker, connect to remote Qdrant, or write Qdrant files.

Metadata filtering uses the same deterministic semantics as Phase 4B before
vector similarity ranking. Qdrant receives only eligible point IDs for vector
sorting.

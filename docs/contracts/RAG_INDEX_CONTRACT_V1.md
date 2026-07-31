# RAG Index Contract V1

Phase 4B connects Phase 4A chunks to Phase 3B retrieval through a pure in-memory
index. It is not a vector store and does not persist data.

## IndexBuildRequest

`IndexBuildRequest` contains:

- `chunks: list[KnowledgeChunk]`
- `index_version`

The request rejects extra fields and empty chunk lists. It does not contain
embeddings, database settings, API keys, Graph state, or retriever objects.

## IndexBuildTrace

`IndexBuildTrace` records:

- stable `build_id`;
- `index_type = "in_memory"`;
- `index_version`;
- input, indexed, rejected, and duplicate chunk IDs;
- chunk count.

The trace stores IDs only. It does not store chunk text, embeddings, index
objects, or runtime clients.

## IndexBuildResult

`IndexBuildResult` contains the trace and structured `ValidationError` values.
Non-empty errors mean the build did not succeed.

## KnowledgeIndex

```python
class KnowledgeIndex(Protocol):
    def build(self, request: IndexBuildRequest) -> IndexBuildResult: ...
    def get(self, chunk_id: str) -> KnowledgeChunk | None: ...
    def snapshot(self) -> tuple[KnowledgeChunk, ...]: ...
```

The V1 port has no upsert, delete, persistence, transaction, async, health
check, or embedding search API.

## InMemoryKnowledgeIndex

`InMemoryKnowledgeIndex`:

- deep-copies input chunks;
- sorts snapshots by `document_id`, `sequence`, and `chunk_id`;
- builds a stable `build_id` independent of input order;
- replaces the full snapshot on each successful build;
- returns defensive copies from `get()` and `snapshot()`.

## Atomic Build

Duplicate `chunk_id` values produce `INDEX_DUPLICATE_CHUNK_ID`. The failed build
does not partially write and the previous snapshot remains unchanged.

## Stable Build ID

The build ID is based on:

- `index_version`;
- sorted `chunk_id`;
- `document_id`;
- `sequence`;
- content SHA-256;
- `document_version`.

It does not use UUIDs, current time, or Python `hash()`.

## No Persistence Boundary

The index is process-local memory only. It does not read disk, write disk,
connect to a database, or create vector index files.

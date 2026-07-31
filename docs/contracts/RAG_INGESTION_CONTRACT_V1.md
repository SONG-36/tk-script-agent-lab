# RAG Ingestion Contract V1

Phase 4A defines the local ingestion side of the future RAG framework:

```text
raw standardized text
-> KnowledgeDocument
-> deterministic chunking
-> KnowledgeChunk
-> IngestionTrace
-> IngestionResult
```

This is not vector RAG. It does not implement embeddings, vector databases,
semantic search, reranking, retrieval, LangGraph nodes, or model prompt
injection.

## Contracts

`DocumentSource` records where a document came from without storing content,
credentials, request headers, or local absolute paths. `official_url` sources
must use `http` or `https`; `internal_file` references must be relative and
must not traverse parent directories.

`KnowledgeDocument` is the document-level input. It keeps title, content,
version, language, provenance, evidence status, applicability, and metadata.
Internal working rules cannot be marked `verified`.

`KnowledgeChunk` is the deterministic chunk-level output. Chunk offsets are
relative to normalized `KnowledgeDocument.content`, not the original raw file
text. Chunks keep document provenance and evidence status. They do not contain
embeddings and must not become `ProductFact` or `CreativeIdea.SourceUsage`.

`ChunkingRequest` and `ChunkingResult` define the chunker boundary.
`IngestionRequest`, `IngestionTrace`, and `IngestionResult` define the ingestor
boundary.

## Ports

Phase 4A adds only two ports:

```python
class ChunkingStrategy(Protocol):
    def chunk(self, request: ChunkingRequest) -> ChunkingResult: ...

class KnowledgeIngestor(Protocol):
    def ingest(self, request: IngestionRequest) -> IngestionResult: ...
```

No async, batch, streaming, parser, embedding, persistence, queue, or index
methods are part of V1.

## Deterministic Chunking

`DeterministicParagraphChunker`:

- normalizes CRLF/CR to LF;
- trims trailing spaces per line;
- compresses three or more blank lines to one paragraph break;
- trims document boundaries;
- prefers paragraph boundaries;
- uses fixed character windows for paragraphs longer than `max_chars`;
- applies `overlap_chars` to fixed-window chunks;
- creates stable `kc_` IDs from document id, version, chunker version,
  sequence, and normalized chunk content.

The implementation does not use a tokenizer, model, network call, UUID, current
time, or Python `hash()`.

## Deterministic Ingestion

`DeterministicKnowledgeIngestor`:

- receives already constructed `KnowledgeDocument` objects;
- checks duplicate `document_id` values;
- delegates to `ChunkingStrategy`;
- rejects documents with chunking errors;
- checks duplicate `chunk_id` values;
- returns successful chunks plus structured `ValidationError` records;
- builds a stable `ir_` trace id.

It does not read disks, URLs, APIs, databases, vector stores, or environment
variables.

## Retrieval Relationship

Phase 4A stops before retrieval:

```text
IngestionResult.chunks
    -> future Phase 4B / 4C Index Adapter
    -> KnowledgeRetriever
    -> RetrievalResult
```

`RetrievalRequest`, `RetrievedKnowledge`, `RetrievalTrace`, and
`KnowledgeRetriever` keep their Phase 3B semantics.

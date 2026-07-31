# Phase 4A Ingestion Report

## Scope

Phase 4A adds the knowledge ingestion entry contract for future RAG work. It
does not change LangGraph, Provider behavior, Creative prompts, Script prompts,
or Phase 3B retrieval semantics.

## Implemented

- `KnowledgeDocument` and `DocumentSource` contracts.
- Deterministic text normalization.
- `KnowledgeChunk` with stable offsets and stable IDs.
- `ChunkingStrategy` and `KnowledgeIngestor` ports.
- `DeterministicParagraphChunker`.
- `DeterministicKnowledgeIngestor`.
- Local fixture and local demo for ingestion.

## Boundaries

The ingestor receives already constructed documents. Demo code may read the
fixture file, but `IngestionRequest` does not store arbitrary file paths and the
ingestor does not read from disk.

## Not Implemented

No embeddings, vector database, semantic retrieval, reranker, index manager,
parser registry, ingestion queue, persistence layer, Tool Calling, multi-agent
flow, or LangGraph ingestion node was added.

## Phase 4B Readiness

`IngestionResult.chunks` is the intended input to a future index adapter. That
future adapter should remain behind the existing `KnowledgeRetriever` boundary
instead of making OpenAI Providers responsible for retrieval.

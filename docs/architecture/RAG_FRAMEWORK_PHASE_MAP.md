# RAG Framework Phase Map

This map separates the RAG framework pieces that already exist from future
work. Phase 4B is still not vector RAG.

## Current Baseline

Phase 3B completed:

- Retrieval Contracts V1;
- `KnowledgeRetriever` Port;
- `StaticKnowledgeRetriever`;
- Framework Baseline V1.

Phase 4A completed:

- Ingestion Contracts V1;
- `KnowledgeDocument`;
- `KnowledgeChunk`;
- `ChunkingStrategy`;
- `KnowledgeIngestor`;
- `DeterministicParagraphChunker`;
- `DeterministicKnowledgeIngestor`.

Phase 4B completed:

- `KnowledgeIndex` Port;
- `InMemoryKnowledgeIndex`;
- exact / metadata retrieval;
- deterministic ranking;
- Retrieval Eval;
- no Embedding.

The current implemented chain is:

```text
KnowledgeDocument
-> KnowledgeChunk
-> IngestionResult
-> InMemoryKnowledgeIndex
-> ExactMetadataKnowledgeRetriever
-> RetrievalResult
-> Deterministic Retrieval Eval
```

Ingestion and Retrieval are different Ports. Ingestion prepares standardized
chunks. Retrieval later chooses relevant knowledge for a task.

## Future Phases

Phase 4C, not implemented:

- one real Embedding Adapter;
- one real Vector Store Adapter;
- `VectorKnowledgeRetriever`.

Phase 4D, not implemented:

- Creative RAG connection to LangGraph;
- retrieval result injection into the Creative Prompt;
- observable Retrieval Trace.

Phase 4E, not implemented:

- Script RAG connection to LangGraph;
- Script Knowledge;
- Script Retrieval Eval.

The future complete chain is:

```text
KnowledgeDocument
-> KnowledgeChunk
-> Index
-> KnowledgeRetriever
-> RetrievalResult
-> Prompt Grounding
```

## Explicit Non-Implementations

The current codebase does not implement:

- Embedding;
- Vector DB;
- Semantic Retrieval;
- Reranker;
- Creative RAG;
- Script RAG.

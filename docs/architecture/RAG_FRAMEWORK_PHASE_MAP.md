# RAG Framework Phase Map

This map separates the RAG framework pieces that already exist from future
work. Phase 4D adds Creative RAG but is still not Script RAG.

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

Phase 4C completed:

- `EmbeddingProvider` Port;
- `OpenAIEmbeddingProvider`;
- `VectorStore` Port;
- `QdrantLocalVectorStore`;
- `VectorKnowledgeRetriever`;
- Retrieval Eval reuse.

Phase 4D completed:

- Creative Pack to `KnowledgeDocument` adapter;
- deterministic Creative Retrieval Query;
- process-local Creative Vector Runtime;
- `knowledge_mode=vector`;
- Creative RAG connection through `select_creative_knowledge`;
- `creative_idea_v2` Creative Guidance grounding.

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

The Phase 4C vector chain is:

```text
KnowledgeChunk
-> OpenAIEmbeddingProvider
-> QdrantLocalVectorStore
-> VectorKnowledgeRetriever
-> RetrievalResult
```

The Phase 4D Creative RAG chain is:

```text
CreativeKnowledgePack
-> KnowledgeDocument
-> KnowledgeChunk
-> OpenAIEmbeddingProvider
-> QdrantLocalVectorStore
-> VectorKnowledgeRetriever
-> select_creative_knowledge
-> creative_idea_v2 Creative Guidance
```

Ingestion and Retrieval are different Ports. Ingestion prepares standardized
chunks. Retrieval later chooses relevant knowledge for a task.

## Future Phases

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
- Script RAG.

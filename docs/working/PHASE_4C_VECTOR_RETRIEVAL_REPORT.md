# Phase 4C Vector Retrieval Report

## Implemented

- `EmbeddingProvider` Port.
- `OpenAIEmbeddingProvider`.
- `VectorStore` Port.
- `QdrantLocalVectorStore`.
- `VectorKnowledgeRetriever`.
- Stubbed offline tests for embedding and vector retrieval.
- Safety-gated live demo.

## Boundaries

Phase 4C does not modify LangGraph, Creative Prompt, Script Prompt, Creative
Provider, or Script Provider. Vector retrieval remains a standalone adapter.

## Metadata Filter

Metadata filtering reuses Phase 4B semantics for stage, market, category,
effective date, wildcard, and custom metadata. Filtering happens before Qdrant
vector ranking.

## Trace Labels

Exact retrieval keeps `query_match_mode=exact_all_terms_or_phrase` and
`ranking_version=exact_rank_v1`. Vector retrieval uses
`query_match_mode=vector_similarity_after_metadata_filter` and
`ranking_version=qdrant_cosine_v1` in the internal trace and demo output.

## Citation

Vector hits return chunk IDs and scores. `VectorKnowledgeRetriever` resolves
each hit through `VectorStore.get_chunk()` before producing
`RetrievedKnowledge`.

## Eval

The Phase 4B `RetrievalEvaluator` is reused. Default tests use fixed vectors so
they are deterministic and offline.

## Live Demo

The live demo requires `--confirm-live`, an embedding model, and
`OPENAI_API_KEY`. It performs at most one document embedding call and one query
embedding call. It does not output vectors, API keys, raw OpenAI responses, or
Qdrant files.

## Known Limits

- vector retrieval quality depends on the chosen embedding model;
- Qdrant is local in-memory only;
- no embedding cache exists;
- no reranker or hybrid retrieval exists;
- no Prompt Grounding is connected yet.

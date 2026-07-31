# Phase 4B Retrieval Report

## Implemented

- `KnowledgeIndex` Port.
- `InMemoryKnowledgeIndex`.
- Atomic index build with duplicate chunk handling.
- `ExactMetadataKnowledgeRetriever`.
- Deterministic exact phrase / all-terms matching.
- Fixed ranking and tie-break rules.
- `RetrievalEvaluator`.
- Offline retrieval demo and synthetic eval fixture.

## Filter Semantics

Filtering happens before scoring:

- stage must match `chunk.task_stages`;
- target market must match exactly or `*`;
- product category must match exactly or `*`;
- optional `effective_on` applies date windows;
- custom metadata filters use exact normalized equality.

Invalid `effective_on` returns `RETRIEVAL_FILTER_INVALID`.

## Ranking

Scoring is deterministic:

- phrase in title: +100;
- phrase in content: +50;
- each query term in title: +10;
- each query term in content: +3.

Ties sort by document ID, sequence, and chunk ID. Items beyond limit are traced
as `over_limit`.

## Trace

`RetrievalTrace` records all candidate IDs, selected IDs, exclusions, filters,
query match mode, and ranking version. It does not store prompts, embeddings,
API keys, index objects, or model responses.

## Eval

Retrieval Eval checks expected IDs, forbidden IDs, recall, top ID, and retrieval
errors. It is not a business quality score.

## Demo

`scripts/run_phase_4b_retrieval_demo.py` runs entirely offline:

```bash
uv run python scripts/run_phase_4b_retrieval_demo.py --run-eval
```

## Change Radius

The implementation adds a small in-memory index/retriever/evaluator layer. It
does not modify LangGraph, prompts, providers, Domain, or Phase 4A ingestion
contracts.

## Known Limits

- exact retrieval cannot understand semantic similarity;
- term extraction is deterministic but not language-aware tokenization;
- in-memory index is not persistent;
- eval fixtures do not represent real business quality.

## Phase 4C Readiness

Phase 4C can introduce a vector adapter behind `KnowledgeRetriever` while
reusing `IngestionResult.chunks` and preserving Phase 4B eval boundaries.

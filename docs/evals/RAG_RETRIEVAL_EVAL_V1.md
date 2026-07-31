# RAG Retrieval Eval V1

Phase 4B adds deterministic retrieval evaluation. It checks whether retrieval
returns expected IDs and avoids forbidden IDs.

## RetrievalEvalCase

Fields:

- `case_id`;
- `request`;
- `expected_ids`;
- `forbidden_ids`;
- `minimum_recall`;
- `expected_top_id`.

Expected and forbidden IDs must be unique and cannot overlap.

## RetrievalEvalResult

Fields:

- selected IDs;
- matched expected IDs;
- missing expected IDs;
- forbidden hits;
- recall;
- optional top ID match;
- structured errors.

## RetrievalEvalSummary

The summary records total cases, passed cases, failed cases, mean recall, and
per-case results.

## Passing Conditions

A case passes when:

- recall is at least `minimum_recall`;
- there are no forbidden hits;
- `expected_top_id`, when present, is the first selected ID;
- the retrieval result has no errors.

## Not A Business Quality Eval

This eval does not judge creative quality, compliance quality, or script quality.
It only checks deterministic retrieval correctness.

## No LLM Judge

The evaluator does not use an LLM judge, embeddings, semantic similarity, or
preference models. That keeps retrieval correctness separate from generation
quality.

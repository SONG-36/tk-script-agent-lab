# Phase 3B Consolidation Report

## Audit Findings

Domain remains clean: it does not import LangGraph, OpenAI, YAML, providers, scripts, tests, or routing.

Providers own model boundary behavior and candidate mapping. They do not route Graph state or perform human review. Creative provider receives selected guidance through `CreativeGenerationRequest`.

Knowledge had safe loader and deterministic selector, but Graph node previously knew loader and selector details. Phase 3B introduces a retriever port and static adapter to reduce that coupling.

LangGraph nodes still contain orchestration and some state compatibility mapping. They do not build prompts or parse OpenAI structured output.

Demo scripts duplicate serializer allowlists and output summaries. This is acceptable for now; no demo framework was introduced.

## Actual Changes

- Added retrieval contracts in `knowledge/contracts.py`.
- Added `StaticKnowledgeRetriever` adapter.
- Updated `select_creative_knowledge` node to use retriever results.
- Kept existing Graph topology and state field names.
- Changed internal `creative_knowledge_items` type to retrieved JSON-safe knowledge.
- Added dependency direction tests.
- Added docs for framework baseline, dependency rules, and retrieval contract.

## Unmodified Areas

- Domain schemas and validation rules.
- OpenAI provider source validation.
- Creative and script prompt schemas.
- Graph topology.
- Human interrupt and resume flow.
- Knowledge YAML pack content.

## Change Radius

Production changes are intentionally small: new knowledge contract/adapter files plus narrow updates to state, provider request type, prompt conversion, and Graph node retrieval wiring.

## Remaining Risks

- Demo scripts still repeat checkpoint serializer allowlists.
- Graph node still owns compatibility mapping from `RetrievalResult` to `KnowledgeSelectionRecord`.
- Knowledge pack registration remains a fixed mapping.
- Fake provider helper in Graph node still reads Golden Case fixtures.

These are recorded but not expanded in Phase 3B to avoid over-engineering.

## Phase 4 Readiness

Future RAG should enter through `KnowledgeRetriever`, not through OpenAI providers. Static retriever remains available for zero-cost regression and small deterministic packs.

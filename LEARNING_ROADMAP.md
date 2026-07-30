# Learning Roadmap

Current status: Phase 1B implementation scope. Phase 1B is complete only when tests, demo commands, and validation commands pass.

## Phase 0: Project Baseline

Create repository structure, reference audit archive, Golden Case fixtures, technology boundary notes, agent rules, and Python import/test baseline.

No TikTok Agent business logic is implemented in Phase 0.

## Phase 1A: Deterministic Domain Model

Build deterministic product, fact, selling point, reference video, requirement, and validation models. Keep all validation rules in code.

Completed scope:

- fixed Pydantic v2 domain schemas;
- stable IDs for business objects;
- ID-only cross-object references;
- deterministic cross-reference validator;
- Golden Case loading, validation, serialization, and reload tests.

## Phase 1B: Fake Provider And Deterministic Workflow

Implemented scope:

- fixture-backed Fake Provider as a model boundary substitute;
- two-stage workflow: `start_workflow()` then `resume_with_review()`;
- explicit human idea selection gate;
- deterministic Provider output validation;
- completed workflow export to JSON and Markdown.

## Phase 2: Real LLM

Introduce a real LLM provider for constrained generation only after deterministic inputs, outputs, and validation boundaries are clear.

## Phase 3: Minimal RAG

Introduce a small retrieval layer for controlled local materials and source-aware script support. Do not use open-ended web research as the default knowledge source.

## Phase 4: LangGraph

Introduce a single graph entry, state layering, conditional routing, and loop budgets after the deterministic pipeline is proven.

## Phase 5: Tool Calling

Introduce tool calling only for bounded, auditable tools whose inputs, outputs, failures, and budgets are explicit.

## Phase 6: Eval And Product Iteration

Add repeatable eval cases, scoring rubrics, regression checks, and product iteration loops based on observed failures.

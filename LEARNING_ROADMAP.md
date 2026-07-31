# Learning Roadmap

Current status: Phase 3A implementation scope. Phase 3A is complete only when tests, import checks, compile checks, graph demos, and validation commands pass.

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

Completed scope:

- fixture-backed Fake Provider as a model boundary substitute;
- two-stage workflow: `start_workflow()` then `resume_with_review()`;
- explicit human idea selection gate;
- deterministic Provider output validation;
- completed workflow export to JSON and Markdown.

## Phase 1C: LangGraph Visualization And Studio Human Gate

Completed scope:

- single LangGraph entry in `langgraph.json`;
- input, internal, and output state layering;
- node and conditional edge orchestration;
- LangGraph interrupt/resume for human idea selection;
- Studio-ready input fixture.

## Phase 2A: OpenAI CreativeIdea Provider

Completed scope:

- optional OpenAI provider for `CreativeIdea` generation only;
- Fake Provider remains the default no-key path;
- constrained prompt context for product inputs, verified facts, selling points, and manual reference insights;
- Pydantic structured output for model candidates;
- deterministic mapping from candidates to domain IDs;
- model call records in graph state;
- LangGraph routing that stops failed model output before the human gate.

Phase 2A does not generate real `ScriptDraft` values. Phase 2B should handle that boundary separately.

## Phase 2B: Real ScriptDraft Provider

Current scope:

- optional OpenAI provider for `ScriptDraft` generation only after human approval;
- independent Creative and Script provider configuration;
- Pydantic structured output for script candidates and scenes;
- deterministic script, scene, product, creative idea, and source usage IDs;
- source and selected-idea validation before completion;
- Fake Creative + OpenAI Script as the primary live validation path.

## Phase 3A: Static Creative Knowledge Pack

Current scope:

- add a small human-readable Creative Knowledge Pack;
- validate the pack with fixed Pydantic schemas;
- select knowledge with deterministic code;
- inject selected guidance into `creative_idea_v2`;
- compare Control and Treatment runs without declaring an automatic winner.

Phase 3A is not vector RAG. It does not add embeddings, vector databases, semantic retrieval, reranking, tools, or ScriptDraft knowledge injection.

## Phase 3: Minimal RAG

Introduce a small retrieval layer for controlled local materials and source-aware script support. Do not use open-ended web research as the default knowledge source.

## Phase 4: LangGraph

Introduce a single graph entry, state layering, conditional routing, and loop budgets after the deterministic pipeline is proven.

## Phase 5: Tool Calling

Introduce tool calling only for bounded, auditable tools whose inputs, outputs, failures, and budgets are explicit.

## Phase 6: Eval And Product Iteration

Add repeatable eval cases, scoring rubrics, regression checks, and product iteration loops based on observed failures.

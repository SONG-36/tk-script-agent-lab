# Learning Roadmap

Current status: Phase 4D implementation scope.

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

## Phase 3B: Framework Consolidation And Retrieval Contracts

Completed scope:

- Framework Baseline V1;
- Retrieval Contracts V1;
- `KnowledgeRetriever` Port;
- `StaticKnowledgeRetriever`;
- dependency direction tests.

## Phase 4A: RAG Ingestion Contracts And Deterministic Chunking

Implemented / pending commit:

- RAG Ingestion Contracts;
- `KnowledgeDocument`;
- `KnowledgeChunk`;
- `ChunkingStrategy`;
- `KnowledgeIngestor`;
- deterministic chunking;
- stable chunk IDs;
- provenance preservation;
- offline ingestion demo.

Phase 4A is not complete RAG. It does not add embeddings, vector databases, semantic retrieval, reranking, Creative RAG, or Script RAG.

## Phase 4B: In-Memory Index And Retrieval Eval

Implemented / pending commit:

- In-Memory Index;
- exact and metadata retrieval;
- Retrieval Eval;
- no Embedding.

Phase 4B connects `IngestionResult.chunks` to `KnowledgeRetriever` through a
pure in-memory index. It remains offline and does not add vector search.

## Phase 4C: Embedding And Vector Store

Implemented / pending live validation:

- one real OpenAI Embedding adapter;
- one real Qdrant Local/In-Memory Vector Store adapter;
- `VectorKnowledgeRetriever`.

Phase 4C does not connect retrieval to LangGraph or prompts.

## Phase 4D: Creative RAG

Current scope:

- connect vector retrieval to the existing Creative LangGraph path;
- reuse the static Creative Knowledge Pack as the vector corpus;
- inject retrieved knowledge into `creative_idea_v2`;
- keep Retrieval, Embedding, and Vector Build traces observable;
- keep Script RAG out of scope.

## Phase 4E: Script RAG

Future scope:

- Script Knowledge;
- Script RAG connection to LangGraph;
- Script Retrieval Eval.

## Phase 3: Minimal RAG

Introduce a small retrieval layer for controlled local materials and source-aware script support. Do not use open-ended web research as the default knowledge source.

## Phase 4: LangGraph

Introduce a single graph entry, state layering, conditional routing, and loop budgets after the deterministic pipeline is proven.

## Phase 5: Tool Calling

Introduce tool calling only for bounded, auditable tools whose inputs, outputs, failures, and budgets are explicit.

## Phase 6: Eval And Product Iteration

Add repeatable eval cases, scoring rubrics, regression checks, and product iteration loops based on observed failures.

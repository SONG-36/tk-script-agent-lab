# Framework Baseline V1

Phase 3B freezes the current framework boundaries before vector RAG is introduced. The goal is lower change radius, not a new framework.

## Layering

```text
Domain
-> Application Contracts
-> Ports
-> Adapters
-> LangGraph Orchestration
-> Experiments / Evaluation
```

## Layer Responsibilities

Domain owns Pydantic business objects, stable IDs, and deterministic cross-object validation. It must not depend on LangGraph, OpenAI, PyYAML, prompts, providers, scripts, tests, or Studio.

Application Contracts define request/result shapes such as `CreativeGenerationRequest`, `ScriptGenerationRequest`, `RetrievalRequest`, and `RetrievalResult`.

Ports are protocols with current and planned implementations. V1 includes the existing provider protocol and `KnowledgeRetriever`.

Adapters implement ports. Current adapters are Fake Provider, OpenAI Creative Provider, OpenAI Script Provider, and `StaticKnowledgeRetriever`.

LangGraph Orchestration owns nodes, state writes, conditional routing, interrupt/resume, step records, and model call record aggregation.

Experiments / Evaluation includes Golden Case data, demo scripts, live integration tests, and eval rubrics. These consume `src`; `src` must not depend on them.

## Boundaries

Model work:

- OpenAI Creative generates `CreativeIdeaCandidate`.
- OpenAI Script generates `ScriptDraftCandidate`.
- Models do not select knowledge, approve ideas, validate business sources, or decide workflow status.

Deterministic code:

- validates domain objects and cross references;
- selects static knowledge;
- maps candidate output to stable IDs;
- routes Graph failures before human interrupt;
- records trace data.

Human work:

- selects or rejects creative ideas;
- reviews A/B output;
- evaluates quality with rubrics.

## Graph Boundary

Graph nodes may read state, build application requests, call a provider or retriever port, write state, append `WorkflowStepRecord`, and leave routing to routing functions.

Graph nodes must not know YAML file paths, prompt templates, OpenAI structured-output internals, embeddings, vector stores, or demo output formats.

## Provider Boundary

Creative and Script providers receive request contracts, perform fake or OpenAI generation, validate provider boundary constraints, map candidates to domain objects, and return result records.

Providers must not load knowledge, call retrievers, route Graph state, handle human review, or run A/B comparisons.

## Knowledge / RAG Slot

Knowledge retrieval enters through `KnowledgeRetriever.retrieve(RetrievalRequest) -> RetrievalResult`.

`StaticKnowledgeRetriever` is the current adapter. A future vector adapter can implement the same port without changing OpenAI providers or prompt schemas.

Knowledge is creative guidance. It is not `ProductFact`, `SellingPoint`, `ReferenceInsight`, or `SourceUsage` business evidence.

## State Audit

| Field | Scope | Writer | Reader | Studio visible | V1 status |
|---|---|---|---|---:|---|
| `run_id` | input/output | `validate_input` | all nodes | yes | frozen |
| `product_profile` | input | input | validation/prompt | yes | frozen |
| `product_facts` | input | input | validation/prompt/providers | yes | frozen |
| `selling_points` | input | input | validation/prompt/providers | yes | frozen |
| `reference_videos` | input | input | validation | yes | frozen |
| `reference_insights` | input/internal | `validate_input` | validation/prompt/providers | yes | frozen |
| `workflow_input` | internal | `validate_input` | nodes | yes | frozen |
| `creative_knowledge_items` | internal trace | `select_creative_knowledge` | creative prompt request | yes | not output-frozen |
| `knowledge_selection_records` | output trace | `select_creative_knowledge` | demos/evals | yes | frozen |
| `creative_ideas` | output | `generate_creative_ideas` | validation/human/script | yes | frozen |
| `selected_idea_id` | output | `apply_human_review` | script node/output | yes | frozen |
| `idea_review` | output | `apply_human_review` | script validation/output | yes | frozen |
| `resume_payload` | internal | `human_select_idea` | `apply_human_review` | yes | internal |
| `script_draft` | output | `generate_script` | validation/output | yes | frozen |
| `validation_errors` | output | validation/provider/retriever nodes | routing/output | yes | frozen |
| `step_records` | output trace | all nodes | output/demos | yes | frozen |
| `model_call_records` | output trace | model nodes | output/demos | yes | frozen |

State must not store API keys, prompt text, raw OpenAI responses, embeddings, vector clients, retriever objects, or YAML paths.

## Frozen Contracts

Frozen for V1:

- `CreativeGenerationRequest`
- `ScriptGenerationRequest`
- `RetrievalRequest`
- `RetrievedKnowledge`
- `RetrievalTrace`
- `RetrievalResult`
- `KnowledgeRetriever`
- Graph input/output state field names listed as frozen

Not frozen:

- future vector retriever internals;
- knowledge registration mechanism;
- retrieval eval metrics;
- script-stage knowledge retrieval.

## Extension Rules

New model: change configuration/model name, not Domain or Graph topology.

New provider: implement the existing provider request/result contract.

New knowledge pack: use the same YAML schema and static retriever. Fixed registry may need one mapping until an ingestion phase revisits registration.

New retriever: implement `KnowledgeRetriever`; do not change OpenAI providers.

New Graph stage: add explicit state fields, node, routing, and tests. Do not store runtime clients in state.

## Non-Goals

No embeddings, vector database, semantic search, reranker, chunking, ingestion, Tool Calling, multi-agent system, provider registry, plugin system, DI container, workflow engine, production API, or formal UI are implemented in Phase 3B.

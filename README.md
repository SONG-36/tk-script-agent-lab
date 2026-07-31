# tk-script-agent-lab

`tk-script-agent-lab` is a learning-oriented TikTok Script Agent Lab for an AI product manager. The project is intentionally built in phases so each step can separate product thinking from model behavior, deterministic code, validation, and later agent orchestration.

## Current Phase

Current status: Phase 4D.

Phase 0 established the repository baseline, reference audit archive, learning roadmap, technology boundaries, Golden Case fixtures, and import/test scaffolding.

Phase 1A added deterministic domain contracts and cross-reference validation for the TikTok Script Agent Lab.

Phase 1B adds a fixture-backed Fake Provider and a deterministic two-stage workflow with a real human gate.

Phase 1C adds a LangGraph visualization and orchestration layer over the already validated workflow.

Phase 2A adds an optional real OpenAI provider for `CreativeIdea` generation only. The default remains Fake Provider mode, so the project can run and test without an API key or model cost.

Phase 2B adds an optional real OpenAI provider for `ScriptDraft` generation after a human approves a creative idea.

Phase 3A adds static Creative Knowledge Pack injection and Control / Treatment A/B comparison for creative idea generation.

Phase 4A adds offline RAG ingestion contracts and deterministic chunking. It prepares local knowledge documents for future indexing, but it does not connect RAG to LangGraph, prompts, embeddings, vector databases, or semantic retrieval.

Phase 4B adds a pure in-memory index, exact metadata retrieval, deterministic ranking, and retrieval eval. It remains offline and does not add embeddings, a vector database, semantic retrieval, or LangGraph retrieval nodes.

Phase 4C adds a real OpenAI Embedding adapter, Qdrant Local/In-Memory vector store adapter, and `VectorKnowledgeRetriever`.

Phase 4D connects Creative RAG to the existing `select_creative_knowledge` LangGraph node. It injects vector-retrieved Creative Guidance into `creative_idea_v2` while keeping Script RAG out of scope.

There is still no real Agent in this phase. There are no tools, Script RAG, Skills, Tool Calling, TikTok API integrations, scraping integrations, second review interrupt, or production services.

## Learning Goal

The project is designed to help understand:

- data flow between user input, internal state, and output;
- model boundaries and where LLMs should not make decisions;
- deterministic code responsibilities;
- likely points where a system can fabricate, overclaim, or hide uncertainty;
- validation methods before and after model usage;
- staged evaluation of script quality and factual safety.

## Phase Model

The lab evolves one phase at a time. Phase 4D adds Creative RAG only. Later phases may introduce Script RAG, tool calling, and eval loops, but none of those are implemented yet.

## Phase 1A Capability

Phase 1A can:

- load fixed Pydantic domain objects;
- represent products, product facts, selling points, reference videos, reference insights, creative ideas, script drafts, and review decisions;
- express cross-object references only by stable IDs;
- reject invalid single-object states with Pydantic v2;
- return machine-readable validation errors for broken cross-object references;
- load, validate, serialize, and reload the car vacuum Golden Case.

Current data relationship:

```text
ProductProfile
├── ProductFact
├── SellingPoint -> ProductFact
├── ReferenceVideo -> ReferenceInsight
├── CreativeIdea -> SourceUsage
└── ScriptDraft -> CreativeIdea + SourceUsage
```

## Phase 1B Capability

Phase 1B can:

- load the Golden Case as `WorkflowInput`, Fake Provider fixtures, and review fixtures;
- validate workflow input before any Provider call;
- use a fixture-backed Fake Provider to simulate future model boundaries;
- pause at `AWAITING_IDEA_SELECTION`;
- resume only after an explicit `ReviewDecision`;
- generate a fixed script only for an approved creative idea;
- export a completed workflow to JSON and Markdown.

The Fake Provider does not generate new content. It returns fixed fixtures and is rechecked by deterministic validation.

Current data flow:

```text
WorkflowInput
→ deterministic validation
→ FakeProvider.reference_insights
→ deterministic validation
→ FakeProvider.creative_ideas
→ deterministic validation
→ HUMAN GATE
→ FakeProvider.script_draft
→ deterministic validation
→ export
```

Demo without selection:

```bash
uv run python scripts/run_phase_1b_demo.py
```

Demo with approval and export:

```bash
uv run python scripts/run_phase_1b_demo.py \
  --selected-idea-id idea_before_after_cleanup \
  --reviewer "demo-reviewer" \
  --output-dir artifacts/phase_1b_demo
```

## Phase 1C Capability

Phase 1C can:

- load `studio_input.json` as structured LangGraph input;
- validate manual `ReferenceInsight` values before creative generation;
- display nodes, state, conditional routing, interrupt, resume, errors, and step records in LangGraph Studio;
- pause at `human_select_idea` through LangGraph `interrupt()`;
- resume with a human review payload;
- generate the fixed Fake Provider script after approval.

Current LangGraph flow:

```text
Studio Input
→ validate_input
→ validate_manual_insights
→ Fake Creative Ideas
→ deterministic validation
→ LangGraph Interrupt
→ Human Review
→ Fake Script
→ deterministic validation
→ Studio Output
```

Studio usage:

```bash
uv run langgraph dev
```

Then choose graph `agent`, copy `data/golden_cases/car_vacuum_v1/studio_input.json` into the input, submit, review the interrupt payload, and resume with an approved review payload.

Graph demo:

```bash
uv run python scripts/run_phase_1c_graph_demo.py
uv run python scripts/run_phase_1c_graph_demo.py \
  --selected-idea-id idea_before_after_cleanup \
  --reviewer phase-1c-reviewer
```

普通数据变化应通过 Studio input or Golden Case JSON 调整；只有 Schema、业务规则或 Graph 结构变化才需要改源码。

Current boundary: ReferenceInsight is manually supplied, while CreativeIdea and ScriptDraft still come from Fake Provider fixtures. There is still no real model, RAG, Tool Calling, or product UI.

## Phase 2A Capability

Phase 2A can:

- keep Fake Provider as the default path with no `OPENAI_API_KEY`;
- switch the LangGraph creative idea node to OpenAI through graph context or Studio Config;
- build a constrained prompt context from product input, verified facts, selling points, manual `ReferenceInsight`, prohibited claims, and allowed source IDs;
- request Pydantic structured output for `CreativeIdeaCandidate` values;
- map model candidates to official domain `CreativeIdea` objects with deterministic IDs;
- validate model output before entering the human interrupt;
- record one `ModelCallRecord` for one OpenAI creative generation call.

Phase 2A flow:

```text
Studio Input
→ deterministic validation
→ manual ReferenceInsight
→ OpenAI CreativeIdea
→ Pydantic Structured Output
→ deterministic validation
→ LangGraph Interrupt
→ Human Review
```

Runtime configuration for Fake and OpenAI modes is documented in [docs/RUNTIME_CONFIGURATION.md](docs/RUNTIME_CONFIGURATION.md).

Script boundary: Phase 2A only replaces `CreativeIdea` generation. `ReferenceInsight` is still manually supplied, and `ScriptDraft` is still backed by Fake Provider fixtures. If an OpenAI-generated new idea is approved and no fixture script exists, the graph returns `SCRIPT_NOT_AVAILABLE`; it does not create a default script, choose another idea, or fabricate a `ScriptDraft`. Phase 2B is the correct place to replace script generation with a real model.

## Phase 2B Capability

Phase 2B can:

- keep Creative and Script providers independently configurable;
- run all fake mode for zero-cost regression;
- run OpenAI Creative with Fake Script to preserve the Phase 2A boundary;
- run Fake Creative with OpenAI Script to isolate script generation;
- run OpenAI Creative with OpenAI Script for the full real model chain;
- call OpenAI Script generation only after a human `APPROVED` decision;
- map script candidates to deterministic `ScriptDraft`, `ScriptScene`, and `SourceUsage` IDs;
- validate the script against the selected creative idea, product, sources, and explicit fact boundaries.

Supported provider combinations:

| Creative Provider | Script Provider | Expected Use |
|---|---|---|
| `fake` | `fake` | zero-cost full regression |
| `openai` | `fake` | real creative idea only |
| `fake` | `openai` | real script generation only |
| `openai` | `openai` | full real creative-to-script chain |

Script demo:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
export OPENAI_MODEL="<available-model-name>"
uv run python scripts/run_phase_2b_openai_script_demo.py \
  --creative-provider fake \
  --script-provider openai \
  --selected-idea-id idea_before_after_cleanup \
  --reviewer phase-2b-reviewer
```

Runtime configuration is documented in [docs/RUNTIME_CONFIGURATION.md](docs/RUNTIME_CONFIGURATION.md).

Current boundary: `ReferenceInsight` is still manually supplied, creative selection is still human-controlled, and there is no second automatic script review. A generated `ScriptDraft` must still be inspected by the team.

## Phase 3A Capability

Phase 3A can:

- load a static Creative Knowledge Pack from YAML;
- validate the pack with fixed Pydantic schemas;
- use a fixed pack-id loader instead of arbitrary file paths;
- select applicable knowledge with deterministic code;
- record `KnowledgeSelectionRecord` values in Graph state and output;
- insert a deterministic `select_creative_knowledge` Graph node before creative generation;
- use `creative_idea_v2` for both Control and Treatment runs;
- run Control / Treatment A/B comparison for creative idea generation;
- keep `ScriptDraft` generation unchanged from Phase 2B.

Phase 3A Graph flow:

```text
validate_manual_insights
→ select_creative_knowledge
→ generate_creative_ideas
→ validate_creative_ideas
→ human_select_idea
→ INTERRUPT
```

Creative Knowledge is Creative Guidance, not Business Evidence. Product facts, selling points, and reference insights remain the only allowed business evidence sources for `SourceUsage`. A `knowledge_id` must not enter `CreativeIdea.source_usages`.

Current knowledge documentation:

- [knowledge/README.md](knowledge/README.md)
- [docs/RUNTIME_CONFIGURATION.md](docs/RUNTIME_CONFIGURATION.md)
- [docs/evals/PHASE_3A_CREATIVE_AB_RUBRIC.md](docs/evals/PHASE_3A_CREATIVE_AB_RUBRIC.md)

Phase 3A is not RAG. It does not implement embeddings, a vector database, semantic retrieval, top-k similarity search, or a reranker. `ScriptDraft` Knowledge Pack injection is not implemented.

Phase 3A A/B demo:

```bash
# View help. This does not read environment variables and does not call a model.
uv run python scripts/run_phase_3a_creative_ab_demo.py --help
```

Run only Control:

```bash
uv run python scripts/run_phase_3a_creative_ab_demo.py \
  --mode control \
  --confirm-live
```

Run only Treatment:

```bash
uv run python scripts/run_phase_3a_creative_ab_demo.py \
  --mode treatment \
  --confirm-live
```

Run both variants:

```bash
uv run python scripts/run_phase_3a_creative_ab_demo.py \
  --mode both \
  --confirm-live
```

`control` calls OpenAI once. `treatment` calls OpenAI once. `both` calls OpenAI twice. If `--confirm-live` is not provided, the demo refuses to execute real calls. The A/B demo does not automatically announce a winner; use [docs/evals/PHASE_3A_CREATIVE_AB_RUBRIC.md](docs/evals/PHASE_3A_CREATIVE_AB_RUBRIC.md) for human review.

## Phase 4A Capability

Phase 4A can:

- represent ingestion input as `KnowledgeDocument`;
- preserve source provenance and evidence status;
- normalize knowledge text with deterministic rules;
- split text into `KnowledgeChunk` values with stable `chunk_id` values;
- run `DeterministicParagraphChunker` without a model, tokenizer, or network;
- run `DeterministicKnowledgeIngestor` to produce `IngestionResult`;
- run a local offline demo over a synthetic car-cleaning internal knowledge fixture.

Phase 4A is not connected to LangGraph, Creative Prompt injection, Script Prompt injection, embeddings, vector databases, semantic retrieval, top-k retrieval, or reranking.

Phase 4A documentation:

- [docs/contracts/RAG_INGESTION_CONTRACT_V1.md](docs/contracts/RAG_INGESTION_CONTRACT_V1.md)
- [docs/architecture/RAG_FRAMEWORK_PHASE_MAP.md](docs/architecture/RAG_FRAMEWORK_PHASE_MAP.md)
- [docs/working/PHASE_4A_INGESTION_REPORT.md](docs/working/PHASE_4A_INGESTION_REPORT.md)

Phase 4A ingestion demo:

```bash
uv run python scripts/run_phase_4a_ingestion_demo.py --help
```

```bash
uv run python scripts/run_phase_4a_ingestion_demo.py \
  --max-chars 500 \
  --overlap-chars 80
```

## Phase 4B Capability

Phase 4B can:

- build an `InMemoryKnowledgeIndex` from Phase 4A `KnowledgeChunk` values;
- reject duplicate chunk IDs with atomic build semantics;
- retrieve chunks with deterministic stage, market, category, date, and metadata filters;
- score exact phrase and all-term query matches with a fixed ranking rule;
- map selected chunks to `RetrievedKnowledge` while preserving provenance and evidence status;
- record candidate, exclusion, selected, filter, and ranking details in `RetrievalTrace`;
- run deterministic Retrieval Eval over expected and forbidden IDs.

Phase 4B is not vector RAG. It does not implement embeddings, vector databases, semantic retrieval, reranking, Creative RAG, Script RAG, or LangGraph retrieval nodes.

Phase 4B documentation:

- [docs/contracts/RAG_INDEX_CONTRACT_V1.md](docs/contracts/RAG_INDEX_CONTRACT_V1.md)
- [docs/evals/RAG_RETRIEVAL_EVAL_V1.md](docs/evals/RAG_RETRIEVAL_EVAL_V1.md)
- [docs/working/PHASE_4B_RETRIEVAL_REPORT.md](docs/working/PHASE_4B_RETRIEVAL_REPORT.md)
- [docs/architecture/RAG_FRAMEWORK_PHASE_MAP.md](docs/architecture/RAG_FRAMEWORK_PHASE_MAP.md)

Phase 4B retrieval demo:

```bash
uv run python scripts/run_phase_4b_retrieval_demo.py --help
```

```bash
uv run python scripts/run_phase_4b_retrieval_demo.py \
  --query "cup holder crumbs" \
  --target-market "US" \
  --product-category "car vacuum cleaner" \
  --stage creative \
  --limit 3 \
  --effective-on 2026-07-31
```

```bash
uv run python scripts/run_phase_4b_retrieval_demo.py --run-eval
```

## Phase 4C Capability

Phase 4C can:

- convert `KnowledgeChunk` text into vectors through `OpenAIEmbeddingProvider`;
- build a local in-memory Qdrant collection with `QdrantLocalVectorStore`;
- run vector similarity retrieval through `VectorKnowledgeRetriever`;
- preserve metadata filtering before vector ranking;
- return standard `RetrievalResult` and `RetrievedKnowledge`;
- reuse Phase 4B `RetrievalEvaluator`;
- keep `ExactMetadataKnowledgeRetriever` as the zero-cost deterministic baseline.

Phase 4C is not Creative RAG or Script RAG. It does not add LangGraph retrieval nodes, prompt grounding, reranking, hybrid search, query rewrite, persistent Qdrant storage, Tool Calling, or multi-agent behavior.

Phase 4C documentation:

- [docs/contracts/RAG_EMBEDDING_CONTRACT_V1.md](docs/contracts/RAG_EMBEDDING_CONTRACT_V1.md)
- [docs/contracts/RAG_VECTOR_STORE_CONTRACT_V1.md](docs/contracts/RAG_VECTOR_STORE_CONTRACT_V1.md)
- [docs/working/PHASE_4C_VECTOR_RETRIEVAL_REPORT.md](docs/working/PHASE_4C_VECTOR_RETRIEVAL_REPORT.md)

Phase 4C safe demo help:

```bash
uv run python scripts/run_phase_4c_vector_retrieval_demo.py --help
```

Live demo:

```bash
uv run python scripts/run_phase_4c_vector_retrieval_demo.py \
  --confirm-live \
  --embedding-model "<available-embedding-model>" \
  --query "cup holder crumbs" \
  --target-market US \
  --product-category "car vacuum cleaner" \
  --stage creative \
  --limit 3 \
  --run-eval
```

## Phase 4D Capability

Phase 4D can:

- run `knowledge_mode=off`, `knowledge_mode=static`, or `knowledge_mode=vector`;
- reuse the same Creative Knowledge Pack for static and vector modes;
- convert Creative Knowledge Pack items into `KnowledgeDocument` values;
- build a process-local Qdrant in-memory vector runtime;
- reuse the runtime in the same process for the same pack, version, embedding model, and retriever version;
- call vector retrieval inside the existing `select_creative_knowledge` node;
- record retrieval, embedding, and vector build traces in Graph State;
- inject selected vector guidance into `creative_idea_v2`;
- keep Creative Guidance separate from Business Evidence and `SourceUsage`;
- stop before Creative Provider if vector retrieval fails;
- keep Human Interrupt behavior unchanged.

Phase 4D Graph flow:

```text
validate_manual_insights
→ select_creative_knowledge
→ generate_creative_ideas
→ validate_creative_ideas
→ human_select_idea
→ INTERRUPT
```

Phase 4D is Creative RAG only. Script RAG, Script Knowledge, reranking, hybrid search, query rewrite, persistent Qdrant, embedding cache services, Tool Calling, and multi-agent behavior are not implemented.

Documentation:

- [docs/architecture/CREATIVE_RAG_RUNTIME_V1.md](docs/architecture/CREATIVE_RAG_RUNTIME_V1.md)
- [docs/contracts/CREATIVE_RAG_GROUNDING_V1.md](docs/contracts/CREATIVE_RAG_GROUNDING_V1.md)
- [docs/working/PHASE_4D_CREATIVE_RAG_REPORT.md](docs/working/PHASE_4D_CREATIVE_RAG_REPORT.md)
- [docs/RUNTIME_CONFIGURATION.md](docs/RUNTIME_CONFIGURATION.md)

Safe demo help:

```bash
uv run python scripts/run_phase_4d_creative_rag_demo.py --help
```

Offline fake demos:

```bash
uv run python scripts/run_phase_4d_creative_rag_demo.py \
  --knowledge-mode off \
  --creative-provider fake

uv run python scripts/run_phase_4d_creative_rag_demo.py \
  --knowledge-mode static \
  --creative-provider fake \
  --knowledge-pack tiktok_car_cleaning_v1
```

Live Creative RAG demo:

```bash
uv run python scripts/run_phase_4d_creative_rag_demo.py \
  --confirm-live \
  --knowledge-mode vector \
  --creative-provider openai \
  --creative-model "<available-chat-model>" \
  --embedding-model "<available-embedding-model>" \
  --knowledge-pack tiktok_car_cleaning_v1 \
  --knowledge-limit 6
```

## Running Tests

```bash
uv run python -m pytest -q
```

## Current Non-Goals

- no multi-agent system;
- no automated TikTok publishing;
- no complex platform or dashboard;
- no production deployment;
- no real creator scraping;
- no business API integration;
- no Script RAG;
- no Skills or Tool Calling;
- no ScriptDraft Knowledge Pack;
- no persistent vector database;
- no reranker;
- no hybrid retrieval;
- no query rewrite;
- no automatic knowledge generation;
- no automatic A/B winner selection;
- no copied `enrichment_agent` package from the reference project.

## Reference

This project studies architecture patterns from `langchain-ai/data-enrichment`, especially state layering, graph entry design, structured output concepts, conditional routing, budget controls, Studio debugging, and test layering. The new project does not depend on the reference repository at runtime and does not import its package.

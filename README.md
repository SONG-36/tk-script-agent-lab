# tk-script-agent-lab

`tk-script-agent-lab` is a learning-oriented TikTok Script Agent Lab for an AI product manager. The project is intentionally built in phases so each step can separate product thinking from model behavior, deterministic code, validation, and later agent orchestration.

## Current Phase

Current status: Phase 3A.

Phase 0 established the repository baseline, reference audit archive, learning roadmap, technology boundaries, Golden Case fixtures, and import/test scaffolding.

Phase 1A added deterministic domain contracts and cross-reference validation for the TikTok Script Agent Lab.

Phase 1B adds a fixture-backed Fake Provider and a deterministic two-stage workflow with a real human gate.

Phase 1C adds a LangGraph visualization and orchestration layer over the already validated workflow.

Phase 2A adds an optional real OpenAI provider for `CreativeIdea` generation only. The default remains Fake Provider mode, so the project can run and test without an API key or model cost.

Phase 2B adds an optional real OpenAI provider for `ScriptDraft` generation after a human approves a creative idea.

Phase 3A adds static Creative Knowledge Pack injection and Control / Treatment A/B comparison for creative idea generation.

There is still no real Agent in this phase. There are no tools, RAG, Skills, Tool Calling, TikTok API integrations, scraping integrations, second review interrupt, or production services.

## Learning Goal

The project is designed to help understand:

- data flow between user input, internal state, and output;
- model boundaries and where LLMs should not make decisions;
- deterministic code responsibilities;
- likely points where a system can fabricate, overclaim, or hide uncertainty;
- validation methods before and after model usage;
- staged evaluation of script quality and factual safety.

## Phase Model

The lab evolves one phase at a time. Phase 3A adds only static Creative Knowledge guidance before creative idea generation. Later phases may introduce minimal RAG, tool calling, and eval loops, but none of those are implemented yet.

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
- no RAG, Skills, Tool Calling, or vector database;
- no ScriptDraft Knowledge Pack;
- no embeddings;
- no vector database;
- no semantic retrieval;
- no reranker;
- no automatic knowledge generation;
- no automatic A/B winner selection;
- no copied `enrichment_agent` package from the reference project.

## Reference

This project studies architecture patterns from `langchain-ai/data-enrichment`, especially state layering, graph entry design, structured output concepts, conditional routing, budget controls, Studio debugging, and test layering. The new project does not depend on the reference repository at runtime and does not import its package.

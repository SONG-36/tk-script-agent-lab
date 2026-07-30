# tk-script-agent-lab

`tk-script-agent-lab` is a learning-oriented TikTok Script Agent Lab for an AI product manager. The project is intentionally built in phases so each step can separate product thinking from model behavior, deterministic code, validation, and later agent orchestration.

## Current Phase

Current status: Phase 1C.

Phase 0 established the repository baseline, reference audit archive, learning roadmap, technology boundaries, Golden Case fixtures, and import/test scaffolding.

Phase 1A added deterministic domain contracts and cross-reference validation for the TikTok Script Agent Lab.

Phase 1B adds a fixture-backed Fake Provider and a deterministic two-stage workflow with a real human gate.

Phase 1C adds a LangGraph visualization and orchestration layer over the already validated workflow.

There is still no real Agent in this phase. There are no model calls, tools, RAG, LangGraph workflows, TikTok API integrations, scraping integrations, or production services.

## Learning Goal

The project is designed to help understand:

- data flow between user input, internal state, and output;
- model boundaries and where LLMs should not make decisions;
- deterministic code responsibilities;
- likely points where a system can fabricate, overclaim, or hide uncertainty;
- validation methods before and after model usage;
- staged evaluation of script quality and factual safety.

## Phase Model

The lab evolves one phase at a time. Phase 1C runs the same deterministic chain through LangGraph. Later phases may introduce real LLM usage, minimal RAG, tool calling, and eval loops, but none of those are implemented yet.

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
- no copied `enrichment_agent` package from the reference project.

## Reference

This project studies architecture patterns from `langchain-ai/data-enrichment`, especially state layering, graph entry design, structured output concepts, conditional routing, budget controls, Studio debugging, and test layering. The new project does not depend on the reference repository at runtime and does not import its package.

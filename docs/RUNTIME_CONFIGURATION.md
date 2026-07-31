# Runtime Configuration

Phase 4D supports independent creative idea and script draft generation modes plus optional Creative Knowledge injection through off, static, or vector modes.

## Graph Configuration

These values are passed through LangGraph context or Studio Config.

| Name | Required | Default | Purpose |
|---|---:|---|---|
| `creative_provider` | No | `fake` | Selects `fake` or `openai` creative idea generation. |
| `creative_model` | OpenAI mode only | `null` | OpenAI model name available to the current account. |
| `creative_prompt_version` | No | `creative_idea_v1` | Prompt version used for OpenAI creative idea generation. |
| `script_provider` | No | `fake` | Selects `fake` or `openai` script draft generation. |
| `script_model` | OpenAI script mode only | `null` | OpenAI model name available for script generation. |
| `script_prompt_version` | No | `script_draft_v1` | Prompt version used for OpenAI script draft generation. |
| `knowledge_mode` | No | `off` | Selects `off`, `static`, or `vector` Creative Knowledge mode. |
| `creative_knowledge_pack` | Static/vector mode only | `null` | Registered Creative Knowledge Pack id, such as `tiktok_car_cleaning_v1`. |
| `creative_knowledge_limit` | No | `6` | Maximum selected Creative Knowledge items. |
| `knowledge_selector_version` | No | `static_selector_v1` | Deterministic selector version recorded in `KnowledgeSelectionRecord`. |
| `creative_embedding_model` | Vector mode only | `null` | OpenAI embedding model for Creative RAG. Do not use `OPENAI_MODEL` as a fallback. |
| `creative_retrieval_query_version` | No | `creative_retrieval_query_v1` | Deterministic Creative retrieval query version. |
| `creative_vector_retriever_version` | No | `vector_retriever_v1` | Vector retriever version recorded in trace output. |

`OPENAI_API_KEY` is not a graph configuration field and must not be placed in Studio Input, Graph State, logs, or exported workflow results.

## Environment Variables

These values are read from the shell environment.

| Name | Required | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | OpenAI mode only | API key used by `OpenAICreativeProvider`. |
| `OPENAI_MODEL` | Demo scripts only | Default model name consumed by Phase 2A and Phase 2B demo scripts. |
| `OPENAI_EMBEDDING_MODEL` | Vector demo scripts only | Default embedding model for Phase 4C/4D vector demos. |

Use placeholders in documentation and committed files. Do not commit real secrets.

## Fake Mode

Fake mode is the default. It does not require `OPENAI_API_KEY`, does not initialize `ChatOpenAI`, and keeps the fixture-backed flow available.

Studio Config:

```yaml
creative_provider: fake
creative_model: null
creative_prompt_version: creative_idea_v1
script_provider: fake
script_model: null
script_prompt_version: script_draft_v1
knowledge_mode: off
creative_knowledge_pack: null
creative_knowledge_limit: 6
knowledge_selector_version: static_selector_v1
```

Shell:

```bash
uv run langgraph dev
```

## Fake Creative And OpenAI Script

This mode isolates real script generation after a fixture creative idea is approved.

Shell:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
export OPENAI_MODEL="<available-model-name>"
uv run python scripts/run_phase_2b_openai_script_demo.py \
  --creative-provider fake \
  --script-provider openai \
  --selected-idea-id idea_before_after_cleanup \
  --reviewer phase-2b-reviewer
```

Studio Config:

```yaml
creative_provider: fake
creative_model: null
creative_prompt_version: creative_idea_v1
script_provider: openai
script_model: <available-model-name>
script_prompt_version: script_draft_v1
knowledge_mode: off
creative_knowledge_pack: null
creative_knowledge_limit: 6
knowledge_selector_version: static_selector_v1
```

## OpenAI Creative Only

This mode replaces only `CreativeIdea` generation. `ReferenceInsight` remains manual, and `ScriptDraft` remains fixture-backed.

Shell:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
export OPENAI_MODEL="<available-model-name>"
uv run python scripts/run_phase_2a_openai_demo.py
```

LangGraph Studio:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
uv run langgraph dev
```

Studio Config:

```yaml
creative_provider: openai
creative_model: <available-model-name>
creative_prompt_version: creative_idea_v1
script_provider: fake
script_model: null
script_prompt_version: script_draft_v1
knowledge_mode: off
creative_knowledge_pack: null
creative_knowledge_limit: 6
knowledge_selector_version: static_selector_v1
```

## Full OpenAI Creative And Script

This mode performs both real creative idea and real script draft generation. Creative selection remains a human decision.

Studio Config:

```yaml
creative_provider: openai
creative_model: <available-model-name>
creative_prompt_version: creative_idea_v1
script_provider: openai
script_model: <available-model-name>
script_prompt_version: script_draft_v1
knowledge_mode: off
creative_knowledge_pack: null
creative_knowledge_limit: 6
knowledge_selector_version: static_selector_v1
```

Studio Input should continue to use:

```text
data/golden_cases/car_vacuum_v1/studio_input.json
```

## Local Secret Files

`.env.example` is intentionally commit-safe and contains only empty placeholders.

The following local-only files are ignored by git:

```text
.env
.env.local
.env.*
!.env.example
LOCAL_SECRETS_NOTES.md
```

Do not create real secret files as part of Phase 3A implementation work.

## Phase 3A Creative Knowledge Modes

Phase 3A knowledge only affects `CreativeIdea` generation. It does not inject knowledge into `ScriptDraft`.

Knowledge is creative guidance, not business evidence. Product facts, selling points, and reference insights remain the only allowed source types in `SourceUsage`.

### Control

Control uses `creative_idea_v2` with knowledge disabled.

Studio Config:

```json
{
  "creative_provider": "openai",
  "creative_model": "<OPENAI_MODEL>",
  "creative_prompt_version": "creative_idea_v2",
  "script_provider": "fake",
  "script_model": null,
  "script_prompt_version": "script_draft_v1",
  "knowledge_mode": "off",
  "creative_knowledge_pack": null,
  "creative_knowledge_limit": 6,
  "knowledge_selector_version": "static_selector_v1"
}
```

Shell:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
export OPENAI_MODEL="<available-model-name>"
uv run langgraph dev
```

### Treatment

Treatment uses the same model and prompt version with static Creative Knowledge enabled.

Studio Config:

```json
{
  "creative_provider": "openai",
  "creative_model": "<OPENAI_MODEL>",
  "creative_prompt_version": "creative_idea_v2",
  "script_provider": "fake",
  "script_model": null,
  "script_prompt_version": "script_draft_v1",
  "knowledge_mode": "static",
  "creative_knowledge_pack": "tiktok_car_cleaning_v1",
  "creative_knowledge_limit": 6,
  "knowledge_selector_version": "static_selector_v1"
}
```

Shell:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
export OPENAI_MODEL="<available-model-name>"
uv run python scripts/run_phase_3a_creative_ab_demo.py
```

Studio Input should continue to use:

```text
data/golden_cases/car_vacuum_v1/studio_input.json
```

Expected Studio observations:

- `select_creative_knowledge`;
- `KnowledgeSelectionRecord`;
- selected knowledge IDs in Treatment;
- no selected knowledge IDs in Control;
- `generate_creative_ideas`;
- `human_select_idea` interrupt.

`.env.example` is commit-safe and contains only placeholders. Do not create or commit `.env` for Phase 3A work.

## Phase 4D Studio Config

API keys are read only from the Mac mini process environment. Ordinary product
changes should stay in Studio Input.

### Off

```json
{
  "knowledge_mode": "off",
  "creative_knowledge_pack": null,
  "creative_knowledge_limit": 6,
  "creative_provider": "openai",
  "creative_model": "<available-chat-model>",
  "creative_prompt_version": "creative_idea_v2"
}
```

### Static

```json
{
  "knowledge_mode": "static",
  "creative_knowledge_pack": "tiktok_car_cleaning_v1",
  "creative_knowledge_limit": 6,
  "creative_provider": "openai",
  "creative_model": "<available-chat-model>",
  "creative_prompt_version": "creative_idea_v2"
}
```

### Vector

```json
{
  "knowledge_mode": "vector",
  "creative_knowledge_pack": "tiktok_car_cleaning_v1",
  "creative_knowledge_limit": 6,
  "creative_embedding_model": "<available-embedding-model>",
  "creative_retrieval_query_version": "creative_retrieval_query_v1",
  "creative_vector_retriever_version": "vector_retriever_v1",
  "creative_provider": "openai",
  "creative_model": "<available-chat-model>",
  "creative_prompt_version": "creative_idea_v2"
}
```

Vector mode builds a process-local in-memory Qdrant runtime. It is not a
production persistent index lifecycle.

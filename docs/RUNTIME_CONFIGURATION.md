# Runtime Configuration

Phase 2B supports independent creative idea and script draft generation modes.

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

`OPENAI_API_KEY` is not a graph configuration field and must not be placed in Studio Input, Graph State, logs, or exported workflow results.

## Environment Variables

These values are read from the shell environment.

| Name | Required | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | OpenAI mode only | API key used by `OpenAICreativeProvider`. |
| `OPENAI_MODEL` | Demo scripts only | Default model name consumed by Phase 2A and Phase 2B demo scripts. |

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

Do not create real secret files as part of Phase 2B implementation work.

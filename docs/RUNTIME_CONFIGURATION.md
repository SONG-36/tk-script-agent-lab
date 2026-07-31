# Runtime Configuration

Phase 2A supports two creative idea generation modes: `fake` and `openai`.

## Graph Configuration

These values are passed through LangGraph context or Studio Config.

| Name | Required | Default | Purpose |
|---|---:|---|---|
| `creative_provider` | No | `fake` | Selects `fake` or `openai` creative idea generation. |
| `creative_model` | OpenAI mode only | `null` | OpenAI model name available to the current account. |
| `creative_prompt_version` | No | `creative_idea_v1` | Prompt version used for OpenAI creative idea generation. |

`OPENAI_API_KEY` is not a graph configuration field and must not be placed in Studio Input, Graph State, logs, or exported workflow results.

## Environment Variables

These values are read from the shell environment.

| Name | Required | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | OpenAI mode only | API key used by `OpenAICreativeProvider`. |
| `OPENAI_MODEL` | Demo script only | Model name consumed by `scripts/run_phase_2a_openai_demo.py`. |

Use placeholders in documentation and committed files. Do not commit real secrets.

## Fake Mode

Fake mode is the default. It does not require `OPENAI_API_KEY`, does not initialize `ChatOpenAI`, and keeps the Phase 1C fixture-backed flow available.

Studio Config:

```yaml
creative_provider: fake
creative_model: null
creative_prompt_version: creative_idea_v1
```

Shell:

```bash
uv run langgraph dev
```

## OpenAI Mode

OpenAI mode replaces only `CreativeIdea` generation. `ReferenceInsight` remains manual, and `ScriptDraft` remains fixture-backed in Phase 2A.

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

Do not create real secret files as part of Phase 2A implementation work.

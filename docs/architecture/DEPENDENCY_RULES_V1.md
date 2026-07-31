# Dependency Rules V1

These rules freeze allowed dependency direction for Framework Baseline V1.

## Allowed

- `domain` may depend on Python standard library and Pydantic.
- `workflow` may depend on `domain` and provider ports used by the deterministic workflow.
- `providers` may depend on `domain`, provider contracts, prompt builders, and external model SDK adapters.
- `knowledge.contracts` may depend on `domain.ValidationError` and Pydantic.
- `knowledge.static_retriever` may depend on knowledge loader and selector.
- `langgraph_app` may depend on `domain`, `workflow`, `providers`, `knowledge`, and LangGraph.
- `scripts` and `tests` may depend on `src`.

## Forbidden

- `domain` must not import LangGraph, OpenAI, PyYAML, providers, prompts, scripts, or tests.
- `knowledge.contracts` must not import LangGraph, OpenAI, PyYAML, prompts, scripts, or tests.
- `providers` must not import `langgraph_app`, scripts, or tests.
- `src/tk_script_agent_lab` must not import scripts, tests, or docs.
- Core runtime must not depend on Golden Case fixtures except the existing Fake Provider helper inside Graph nodes.

## Examples

Allowed:

```python
from tk_script_agent_lab.knowledge.contracts import RetrievalRequest
from tk_script_agent_lab.knowledge.static_retriever import StaticKnowledgeRetriever
```

Forbidden:

```python
from scripts.run_phase_3a_creative_ab_demo import _summarize
from tk_script_agent_lab.langgraph_app.graph import graph  # inside provider modules
```

## Test Evidence

`tests/architecture_tests/test_dependency_rules.py` uses Python AST parsing to inspect imports without importing application modules. It verifies:

- domain has no framework or adapter imports;
- knowledge contracts have no runtime adapter imports;
- providers do not import Graph, scripts, or tests;
- src does not import scripts, tests, or docs.

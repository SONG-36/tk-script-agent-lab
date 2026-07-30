# Technology Purpose

Technology should be added only when it serves the current phase.

| Technology | Current Business Required | Learning Required | When To Add |
|---|---:|---:|---|
| Pydantic | Yes | Yes | Phase 1A |
| LLM Provider | Yes | Yes | Phase 2 |
| RAG | No | Yes | Phase 3 |
| LangGraph | No | Yes | Phase 4 |
| Tool Calling | No | Yes | Phase 5 |
| Multi-Agent | No | No | Not planned |

## Phase 0 Boundary

Phase 0 uses only Python packaging and pytest. It records why later technologies may matter, but does not install or implement them.

## Phase 1A Pydantic Boundary

Pydantic is introduced in Phase 1A for fixed schema validation and single-object business constraints. It checks types, required fields, enum values, local list rules, and status-dependent rules such as verified facts requiring a source.

Pydantic does not prove factual correctness. A syntactically valid fact can still be false, outdated, or unsupported.

Cross-object integrity is handled by deterministic validation code in `validate_domain_dataset()`, not by a model and not by Pydantic side effects.

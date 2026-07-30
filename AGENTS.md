# AGENTS.md

Rules for Codex and other coding agents working in this repository:

- Implement only one phase at a time.
- Do not enter a later phase early.
- Do not add technology stack components unless the current phase requires them.
- Do not hand deterministic business rules to a model.
- Do not automatically commit or push.
- Run tests after modifications.
- Do not refactor unrelated files opportunistically.
- Do not weaken existing test assertions.
- Do not import `enrichment_agent`.
- Do not depend on local paths from the reference repository.
- Do not add Agent, RAG, LangGraph, model SDK, tool calling, API, scraping, service, or database code during Phase 0 or Phase 1A.

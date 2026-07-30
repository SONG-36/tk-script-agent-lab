# Decision Log

## 2026-07-29: Phase 0 Only

Decision: initialize `tk-script-agent-lab` as a learning baseline, not as a working TikTok Agent.

Reason: the project should first make data flow, model boundaries, deterministic validation, and failure modes visible before introducing model calls or orchestration frameworks.

## 2026-07-29: Reference Project Is Documentation Only

Decision: copy only the three reference audit reports into `docs/reference_audit/`.

Reason: the reference project contains useful architecture patterns, but its web research business logic, Tavily usage, dynamic schema, prompts, and `enrichment_agent` package do not fit this project boundary.

## 2026-07-29: No Model Or Graph Dependencies In Phase 0

Decision: do not add LangGraph, LangChain, OpenAI SDK, Anthropic SDK, Tavily, RAG, embedding, vector database, Streamlit, FastAPI, Docker, TikTok API, or scraping APIs.

Reason: Phase 0 is a repository and learning baseline. Adding runtime AI infrastructure now would blur what is deterministic code versus model behavior.

## 2026-07-29: Phase 1A Fixed Domain Schemas

Decision: Phase 1A uses fixed Pydantic domain schemas and explicit cross-reference validation instead of user-defined dynamic schemas.

Reason: fixed business boundaries are easier to test, prevent arbitrary schema injection, and keep the distinction clear between format validity and factual truth.

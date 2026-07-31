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

## 2026-07-30: Phase 1B Fixture-Backed Fake Provider

Decision: Phase 1B uses fixture-backed Fake Provider before integrating a real LLM.

Reason: this gives stable tests, separates model problems from workflow problems, makes Provider input/output contracts explicit, and avoids API cost and non-determinism.

## 2026-07-30: Human Gate Before Script Generation

Decision: idea selection is an explicit human review gate and script generation cannot occur before approval.

Reason: humans keep final creative selection authority, the workflow does not let a model decide for the user, and the state semantics are ready for a future interrupt/resume implementation.

## 2026-07-30: Phase 1C LangGraph Layer

Decision: Phase 1C introduces LangGraph as a visualization and orchestration layer over the already validated Phase 1B workflow.

Reason: this avoids depending on Graph before the business chain is proven, avoids duplicating orchestration mechanics, teaches State/Node/Edge/Interrupt, and keeps business rules separate from the framework.

## 2026-07-30: Manual Reference Insights In Phase 1C

Decision: Reference insights are manually supplied in Phase 1C.

Reason: this validates Graph and the business chain first. Reference video analysis standards can be explored later through knowledge base, Skills, or real model experiments without hard-coding immature analysis rules now.

## 2026-07-30: Phase 2A Replaces Only CreativeIdea Generation

Decision: Phase 2A replaces only `CreativeIdea` generation with a real OpenAI model.

Reason: one model boundary is easier to observe, debug, and evaluate at a time. The workflow continues to reuse manual `ReferenceInsight`, deterministic validators, the human gate, and Fake Provider script fixtures, which keeps cost and non-determinism controlled.

## 2026-07-30: Model-Generated Identities Are Not Trusted

Decision: model output is limited to semantic candidate content, and official `CreativeIdea` IDs, `SourceUsage` IDs, `product_id`, ordering, and validation errors are produced by deterministic code.

Reason: model-generated IDs can be duplicate, unstable, invalid, or inconsistent with the domain graph. Deterministic mapping keeps cross-object references auditable and repeatable.

## 2026-07-31: Phase 2B Replaces Only ScriptDraft Generation

Decision: Phase 2B replaces only `ScriptDraft` generation with an optional OpenAI provider.

Reason: this keeps one model boundary under test at a time. Fake Creative + OpenAI Script can isolate script generation, while the human gate ensures the script model only receives an approved creative idea.

## 2026-07-31: Script And Scene Identities Are Deterministic

Decision: model output is limited to script semantic content, scenes, and source usage candidates. Official `script_id`, `scene_id`, scene sequence, `product_id`, `creative_idea_id`, and `source_usage_id` are produced by deterministic code.

Reason: script and scene identities must be stable, auditable, and bound to the approved creative idea. The model is not trusted to create durable IDs or cross-object relationships.

## 2026-07-31: Phase 3A Uses Static Creative Knowledge Selection

Decision: Phase 3A uses deterministic static knowledge selection before introducing RAG.

Reason: the knowledge set is small, selection must be explainable, and the team should first validate whether the knowledge itself improves creative output before adding embeddings or a vector database. This keeps the A/B comparison controlled: Control and Treatment both use `creative_idea_v2`, and the only intended difference is `knowledge_mode`.

## 2026-07-31: Creative Guidance Is Not Business Evidence

Decision: Creative Knowledge can guide expression, structure, shootability, and claim-safety discipline, but it cannot be cited as `SourceUsage`.

Reason: ProductFact, SellingPoint, and ReferenceInsight remain the only allowed business evidence sources. Knowledge IDs entering `SourceUsage` would make creative hypotheses look like factual proof.

## 2026-07-31: Framework Baseline V1 Freezes Dependency Direction

Decision: freeze Framework Baseline V1 before vector RAG.

Reason: Phase 3A increased the number of moving parts, and future RAG will add more infrastructure. Freezing dependency direction now reduces the risk that Graph, Provider, Prompt, and Retriever layers contaminate each other.

## 2026-07-31: Knowledge Retrieval Is A Port

Decision: knowledge retrieval is represented by `KnowledgeRetriever`, not by OpenAI providers.

Reason: retrieval must be observable and replaceable. Static and future vector retrieval should share a contract, while providers remain responsible only for generation and provider-boundary validation.

## 2026-07-31: Static Knowledge Remains Supported After Vector RAG

Decision: static knowledge remains a supported retriever implementation even after vector retrieval is introduced later.

Reason: static retrieval is zero-cost, deterministic, useful for regression tests, and appropriate for small curated knowledge sets.

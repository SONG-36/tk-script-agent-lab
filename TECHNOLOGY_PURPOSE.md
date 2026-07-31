# Technology Purpose

Technology should be added only when it serves the current phase.

| Technology | Current Business Required | Learning Required | When To Add |
|---|---:|---:|---|
| Pydantic | Yes | Yes | Phase 1A |
| LLM Provider | Yes | Yes | Phase 2 |
| RAG | No | Yes | Phase 3 |
| LangGraph | Yes | Yes | Phase 1C |
| langchain-openai | Yes | Yes | Phase 2A |
| Tool Calling | No | Yes | Phase 5 |
| Multi-Agent | No | No | Not planned |

## Phase 0 Boundary

Phase 0 uses only Python packaging and pytest. It records why later technologies may matter, but does not install or implement them.

## Phase 1A Pydantic Boundary

Pydantic is introduced in Phase 1A for fixed schema validation and single-object business constraints. It checks types, required fields, enum values, local list rules, and status-dependent rules such as verified facts requiring a source.

Pydantic does not prove factual correctness. A syntactically valid fact can still be false, outdated, or unsupported.

Cross-object integrity is handled by deterministic validation code in `validate_domain_dataset()`, not by a model and not by Pydantic side effects.

## Phase 1B Fake Provider Boundary

The Fake Provider is a model boundary substitute. It returns fixed fixtures so tests can prove the workflow before any real LLM is connected.

The Fake Provider is not responsible for real generation, fact discovery, planning, ranking, or automatic repair. Its outputs still pass through Pydantic and deterministic cross-reference validation.

The deterministic Workflow proves the business chain first: input validation, provider output validation, explicit human selection, script validation, and export.

The Human Gate is an explicit business state. Script generation cannot happen until a review approves a specific creative idea.

LangGraph is still not included. The current goal is to prove the chain in ordinary Python before introducing graph orchestration.

## Phase 1C LangGraph Boundary

LangGraph is introduced in Phase 1C for State, Node, Edge, Interrupt, Resume, and Studio visualization.

LangGraph does not prove business facts, product truth, source validity, or script safety. The deterministic domain validator still owns those rules.

LangGraph Studio is a development and debugging interface, not the formal product UI.

ReferenceInsight is manually supplied in Phase 1C. Fake Provider still only supplies CreativeIdea and ScriptDraft fixtures.

## Phase 2A OpenAI Creative Boundary

`langchain-openai` is introduced in Phase 2A only for OpenAI `CreativeIdea` semantic generation. It is not a general provider registry, agent layer, tool layer, or script generation system.

OpenAI receives only the constrained prompt context built by deterministic code: product profile, verified facts, selling points, manually supplied reference insights, prohibited claims, requested idea count, and allowed source IDs. `UNVERIFIED` and `REJECTED` fact values are not made available as usable facts.

Pydantic structured output defines the model response shape. Structured output proves that the response fits the requested schema; it does not prove that the creative claim is true, compliant, or source-safe.

The deterministic validator still owns source and fact rules. It checks source IDs, product references, output count, duplicate ideas, domain object construction, and whether the graph may continue to the human gate.

LangGraph owns orchestration: selecting Fake or OpenAI mode from configuration, writing generated ideas into state, routing failures to `END`, and interrupting for human review.

The Human Gate owns the creative decision. The model does not auto-select, auto-approve, auto-review, or generate a fallback script.

## Phase 2B OpenAI Script Boundary

OpenAI Script Provider is introduced in Phase 2B only for `ScriptDraft` semantic generation after a human approves one `CreativeIdea`.

OpenAI Creative Provider owns optional creative idea generation. OpenAI Script Provider owns optional script generation. The two providers are configured independently so each model boundary can be tested alone.

LangGraph owns orchestration: routing through validation, interrupting for human choice, and invoking script generation only after `APPROVED`.

Pydantic owns structured output shape for script candidates and scenes. Deterministic code owns script IDs, scene IDs, sequence numbers, product binding, selected creative idea binding, source usage IDs, and validation errors.

The validator owns explicit ID, source, product, selected idea, and verified fact boundaries. A model-generated script can still be low quality or contain subtle unsupported natural language; structured output and validation do not prove creative quality or absolute factual truth.

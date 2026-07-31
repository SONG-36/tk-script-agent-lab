# Technology Purpose

Technology should be added only when it serves the current phase.

| Technology | Current Business Required | Learning Required | When To Add |
|---|---:|---:|---|
| Pydantic | Yes | Yes | Phase 1A |
| LLM Provider | Yes | Yes | Phase 2 |
| RAG | No | Yes | Phase 3 |
| LangGraph | Yes | Yes | Phase 1C |
| langchain-openai | Yes | Yes | Phase 2A |
| YAML | Yes | Yes | Phase 3A |
| Static Selector | Yes | Yes | Phase 3A |
| A/B Rubric | Yes | Yes | Phase 3A |
| DeterministicParagraphChunker | Yes | Yes | Phase 4A |
| KnowledgeIngestor | Yes | Yes | Phase 4A |
| Provenance | Yes | Yes | Phase 4A |
| Stable hashing | Yes | Yes | Phase 4A |
| Tokenizer | No | Later | Not used in Phase 4A |
| Embedding | No | Later | Not used in Phase 4A |
| Vector database | No | Later | Not used in Phase 4A |
| InMemoryKnowledgeIndex | Yes | Yes | Phase 4B |
| ExactMetadataKnowledgeRetriever | Yes | Yes | Phase 4B |
| RetrievalEvaluator | Yes | Yes | Phase 4B |
| OpenAI Embeddings | Yes | Yes | Phase 4C |
| Qdrant Local | Yes | Yes | Phase 4C |
| VectorKnowledgeRetriever | Yes | Yes | Phase 4C |
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

## Phase 3A Static Creative Knowledge Boundary

YAML is introduced as a human-readable carrier for a small Creative Knowledge Pack.

Pydantic validates pack shape, item status, provenance, applicability, and stable selection records.

The Static Selector is deterministic and transparent. It selects active creative-stage items by target market, product category, priority, and limit. It does not call a model and does not perform semantic retrieval.

LangGraph adds one deterministic node, `select_creative_knowledge`, before `generate_creative_ideas`.

OpenAI creative generation can read selected knowledge in `creative_idea_v2`, but knowledge remains creative guidance only. It is not ProductFact, SellingPoint, ReferenceInsight, or SourceUsage evidence.

The A/B Rubric supports human review of Control and Treatment outputs. One run is not proof of long-term improvement.

There is still no embedding, vector store, top-k retrieval, reranker, retrieval service, ScriptDraft knowledge injection, or RAG pipeline in Phase 3A.

## Phase 4A RAG Ingestion Boundary

Pydantic is used for ingestion contracts and validation: `DocumentSource`, `KnowledgeDocument`, `KnowledgeChunk`, `ChunkingRequest`, `IngestionRequest`, `IngestionTrace`, and `IngestionResult`.

`DeterministicParagraphChunker` provides a reproducible chunking baseline before any token-aware or semantic chunking exists.

`KnowledgeIngestor` prepares local knowledge offline. It receives already constructed documents, calls a chunker, preserves provenance and evidence status, and returns structured ingestion traces and errors.

Provenance records where knowledge came from and what evidence status it has. It does not make knowledge a `ProductFact` or `SourceUsage`.

Stable hashing is used for deterministic chunk and ingestion request IDs. Phase 4A does not use random UUIDs or current time for these IDs.

Phase 4A has no model calls. It does not use a tokenizer, embedding model, vector database, semantic retrieval, or model-based chunking.

## Phase 4B Exact Retrieval Boundary

`InMemoryKnowledgeIndex` is introduced as a zero-cost, process-local index for
`KnowledgeChunk` snapshots. It proves build, duplicate handling, snapshot, and
retrieval contracts before any vector store exists.

`ExactMetadataKnowledgeRetriever` implements deterministic metadata filtering
and exact query matching. Metadata filters run before scoring so wrong stage,
market, category, or date-window chunks cannot become candidates.

`RetrievalEvaluator` checks expected IDs, forbidden IDs, recall, and top ID. It
does not judge creative quality or use an LLM judge.

Phase 4B has no model calls. It does not use embeddings, a vector database,
semantic retrieval, reranking, query rewriting, or prompt injection.

## Phase 4C Vector Retrieval Boundary

OpenAI Embeddings are introduced only for text-to-vector conversion. The
embedding provider does not retrieve knowledge, write prompts, call LangGraph,
or make creative/script decisions.

Qdrant Local is introduced in in-memory mode only. It verifies real vector store
semantics without Docker, remote Qdrant, persistence, or database operations.

`VectorKnowledgeRetriever` converts a `RetrievalRequest` into one query
embedding call, delegates vector search to Qdrant, resolves chunk citations, and
returns `RetrievalResult` V1.

Phase 4C does not use Chat Completions, rerankers, hybrid search, query rewrite,
Prompt Grounding, or LangGraph retrieval nodes.

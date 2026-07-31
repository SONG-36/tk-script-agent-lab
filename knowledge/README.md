# Knowledge Packs

Phase 3A introduces a small static Creative Knowledge Pack.

This directory is not a vector database, retrieval service, embedding cache, or RAG pipeline. Knowledge packs are human-readable YAML files selected by deterministic code before creative idea generation.

Current pack:

- `creative/tiktok_car_cleaning_v1.yaml`

Creative Knowledge is guidance for expression, structure, shootability, and claim safety. It is not product evidence, not a ProductFact, not an official TikTok policy source, and must not appear in `CreativeIdea.source_usages`.

Selection is controlled by `GraphConfiguration`:

- `knowledge_mode="off"` keeps Phase 2 behavior and selects no items.
- `knowledge_mode="static"` loads a named pack and applies the static selector.

The selector uses active status, stage, target market, product category, priority, and limit. It does not call a model and does not perform semantic retrieval.

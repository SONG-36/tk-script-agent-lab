# Creative RAG Grounding V1

Phase 4D injects retrieved Creative Guidance into `creative_idea_v2`.

## Business Evidence

Only these sources may become `CreativeIdea.source_usages`:

- verified `ProductFact`;
- `SellingPoint`;
- manual `ReferenceInsight`.

## Creative Guidance

Static and vector retrieved knowledge may guide:

- hooks;
- creative angles;
- shootability;
- structure;
- expression;
- risk reminders.

Creative Guidance must not become:

- `ProductFact`;
- `SellingPoint`;
- `ReferenceInsight`;
- `SourceUsage`;
- official TikTok policy without an official source.

Vector similarity is not fact strength. A high score only means the retrieved
chunk is similar to the deterministic retrieval query.

## Prompt Boundary

`creative_idea_v2` keeps `BUSINESS EVIDENCE` and `CREATIVE GUIDANCE` separate.
Allowed `source_usages` are derived only from Business Evidence. Knowledge IDs,
chunk IDs, Qdrant IDs, and retrieval scores are not allowed business source IDs.

from datetime import date

from tk_script_agent_lab.knowledge.ingestion_contracts import DocumentSource, KnowledgeChunk


def chunk(
    chunk_id: str = "kc_us_car_creative",
    *,
    document_id: str = "doc_us_car_creative",
    sequence: int = 1,
    title: str = "Cup holder crumbs creative note",
    content: str = "Cup holder crumbs and seat seam debris are visible cleanup details.",
    target_markets: list[str] | None = None,
    product_categories: list[str] | None = None,
    task_stages: list[str] | None = None,
    effective_from: date | None = date(2026, 1, 1),
    effective_to: date | None = None,
    metadata: dict[str, str] | None = None,
) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        sequence=sequence,
        content=content,
        char_start=0,
        char_end=len(content),
        char_count=len(content),
        title=title,
        source=DocumentSource(
            source_id=f"src_{chunk_id}",
            source_type="manual_entry",
            source_reference=f"synthetic.{chunk_id}",
        ),
        document_version="v1",
        language="en",
        provenance_type="internal_working_rule",
        evidence_status="hypothesis",
        target_markets=target_markets or ["US"],
        product_categories=product_categories or ["car vacuum cleaner"],
        task_stages=task_stages or ["creative"],
        effective_from=effective_from,
        effective_to=effective_to,
        metadata=metadata or {"kind": "creative_note", "topic": "car_cleanup"},
    )

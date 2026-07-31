from hashlib import sha256
import json

from tk_script_agent_lab.knowledge.ingestion_contracts import DocumentSource, KnowledgeDocument
from tk_script_agent_lab.knowledge.models import CreativeKnowledgeItem, CreativeKnowledgePack

CREATIVE_PACK_SOURCE_REFERENCES = {
    "tiktok_car_cleaning_v1": "knowledge/creative/tiktok_car_cleaning_v1.yaml",
}


def creative_pack_to_documents(pack: CreativeKnowledgePack) -> list[KnowledgeDocument]:
    source_path = CREATIVE_PACK_SOURCE_REFERENCES.get(pack.pack_id)
    if source_path is None:
        raise ValueError("creative knowledge pack is not registered for document conversion")
    return [
        _document(pack, item, source_path)
        for item in pack.items
        if item.status == "active"
    ]


def _document(
    pack: CreativeKnowledgePack,
    item: CreativeKnowledgeItem,
    source_path: str,
) -> KnowledgeDocument:
    document_id = _stable_document_id(pack, item)
    return KnowledgeDocument(
        document_id=document_id,
        title=item.title,
        content=_content(item),
        source=DocumentSource(
            source_id=f"src_{document_id}",
            source_type="internal_file",
            source_reference=f"{source_path}#{item.knowledge_id}",
        ),
        version=pack.version,
        language="en",
        provenance_type=item.provenance_type,
        evidence_status=item.evidence_status,
        target_markets=list(item.applicability.target_markets),
        product_categories=list(item.applicability.product_categories),
        task_stages=["creative"],
        metadata={
            "pack_id": pack.pack_id,
            "pack_version": pack.version,
            "knowledge_id": item.knowledge_id,
            "kind": item.kind,
            "priority": str(item.priority),
            "status": item.status,
        },
    )


def _content(item: CreativeKnowledgeItem) -> str:
    sections = [f"Instruction: {item.instruction}"]
    if item.rationale:
        sections.append(f"Rationale: {item.rationale}")
    if item.positive_examples:
        sections.append("Positive examples: " + "; ".join(item.positive_examples))
    if item.anti_examples:
        sections.append("Anti examples: " + "; ".join(item.anti_examples))
    return "\n".join(sections)


def _stable_document_id(pack: CreativeKnowledgePack, item: CreativeKnowledgeItem) -> str:
    payload = {
        "pack_id": pack.pack_id,
        "pack_version": pack.version,
        "knowledge_id": item.knowledge_id,
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"kdoc_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"

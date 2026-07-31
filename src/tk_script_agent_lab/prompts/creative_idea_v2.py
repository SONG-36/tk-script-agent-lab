import json

from tk_script_agent_lab.providers.base import CreativeGenerationRequest
from tk_script_agent_lab.prompts.creative_idea_v1 import (
    build_creative_idea_context as build_business_evidence_context,
)

PROMPT_VERSION = "creative_idea_v2"

SYSTEM_INSTRUCTION = """You generate TikTok short-video creative idea candidates.
Use BUSINESS EVIDENCE for factual product claims and source_usages.
Use CREATIVE GUIDANCE only for expression, structure, shootability, and claim-safety discipline.
Creative guidance is not product fact evidence and is not official TikTok policy unless explicitly labeled as official policy.
Do not invent power, suction, runtime, noise, certification, price, discount, or performance data.
Do not create source IDs that are not listed in BUSINESS EVIDENCE allowed_source_ids.
Do not put creative knowledge IDs in source_usages.
Each idea must reference at least one product source: product_fact or selling_point.
Each idea must reference at least one reference_insight.
Do not copy reference video text verbatim.
Reference insights are only for structure, hook, scene, pacing, or format inspiration.
The ideas must be meaningfully different.
Return only data matching CreativeIdeaBatch. Do not output Markdown or explanatory text.
Do not claim the ideas are approved, compliant, or selected.
Do not choose a best idea."""


def build_creative_idea_context(request: CreativeGenerationRequest) -> dict[str, object]:
    business_evidence = build_business_evidence_context(request)
    creative_guidance = [
        {
            "knowledge_id": item.knowledge_id,
            "kind": item.kind,
            "title": item.title,
            "instruction": item.content,
            "rationale": item.metadata.get("rationale"),
            "positive_examples": _metadata_json_list(item.metadata.get("positive_examples")),
            "anti_examples": _metadata_json_list(item.metadata.get("anti_examples")),
            "provenance_type": item.provenance_type,
            "evidence_status": item.evidence_status,
            "boundary": "creative_guidance_only_not_business_evidence",
        }
        for item in request.creative_knowledge_items
    ]
    return {
        "business_evidence": business_evidence,
        "creative_guidance": creative_guidance,
        "constraints": business_evidence["constraints"],
        "knowledge_boundary": {
            "creative_guidance_can_shape": [
                "hook pattern",
                "idea diversity",
                "shootability",
                "claim safety",
                "creative structure",
            ],
            "creative_guidance_cannot_be_used_as": [
                "product_fact",
                "selling_point",
                "reference_insight",
                "SourceUsage",
                "official TikTok policy",
            ],
        },
    }


def build_creative_idea_prompt(request: CreativeGenerationRequest) -> str:
    context = build_creative_idea_context(request)
    return (
        "Generate exactly "
        f"{request.idea_count} CreativeIdeaCandidate items.\n\n"
        "BUSINESS EVIDENCE:\n"
        f"{json.dumps(context['business_evidence'], ensure_ascii=False, indent=2)}\n\n"
        "CREATIVE GUIDANCE:\n"
        f"{json.dumps(context['creative_guidance'], ensure_ascii=False, indent=2)}\n\n"
        "Use only BUSINESS EVIDENCE allowed_source_ids in source_usages.\n"
        "Do not put creative knowledge IDs in source_usages."
    )


def _metadata_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("creative guidance examples metadata must be a JSON string list")
    return parsed

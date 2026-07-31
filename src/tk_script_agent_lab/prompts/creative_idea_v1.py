import json

from tk_script_agent_lab.domain import (
    DomainDataset,
    ProductFact,
    ReferenceInsight,
    SellingPoint,
    validate_domain_dataset,
)
from tk_script_agent_lab.domain.enums import VerificationStatus
from tk_script_agent_lab.providers.base import CreativeGenerationRequest

PROMPT_VERSION = "creative_idea_v1"

SYSTEM_INSTRUCTION = """You generate TikTok short-video creative idea candidates.
Use only the provided verified product facts, selling points, and manual reference insights.
Do not invent power, suction, runtime, noise, certification, price, discount, or performance data.
Do not create source IDs that are not listed in allowed_source_ids.
Each idea must reference at least one product source: product_fact or selling_point.
Each idea must reference at least one reference_insight.
Do not copy reference video text verbatim.
Reference insights are only for structure, hook, scene, pacing, or format inspiration.
The ideas must be meaningfully different.
Return only data matching CreativeIdeaBatch. Do not output Markdown or explanatory text.
Do not claim the ideas are approved, compliant, or selected.
Do not choose a best idea."""


def build_creative_idea_context(request: CreativeGenerationRequest) -> dict[str, object]:
    _ensure_context_inputs_valid(request)

    verified_facts = [
        _fact_context(fact)
        for fact in request.product_facts
        if fact.status == VerificationStatus.VERIFIED
    ]
    selling_points = [
        {
            "selling_point_id": selling_point.selling_point_id,
            "title": selling_point.title,
            "description": selling_point.description,
            "fact_ids": selling_point.fact_ids,
            "target_pain_points": selling_point.target_pain_points,
            "priority": selling_point.priority,
        }
        for selling_point in request.selling_points
    ]
    reference_insights = [
        {
            "insight_id": insight.insight_id,
            "reference_video_id": insight.reference_video_id,
            "insight_type": insight.insight_type,
            "description": insight.description,
            "evidence_text": insight.evidence_text,
            "start_second": insight.start_second,
            "end_second": insight.end_second,
        }
        for insight in request.reference_insights
    ]
    allowed_source_ids = {
        "product_fact": [fact["fact_id"] for fact in verified_facts],
        "selling_point": [item["selling_point_id"] for item in selling_points],
        "reference_insight": [item["insight_id"] for item in reference_insights],
    }
    unavailable_fact_ids = [
        fact.fact_id
        for fact in request.product_facts
        if fact.status != VerificationStatus.VERIFIED
    ]
    return {
        "product": {
            "product_id": request.product_profile.product_id,
            "product_name": request.product_profile.product_name,
            "category": request.product_profile.category,
            "target_market": request.product_profile.target_market,
            "target_audiences": request.product_profile.target_audiences,
            "usage_scenarios": request.product_profile.usage_scenarios,
        },
        "verified_facts": verified_facts,
        "selling_points": selling_points,
        "reference_insights": reference_insights,
        "constraints": {
            "prohibited_claims": request.product_profile.prohibited_claims,
            "idea_count": request.idea_count,
            "allowed_source_types": [
                "product_fact",
                "selling_point",
                "reference_insight",
            ],
            "allowed_source_ids": allowed_source_ids,
            "unavailable_fact_ids": unavailable_fact_ids,
        },
    }


def build_creative_idea_prompt(request: CreativeGenerationRequest) -> str:
    context = build_creative_idea_context(request)
    return (
        "Generate exactly "
        f"{request.idea_count} CreativeIdeaCandidate items using this context:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}"
    )


def _fact_context(fact: ProductFact) -> dict[str, object]:
    return {
        "fact_id": fact.fact_id,
        "field_name": fact.field_name,
        "value": fact.value,
        "unit": fact.unit,
        "source_ids": fact.source_ids,
    }


def _ensure_context_inputs_valid(request: CreativeGenerationRequest) -> None:
    dataset = DomainDataset(
        product_profile=request.product_profile,
        product_facts=request.product_facts,
        selling_points=request.selling_points,
        reference_videos=[],
        reference_insights=request.reference_insights,
        creative_ideas=[],
        script_drafts=[],
        review_decisions=[],
    )
    errors = validate_domain_dataset(dataset)
    blocking_errors = [
        error
        for error in errors
        if error.code
        not in {
            "REFERENCE_VIDEO_NOT_FOUND",
        }
    ]
    if blocking_errors:
        raise ValueError(blocking_errors[0].code)

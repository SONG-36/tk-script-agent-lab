import json

from tk_script_agent_lab.domain import (
    DomainDataset,
    ProductFact,
    validate_domain_dataset,
)
from tk_script_agent_lab.domain.enums import VerificationStatus
from tk_script_agent_lab.providers.base import ScriptGenerationRequest

PROMPT_VERSION = "script_draft_v1"

SYSTEM_INSTRUCTION = """You generate TikTok short-video ScriptDraft candidates from an approved CreativeIdea.
Follow the selected CreativeIdea. Do not replace the creative theme or target audience.
Keep the opening hook consistent with the selected CreativeIdea.
Use only the provided verified product facts, selling points, and manual reference insights.
Do not invent suction, power, runtime, noise, efficiency percentages, rankings, sales, or user reviews.
Every factual product expression must map to a valid source_usage.
Reference insights are only for structure, hook, scene, pacing, or format inspiration.
Do not copy reference video text verbatim.
ScriptDraft must include ordered, shootable scenes.
Do not claim the script is approved, compliant, or ready to publish.
Return only data matching ScriptDraftCandidate. Do not output Markdown or explanatory text."""


def build_script_draft_context(request: ScriptGenerationRequest) -> dict[str, object]:
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
    selected_idea = request.selected_idea
    return {
        "product": {
            "product_id": request.product_profile.product_id,
            "product_name": request.product_profile.product_name,
            "category": request.product_profile.category,
            "target_market": request.product_profile.target_market,
            "target_audiences": request.product_profile.target_audiences,
            "usage_scenarios": request.product_profile.usage_scenarios,
            "prohibited_claims": request.product_profile.prohibited_claims,
        },
        "verified_facts": verified_facts,
        "selling_points": selling_points,
        "reference_insights": reference_insights,
        "approved_creative_idea": {
            "creative_idea_id": selected_idea.creative_idea_id,
            "title": selected_idea.title,
            "hook": selected_idea.hook,
            "concept_summary": selected_idea.concept_summary,
            "target_audience": selected_idea.target_audience,
            "source_usages": [
                usage.model_dump(mode="json")
                for usage in selected_idea.source_usages
            ],
            "risk_notes": selected_idea.risk_notes,
        },
        "constraints": {
            "must_follow_selected_creative_idea": True,
            "do_not_change_target_audience": True,
            "prohibited_claims": request.product_profile.prohibited_claims,
            "allowed_source_types": [
                "product_fact",
                "selling_point",
                "reference_insight",
            ],
            "allowed_source_ids": allowed_source_ids,
            "unavailable_fact_ids": unavailable_fact_ids,
        },
    }


def build_script_draft_prompt(request: ScriptGenerationRequest) -> str:
    context = build_script_draft_context(request)
    return (
        "Generate one ScriptDraftCandidate for the approved CreativeIdea using this context:\n"
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


def _ensure_context_inputs_valid(request: ScriptGenerationRequest) -> None:
    dataset = DomainDataset(
        product_profile=request.product_profile,
        product_facts=request.product_facts,
        selling_points=request.selling_points,
        reference_videos=[],
        reference_insights=request.reference_insights,
        creative_ideas=[request.selected_idea],
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

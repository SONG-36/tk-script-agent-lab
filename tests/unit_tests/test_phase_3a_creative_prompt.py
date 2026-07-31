from tk_script_agent_lab.knowledge import RetrievalRequest, StaticKnowledgeRetriever
from tk_script_agent_lab.providers import CreativeGenerationRequest
from tk_script_agent_lab.prompts.creative_idea_v2 import (
    PROMPT_VERSION,
    build_creative_idea_context,
    build_creative_idea_prompt,
)

from phase_1b_helpers import load_phase_1b


def request_with_knowledge() -> CreativeGenerationRequest:
    workflow_input, fixtures, _reviews = load_phase_1b()
    retrieval = StaticKnowledgeRetriever(pack_id="tiktok_car_cleaning_v1").retrieve(
        RetrievalRequest(
            stage="creative",
            target_market=workflow_input.product_profile.target_market,
            product_category=workflow_input.product_profile.category,
            query="Creative guidance for prompt test.",
            limit=2,
            filters={},
        )
    )
    return CreativeGenerationRequest(
        product_profile=workflow_input.product_profile,
        product_facts=workflow_input.product_facts,
        selling_points=workflow_input.selling_points,
        reference_insights=fixtures.reference_insights,
        creative_knowledge_items=retrieval.items,
        idea_count=2,
    )


def test_creative_prompt_v2_separates_business_evidence_and_guidance() -> None:
    context = build_creative_idea_context(request_with_knowledge())

    assert PROMPT_VERSION == "creative_idea_v2"
    assert "business_evidence" in context
    assert "creative_guidance" in context
    assert context["constraints"] == context["business_evidence"]["constraints"]  # type: ignore[index]
    assert context["creative_guidance"][0]["knowledge_id"] == "ck_claim_safety_no_unverified_performance"  # type: ignore[index]


def test_creative_prompt_v2_does_not_allow_knowledge_as_source_usage() -> None:
    context = build_creative_idea_context(request_with_knowledge())
    allowed_source_ids = context["constraints"]["allowed_source_ids"]  # type: ignore[index]
    prompt = build_creative_idea_prompt(request_with_knowledge())

    assert "ck_claim_safety_no_unverified_performance" not in allowed_source_ids["product_fact"]
    assert "ck_claim_safety_no_unverified_performance" not in allowed_source_ids["selling_point"]
    assert "ck_claim_safety_no_unverified_performance" not in allowed_source_ids["reference_insight"]
    assert "Do not put creative knowledge IDs in source_usages" in prompt

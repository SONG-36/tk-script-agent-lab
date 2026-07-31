import json

from tk_script_agent_lab.domain import ProductFact, VerificationStatus
from tk_script_agent_lab.prompts.script_draft_v1 import (
    build_script_draft_context,
    build_script_draft_prompt,
)
from tk_script_agent_lab.providers import ScriptGenerationRequest

from phase_1b_helpers import load_phase_1b


def request() -> ScriptGenerationRequest:
    workflow_input, fixtures, _reviews = load_phase_1b()
    return ScriptGenerationRequest(
        product_profile=workflow_input.product_profile,
        product_facts=[
            *workflow_input.product_facts,
            ProductFact(
                fact_id="fact_rejected_claim",
                product_id=workflow_input.product_profile.product_id,
                field_name="bad_claim",
                value="rejected private claim",
                unit=None,
                status=VerificationStatus.REJECTED,
                source_ids=[],
                notes=None,
            ),
        ],
        selling_points=workflow_input.selling_points,
        reference_insights=fixtures.reference_insights,
        selected_idea=fixtures.creative_ideas[0],
    )


def test_script_context_contains_selected_idea_and_allowed_sources() -> None:
    context = build_script_draft_context(request())

    assert context["approved_creative_idea"]["creative_idea_id"] == "idea_before_after_cleanup"  # type: ignore[index]
    assert context["approved_creative_idea"]["hook"]  # type: ignore[index]
    constraints = context["constraints"]  # type: ignore[index]
    allowed = constraints["allowed_source_ids"]  # type: ignore[index]
    assert allowed["product_fact"] == ["fact_product_category", "fact_usage_context"]
    assert allowed["selling_point"] == ["sp_car_interior_cleanup_context"]
    assert allowed["reference_insight"] == ["insight_car_mess_hook"]


def test_script_context_excludes_unavailable_fact_values_and_unselected_ideas() -> None:
    prompt = build_script_draft_prompt(request())
    payload = prompt.split("using this context:\n", maxsplit=1)[1]

    assert "rejected private claim" not in payload
    assert "fact_rejected_claim" in payload
    assert "fact_power_watts_unknown" in payload
    assert "fact_battery_runtime_unknown" in payload
    assert "idea_driver_cleanup_moment" not in payload
    assert "ScriptDraft" not in payload
    assert "ReviewDecision" not in payload
    assert "ModelCallRecord" not in payload
    assert "OPENAI_API_KEY" not in payload


def test_script_context_does_not_mutate_input() -> None:
    req = request()
    before = req.model_dump(mode="json")

    build_script_draft_context(req)

    assert req.model_dump(mode="json") == before


def test_script_prompt_is_json_context_without_markdown() -> None:
    prompt = build_script_draft_prompt(request())
    payload = prompt.split("using this context:\n", maxsplit=1)[1]

    parsed = json.loads(payload)

    assert parsed["approved_creative_idea"]["creative_idea_id"] == "idea_before_after_cleanup"
    assert "```" not in prompt

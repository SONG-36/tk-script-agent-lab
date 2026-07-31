from tk_script_agent_lab.domain import ProductFact, VerificationStatus
from tk_script_agent_lab.providers import CreativeGenerationRequest
from tk_script_agent_lab.prompts import build_creative_idea_context

from phase_1b_helpers import load_phase_1b


def make_request() -> CreativeGenerationRequest:
    workflow_input, fixtures, _reviews = load_phase_1b()
    return CreativeGenerationRequest(
        product_profile=workflow_input.product_profile,
        product_facts=workflow_input.product_facts,
        selling_points=workflow_input.selling_points,
        reference_insights=fixtures.reference_insights,
        idea_count=2,
    )


def test_prompt_context_includes_verified_fact_values() -> None:
    context = build_creative_idea_context(make_request())

    assert context["verified_facts"][0]["fact_id"] == "fact_product_category"  # type: ignore[index]


def test_prompt_context_excludes_unverified_fact_values() -> None:
    context = build_creative_idea_context(make_request())
    payload = str(context)

    assert "fact_power_watts_unknown" in payload
    assert "'value': None" not in payload


def test_prompt_context_excludes_rejected_facts() -> None:
    request = make_request()
    rejected = ProductFact(
        fact_id="fact_rejected",
        product_id=request.product_profile.product_id,
        field_name="bad_claim",
        value="bad",
        unit=None,
        status=VerificationStatus.REJECTED,
        source_ids=["source"],
        notes=None,
    )
    request = request.model_copy(
        update={"product_facts": [*request.product_facts, rejected]},
        deep=True,
    )

    context = build_creative_idea_context(request)

    assert "bad" not in str(context["verified_facts"])
    assert "fact_rejected" in str(context["constraints"])


def test_prompt_context_includes_selling_points_and_manual_reference_insights() -> None:
    context = build_creative_idea_context(make_request())

    assert context["selling_points"][0]["selling_point_id"] == "sp_car_interior_cleanup_context"  # type: ignore[index]
    assert context["reference_insights"][0]["insight_id"] == "insight_car_mess_hook"  # type: ignore[index]


def test_prompt_context_includes_allowed_source_ids_and_prohibited_claims() -> None:
    context = build_creative_idea_context(make_request())
    constraints = context["constraints"]  # type: ignore[index]

    assert "fact_product_category" in constraints["allowed_source_ids"]["product_fact"]
    assert "sp_car_interior_cleanup_context" in constraints["allowed_source_ids"]["selling_point"]
    assert "insight_car_mess_hook" in constraints["allowed_source_ids"]["reference_insight"]
    assert constraints["prohibited_claims"]


def test_prompt_context_excludes_script_review_and_errors() -> None:
    context = build_creative_idea_context(make_request())
    payload = str(context)

    assert "ScriptDraft" not in payload
    assert "ReviewDecision" not in payload
    assert "ValidationError" not in payload


def test_prompt_context_does_not_modify_request() -> None:
    request = make_request()
    before = request.model_dump(mode="json")

    build_creative_idea_context(request)

    assert request.model_dump(mode="json") == before

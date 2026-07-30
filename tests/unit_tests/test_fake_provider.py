import pytest

from tk_script_agent_lab.providers import (
    CreativeGenerationRequest,
    ProviderOutputError,
    ReferenceAnalysisRequest,
    ScriptGenerationRequest,
)

from phase_1b_helpers import (
    load_phase_1b,
    make_provider,
    with_unverified_fact_idea,
)


def test_fake_provider_same_input_returns_same_results() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = make_provider(fixtures)
    request = ReferenceAnalysisRequest(
        product_profile=workflow_input.product_profile,
        product_facts=workflow_input.product_facts,
        reference_videos=workflow_input.reference_videos,
    )

    first = provider.analyze_references(request)
    second = provider.analyze_references(request)

    assert [item.model_dump(mode="json") for item in first] == [
        item.model_dump(mode="json") for item in second
    ]


def test_fake_provider_returns_stable_order() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = make_provider(fixtures)

    ideas = provider.generate_creative_ideas(
        CreativeGenerationRequest(
            product_profile=workflow_input.product_profile,
            product_facts=workflow_input.product_facts,
            selling_points=workflow_input.selling_points,
            reference_insights=fixtures.reference_insights,
            idea_count=2,
        )
    )

    assert [idea.creative_idea_id for idea in ideas] == [
        "idea_before_after_cleanup",
        "idea_driver_cleanup_moment",
    ]


def test_fake_provider_returned_objects_do_not_modify_internal_fixture() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = make_provider(fixtures)
    ideas = provider.generate_creative_ideas(
        CreativeGenerationRequest(
            product_profile=workflow_input.product_profile,
            product_facts=workflow_input.product_facts,
            selling_points=workflow_input.selling_points,
            reference_insights=fixtures.reference_insights,
            idea_count=2,
        )
    )

    ideas[0].title = "mutated test title"
    fresh = provider.generate_creative_ideas(
        CreativeGenerationRequest(
            product_profile=workflow_input.product_profile,
            product_facts=workflow_input.product_facts,
            selling_points=workflow_input.selling_points,
            reference_insights=fixtures.reference_insights,
            idea_count=2,
        )
    )

    assert fresh[0].title == "Before and after car interior cleanup"


def test_fake_provider_only_returns_requested_video_insights() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = make_provider(fixtures)
    request = ReferenceAnalysisRequest(
        product_profile=workflow_input.product_profile,
        product_facts=workflow_input.product_facts,
        reference_videos=[],
    )

    assert provider.analyze_references(request) == []


def test_fake_provider_idea_count_one_returns_one_idea() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = make_provider(fixtures)

    ideas = provider.generate_creative_ideas(
        CreativeGenerationRequest(
            product_profile=workflow_input.product_profile,
            product_facts=workflow_input.product_facts,
            selling_points=workflow_input.selling_points,
            reference_insights=fixtures.reference_insights,
            idea_count=1,
        )
    )

    assert [idea.creative_idea_id for idea in ideas] == ["idea_before_after_cleanup"]


def test_fake_provider_selected_ideas_return_matching_scripts() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = make_provider(fixtures)

    for idea in fixtures.creative_ideas:
        script = provider.generate_script(
            ScriptGenerationRequest(
                product_profile=workflow_input.product_profile,
                product_facts=workflow_input.product_facts,
                selling_points=workflow_input.selling_points,
                reference_insights=fixtures.reference_insights,
                selected_idea=idea,
            )
        )
        assert script.creative_idea_id == idea.creative_idea_id


def test_fake_provider_missing_script_returns_business_failure() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = make_provider(fixtures.model_copy(update={"script_drafts": []}, deep=True))

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_script(
            ScriptGenerationRequest(
                product_profile=workflow_input.product_profile,
                product_facts=workflow_input.product_facts,
                selling_points=workflow_input.selling_points,
                reference_insights=fixtures.reference_insights,
                selected_idea=fixtures.creative_ideas[0],
            )
        )

    assert exc_info.value.error.code == "SCRIPT_NOT_AVAILABLE"


def test_fake_provider_does_not_return_idea_using_unverified_fact() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = make_provider(with_unverified_fact_idea(workflow_input, fixtures))

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_creative_ideas(
            CreativeGenerationRequest(
                product_profile=workflow_input.product_profile,
                product_facts=workflow_input.product_facts,
                selling_points=workflow_input.selling_points,
                reference_insights=fixtures.reference_insights,
                idea_count=2,
            )
        )

    assert exc_info.value.error.code == "NO_CREATIVE_IDEAS"

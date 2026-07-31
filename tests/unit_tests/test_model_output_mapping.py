import pytest
from pydantic import ValidationError

from tk_script_agent_lab.providers import (
    CreativeIdeaBatch,
    CreativeIdeaCandidate,
    CreativeSourceUsageCandidate,
    ScriptDraftCandidate,
    ScriptSceneCandidate,
    ScriptSourceUsageCandidate,
    map_candidate_to_creative_idea,
    map_candidate_to_script_draft,
)


def candidate(title: str = "Idea A", hook: str = "Hook A") -> CreativeIdeaCandidate:
    return CreativeIdeaCandidate(
        title=title,
        hook=hook,
        concept_summary="Summary",
        target_audience="Car owners",
        source_usages=[
            CreativeSourceUsageCandidate(
                source_type="selling_point",
                source_id="sp_car_interior_cleanup_context",
                usage_purpose="Use product angle.",
            ),
            CreativeSourceUsageCandidate(
                source_type="reference_insight",
                source_id="insight_car_mess_hook",
                usage_purpose="Use hook structure.",
            ),
        ],
        risk_notes=["No unverified specs."],
    )


def test_creative_idea_batch_accepts_valid_candidates() -> None:
    batch = CreativeIdeaBatch(ideas=[candidate(), candidate("Idea B", "Hook B")])

    assert len(batch.ideas) == 2


def test_creative_idea_candidate_missing_field_fails() -> None:
    with pytest.raises(ValidationError):
        CreativeIdeaCandidate.model_validate({"title": "Only title"})


def test_creative_source_usage_rejects_invalid_source_type() -> None:
    with pytest.raises(ValidationError):
        CreativeSourceUsageCandidate(
            source_type="knowledge_item",
            source_id="x",
            usage_purpose="Bad.",
        )


def test_creative_idea_batch_rejects_empty_ideas() -> None:
    with pytest.raises(ValidationError):
        CreativeIdeaBatch(ideas=[])


def test_creative_idea_batch_rejects_duplicate_title_or_hook() -> None:
    with pytest.raises(ValidationError):
        CreativeIdeaBatch(ideas=[candidate(), candidate("Idea A", "Hook B")])
    with pytest.raises(ValidationError):
        CreativeIdeaBatch(ideas=[candidate(), candidate("Idea B", "Hook A")])


def test_candidate_schema_does_not_include_domain_ids() -> None:
    with pytest.raises(ValidationError):
        CreativeIdeaCandidate.model_validate(
            {
                **candidate().model_dump(mode="json"),
                "creative_idea_id": "model_should_not_set_this",
            }
        )


def test_mapping_generates_stable_ids_and_product_id() -> None:
    first = map_candidate_to_creative_idea(
        product_id="prod_1",
        candidate=candidate(),
        index=1,
    )
    second = map_candidate_to_creative_idea(
        product_id="prod_1",
        candidate=candidate(),
        index=1,
    )

    assert first.creative_idea_id == second.creative_idea_id
    assert first.source_usages[0].source_usage_id == second.source_usages[0].source_usage_id
    assert first.product_id == "prod_1"


def test_mapping_different_candidate_gets_different_id() -> None:
    first = map_candidate_to_creative_idea(product_id="prod_1", candidate=candidate(), index=1)
    second = map_candidate_to_creative_idea(
        product_id="prod_1",
        candidate=candidate("Idea B", "Hook B"),
        index=1,
    )

    assert first.creative_idea_id != second.creative_idea_id


def script_candidate(title: str = "Script A") -> ScriptDraftCandidate:
    return ScriptDraftCandidate(
        title=title,
        scenes=[
            ScriptSceneCandidate(
                visual="Show small car debris.",
                action="Point to the mess before cleanup.",
                voiceover="Small mess in the car?",
                on_screen_text="Tiny car mess",
                duration_seconds=3,
            ),
            ScriptSceneCandidate(
                visual="Show the cleanup context.",
                action="Use the product around the seat.",
                voiceover=None,
                on_screen_text="Clean the small mess",
                duration_seconds=4,
            ),
        ],
        caption="A simple car interior cleanup moment.",
        cta="Check the product details.",
        source_usages=[
            ScriptSourceUsageCandidate(
                source_type="selling_point",
                source_id="sp_car_interior_cleanup_context",
                usage_purpose="Support the car interior cleanup context.",
            ),
            ScriptSourceUsageCandidate(
                source_type="reference_insight",
                source_id="insight_car_mess_hook",
                usage_purpose="Use the small visible mess hook.",
            ),
        ],
    )


def test_script_draft_candidate_accepts_valid_candidate() -> None:
    candidate = script_candidate()

    assert len(candidate.scenes) == 2
    assert len(candidate.source_usages) == 2


def test_script_draft_candidate_rejects_invalid_scene_or_source() -> None:
    with pytest.raises(ValidationError):
        ScriptDraftCandidate(title="Bad", scenes=[], source_usages=script_candidate().source_usages)
    with pytest.raises(ValidationError):
        ScriptSceneCandidate(visual="Show", action="Act", duration_seconds=0)
    with pytest.raises(ValidationError):
        ScriptSceneCandidate(visual="", action="Act", duration_seconds=1)
    with pytest.raises(ValidationError):
        ScriptSourceUsageCandidate(
            source_type="knowledge_item",
            source_id="x",
            usage_purpose="Bad.",
        )


def test_script_candidate_schema_does_not_include_domain_ids() -> None:
    with pytest.raises(ValidationError):
        ScriptDraftCandidate.model_validate(
            {
                **script_candidate().model_dump(mode="json"),
                "script_id": "model_should_not_set_this",
            }
        )


def test_script_draft_candidate_rejects_duplicate_scene_or_source() -> None:
    base = script_candidate()
    with pytest.raises(ValidationError):
        ScriptDraftCandidate(
            title="Duplicate scene",
            scenes=[base.scenes[0], base.scenes[0]],
            source_usages=base.source_usages,
        )
    with pytest.raises(ValidationError):
        ScriptDraftCandidate(
            title="Duplicate source",
            scenes=base.scenes,
            source_usages=[base.source_usages[0], base.source_usages[0]],
        )


def test_script_mapping_generates_stable_ids_and_sequences() -> None:
    first = map_candidate_to_script_draft(
        product_id="prod_1",
        creative_idea_id="idea_1",
        candidate=script_candidate(),
    )
    second = map_candidate_to_script_draft(
        product_id="prod_1",
        creative_idea_id="idea_1",
        candidate=script_candidate(),
    )

    assert first.script_id == second.script_id
    assert first.scenes[0].scene_id == second.scenes[0].scene_id
    assert first.source_usages[0].source_usage_id == second.source_usages[0].source_usage_id
    assert [scene.sequence for scene in first.scenes] == [1, 2]
    assert first.product_id == "prod_1"
    assert first.creative_idea_id == "idea_1"


def test_script_mapping_different_candidate_gets_different_id() -> None:
    first = map_candidate_to_script_draft(
        product_id="prod_1",
        creative_idea_id="idea_1",
        candidate=script_candidate("Script A"),
    )
    second = map_candidate_to_script_draft(
        product_id="prod_1",
        creative_idea_id="idea_1",
        candidate=script_candidate("Script B"),
    )

    assert first.script_id != second.script_id

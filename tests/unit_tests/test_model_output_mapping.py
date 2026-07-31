import pytest
from pydantic import ValidationError

from tk_script_agent_lab.providers import (
    CreativeIdeaBatch,
    CreativeIdeaCandidate,
    CreativeSourceUsageCandidate,
    map_candidate_to_creative_idea,
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

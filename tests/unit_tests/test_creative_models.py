import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import CreativeIdea, SourceUsage


def test_creative_idea_requires_source_usage() -> None:
    idea = CreativeIdea(
        creative_idea_id="idea_1",
        product_id="prod_1",
        title="Before after cleanup",
        hook="Show the mess first.",
        concept_summary="Use verified context.",
        target_audience="Car owners",
        source_usages=[
            SourceUsage(
                source_usage_id="usage_1",
                source_type="selling_point",
                source_id="sp_1",
                usage_purpose="Support angle.",
            )
        ],
        risk_notes=[],
    )

    assert idea.source_usages[0].source_id == "sp_1"


def test_creative_idea_rejects_duplicate_source_reference() -> None:
    with pytest.raises(PydanticValidationError):
        CreativeIdea(
            creative_idea_id="idea_1",
            product_id="prod_1",
            title="Before after cleanup",
            hook="Show the mess first.",
            concept_summary="Use verified context.",
            target_audience="Car owners",
            source_usages=[
                SourceUsage(
                    source_usage_id="usage_1",
                    source_type="selling_point",
                    source_id="sp_1",
                    usage_purpose="Support angle.",
                ),
                SourceUsage(
                    source_usage_id="usage_2",
                    source_type="selling_point",
                    source_id="sp_1",
                    usage_purpose="Repeat angle.",
                ),
            ],
            risk_notes=[],
        )

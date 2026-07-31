import pytest
from pydantic import ValidationError

from tk_script_agent_lab.providers import (
    CreativeIdeaBatch,
    CreativeIdeaCandidate,
    CreativeSourceUsageCandidate,
)

from test_openai_creative_provider import StructuredModel, request
from tk_script_agent_lab.providers import OpenAICreativeProvider, ProviderOutputError


class CapturingModel:
    def __init__(self, result: object) -> None:
        self.result = result
        self.input = None

    def invoke(self, input: object) -> object:
        self.input = input
        return self.result


def test_knowledge_id_cannot_be_source_usage_candidate_type() -> None:
    with pytest.raises(ValidationError):
        CreativeSourceUsageCandidate(
            source_type="knowledge_item",
            source_id="ck_hook_visible_micro_mess",
            usage_purpose="Bad source.",
        )


def test_knowledge_id_as_business_source_id_is_rejected_by_provider() -> None:
    batch = CreativeIdeaBatch(
        ideas=[
            CreativeIdeaCandidate(
                title="Bad knowledge source",
                hook="Bad hook",
                concept_summary="Uses a knowledge id as if it were evidence.",
                target_audience="Car owners",
                source_usages=[
                    CreativeSourceUsageCandidate(
                        source_type="selling_point",
                        source_id="ck_hook_visible_micro_mess",
                        usage_purpose="Invalid evidence.",
                    ),
                    CreativeSourceUsageCandidate(
                        source_type="reference_insight",
                        source_id="insight_car_mess_hook",
                        usage_purpose="Use hook insight.",
                    ),
                ],
                risk_notes=[],
            ),
            CreativeIdeaCandidate(
                title="Valid second idea",
                hook="Second hook",
                concept_summary="A second idea.",
                target_audience="Drivers",
                source_usages=[
                    CreativeSourceUsageCandidate(
                        source_type="selling_point",
                        source_id="sp_car_interior_cleanup_context",
                        usage_purpose="Use product angle.",
                    ),
                    CreativeSourceUsageCandidate(
                        source_type="reference_insight",
                        source_id="insight_car_mess_hook",
                        usage_purpose="Use hook insight.",
                    ),
                ],
                risk_notes=[],
            ),
        ]
    )
    provider = OpenAICreativeProvider(
        model="test-model",
        prompt_version="creative_idea_v2",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel(batch),
    )

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_creative_ideas(request())

    assert exc_info.value.error.code == "MODEL_OUTPUT_SOURCE_INVALID"


def test_openai_creative_provider_uses_v2_prompt_boundary() -> None:
    model = CapturingModel(batch_for_success())
    provider = OpenAICreativeProvider(
        model="test-model",
        prompt_version="creative_idea_v2",
        api_key_getter=lambda: "test-key",
        structured_model=model,
    )

    result = provider.generate_creative_ideas(request())

    assert result.model_call_record.prompt_version == "creative_idea_v2"
    assert model.input is not None
    messages = "\n".join(message[1] for message in model.input)  # type: ignore[union-attr]
    assert "BUSINESS EVIDENCE" in messages
    assert "CREATIVE GUIDANCE" in messages
    assert "Do not put creative knowledge IDs in source_usages" in messages


def batch_for_success() -> CreativeIdeaBatch:
    return CreativeIdeaBatch(
        ideas=[
            CreativeIdeaCandidate(
                title="Valid idea one",
                hook="Valid hook one",
                concept_summary="A valid idea.",
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
                        usage_purpose="Use hook insight.",
                    ),
                ],
                risk_notes=[],
            ),
            CreativeIdeaCandidate(
                title="Valid idea two",
                hook="Valid hook two",
                concept_summary="A second valid idea.",
                target_audience="Drivers",
                source_usages=[
                    CreativeSourceUsageCandidate(
                        source_type="selling_point",
                        source_id="sp_car_interior_cleanup_context",
                        usage_purpose="Use product angle.",
                    ),
                    CreativeSourceUsageCandidate(
                        source_type="reference_insight",
                        source_id="insight_car_mess_hook",
                        usage_purpose="Use hook insight.",
                    ),
                ],
                risk_notes=[],
            ),
        ]
    )

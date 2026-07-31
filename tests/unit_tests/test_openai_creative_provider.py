import pytest

from tk_script_agent_lab.providers import (
    CreativeGenerationRequest,
    CreativeIdeaBatch,
    CreativeIdeaCandidate,
    CreativeSourceUsageCandidate,
    OpenAICreativeProvider,
    ProviderOutputError,
)

from phase_1b_helpers import load_phase_1b


class RawMessage:
    id = "response_123"
    usage_metadata = {"input_tokens": 10, "output_tokens": 20}
    response_metadata = {}


class StructuredModel:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls = 0

    def invoke(self, input: object) -> object:
        self.calls += 1
        return self.result


class RaisingModel:
    def invoke(self, input: object) -> object:
        raise RuntimeError("controlled failure")


def request() -> CreativeGenerationRequest:
    workflow_input, fixtures, _reviews = load_phase_1b()
    return CreativeGenerationRequest(
        product_profile=workflow_input.product_profile,
        product_facts=workflow_input.product_facts,
        selling_points=workflow_input.selling_points,
        reference_insights=fixtures.reference_insights,
        idea_count=2,
    )


def batch() -> CreativeIdeaBatch:
    return CreativeIdeaBatch(
        ideas=[
            _candidate("Idea A", "Hook A"),
            _candidate("Idea B", "Hook B"),
        ]
    )


def test_openai_provider_calls_model_once_and_returns_record() -> None:
    structured = StructuredModel({"parsed": batch(), "raw": RawMessage(), "parsing_error": None})
    provider = OpenAICreativeProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=structured,
    )

    result = provider.generate_creative_ideas(request())

    assert structured.calls == 1
    assert len(result.creative_ideas) == 2
    assert result.model_call_record.response_id == "response_123"
    assert result.model_call_record.input_tokens == 10
    assert result.model_call_record.output_tokens == 20


def test_openai_provider_usage_missing_stays_none() -> None:
    class RawNoUsage:
        id = None
        usage_metadata = {}
        response_metadata = {}

    provider = OpenAICreativeProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel({"parsed": batch(), "raw": RawNoUsage(), "parsing_error": None}),
    )

    result = provider.generate_creative_ideas(request())

    assert result.model_call_record.input_tokens is None
    assert result.model_call_record.output_tokens is None


def test_openai_provider_sdk_exception_becomes_model_call_failed() -> None:
    provider = OpenAICreativeProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=RaisingModel(),
    )

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_creative_ideas(request())

    assert exc_info.value.error.code == "MODEL_CALL_FAILED"


def test_openai_provider_schema_failure_becomes_schema_invalid() -> None:
    provider = OpenAICreativeProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel({"parsed": {"ideas": [{}]}, "raw": None, "parsing_error": None}),
    )

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_creative_ideas(request())

    assert exc_info.value.error.code == "MODEL_OUTPUT_SCHEMA_INVALID"


def test_openai_provider_duplicate_output_becomes_duplicate_invalid() -> None:
    duplicate = {
        "ideas": [
            _candidate("Same title", "Hook A").model_dump(mode="json"),
            _candidate("Same title", "Hook B").model_dump(mode="json"),
        ]
    }
    provider = OpenAICreativeProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel({"parsed": duplicate, "raw": None, "parsing_error": None}),
    )

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_creative_ideas(request())

    assert exc_info.value.error.code == "MODEL_OUTPUT_DUPLICATE"


def test_openai_provider_wrong_count_becomes_count_invalid() -> None:
    provider = OpenAICreativeProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel(CreativeIdeaBatch(ideas=[_candidate("Only", "One")])),
    )

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_creative_ideas(request())

    assert exc_info.value.error.code == "MODEL_OUTPUT_COUNT_INVALID"


def test_openai_provider_bad_source_becomes_source_invalid() -> None:
    bad = CreativeIdeaBatch(
        ideas=[
            _candidate("Idea A", "Hook A", source_id="missing_source"),
            _candidate("Idea B", "Hook B"),
        ]
    )
    provider = OpenAICreativeProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel(bad),
    )

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_creative_ideas(request())

    assert exc_info.value.error.code == "MODEL_OUTPUT_SOURCE_INVALID"


def test_openai_provider_does_not_modify_input() -> None:
    req = request()
    before = req.model_dump(mode="json")
    provider = OpenAICreativeProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel(batch()),
    )

    provider.generate_creative_ideas(req)

    assert req.model_dump(mode="json") == before


def test_openai_provider_missing_key_becomes_configuration_missing() -> None:
    provider = OpenAICreativeProvider(model="test-model", api_key_getter=lambda: None)

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_creative_ideas(request())

    assert exc_info.value.error.code == "MODEL_CONFIGURATION_MISSING"


def _candidate(
    title: str,
    hook: str,
    source_id: str = "sp_car_interior_cleanup_context",
) -> CreativeIdeaCandidate:
    return CreativeIdeaCandidate(
        title=title,
        hook=hook,
        concept_summary=f"{title} summary.",
        target_audience="Car owners",
        source_usages=[
            CreativeSourceUsageCandidate(
                source_type="selling_point",
                source_id=source_id,
                usage_purpose="Use product angle.",
            ),
            CreativeSourceUsageCandidate(
                source_type="reference_insight",
                source_id="insight_car_mess_hook",
                usage_purpose="Use hook structure.",
            ),
        ],
        risk_notes=["Do not use unverified specs."],
    )

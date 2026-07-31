import pytest

from tk_script_agent_lab.providers import (
    OpenAIScriptProvider,
    ProviderOutputError,
    ScriptDraftCandidate,
    ScriptGenerationRequest,
    ScriptSceneCandidate,
    ScriptSourceUsageCandidate,
)

from phase_1b_helpers import load_phase_1b


class RawMessage:
    id = "script_response_123"
    usage_metadata = {"input_tokens": 30, "output_tokens": 40}
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


def request() -> ScriptGenerationRequest:
    workflow_input, fixtures, _reviews = load_phase_1b()
    return ScriptGenerationRequest(
        product_profile=workflow_input.product_profile,
        product_facts=workflow_input.product_facts,
        selling_points=workflow_input.selling_points,
        reference_insights=fixtures.reference_insights,
        selected_idea=fixtures.creative_ideas[0],
    )


def candidate(source_id: str = "sp_car_interior_cleanup_context") -> ScriptDraftCandidate:
    return ScriptDraftCandidate(
        title="Script from approved idea",
        scenes=[
            ScriptSceneCandidate(
                visual="Show small car debris.",
                action="Point to the mess before cleanup.",
                voiceover="Small mess in the car?",
                on_screen_text="Tiny car mess",
                duration_seconds=3,
            ),
            ScriptSceneCandidate(
                visual="Show cleanup around the seat.",
                action="Frame the product as a car cleanup helper.",
                voiceover=None,
                on_screen_text="Clean small debris",
                duration_seconds=4,
            ),
        ],
        caption="A simple car interior cleanup moment.",
        cta="Check the product details.",
        source_usages=[
            ScriptSourceUsageCandidate(
                source_type="selling_point",
                source_id=source_id,
                usage_purpose="Support car interior cleanup context.",
            ),
            ScriptSourceUsageCandidate(
                source_type="reference_insight",
                source_id="insight_car_mess_hook",
                usage_purpose="Use visible mess hook structure.",
            ),
        ],
    )


def test_openai_script_provider_calls_model_once_and_returns_record() -> None:
    structured = StructuredModel({"parsed": candidate(), "raw": RawMessage(), "parsing_error": None})
    provider = OpenAIScriptProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=structured,
    )

    result = provider.generate_script(request())

    assert structured.calls == 1
    assert result.script_draft.creative_idea_id == "idea_before_after_cleanup"
    assert result.script_draft.product_id == "prod_car_vacuum_schema_fixture"
    assert [scene.sequence for scene in result.script_draft.scenes] == [1, 2]
    assert result.model_call_record.operation == "generate_script"
    assert result.model_call_record.response_id == "script_response_123"
    assert result.model_call_record.input_tokens == 30
    assert result.model_call_record.output_tokens == 40
    assert result.model_call_record.output_ids == [result.script_draft.script_id]


def test_openai_script_provider_usage_missing_stays_none() -> None:
    class RawNoUsage:
        id = None
        usage_metadata = {}
        response_metadata = {}

    provider = OpenAIScriptProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel({"parsed": candidate(), "raw": RawNoUsage(), "parsing_error": None}),
    )

    result = provider.generate_script(request())

    assert result.model_call_record.input_tokens is None
    assert result.model_call_record.output_tokens is None


def test_openai_script_provider_sdk_exception_becomes_model_call_failed() -> None:
    provider = OpenAIScriptProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=RaisingModel(),
    )

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_script(request())

    assert exc_info.value.error.code == "MODEL_CALL_FAILED"


def test_openai_script_provider_schema_failure_becomes_schema_invalid() -> None:
    provider = OpenAIScriptProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel({"parsed": {"title": "Missing scenes"}, "raw": None, "parsing_error": None}),
    )

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_script(request())

    assert exc_info.value.error.code == "MODEL_OUTPUT_SCHEMA_INVALID"


def test_openai_script_provider_bad_source_becomes_source_invalid() -> None:
    provider = OpenAIScriptProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel(candidate(source_id="missing_source")),
    )

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_script(request())

    assert exc_info.value.error.code == "MODEL_OUTPUT_SOURCE_INVALID"


def test_openai_script_provider_missing_key_becomes_configuration_missing() -> None:
    provider = OpenAIScriptProvider(model="test-model", api_key_getter=lambda: None)

    with pytest.raises(ProviderOutputError) as exc_info:
        provider.generate_script(request())

    assert exc_info.value.error.code == "MODEL_CONFIGURATION_MISSING"


def test_openai_script_provider_does_not_modify_input() -> None:
    req = request()
    before = req.model_dump(mode="json")
    provider = OpenAIScriptProvider(
        model="test-model",
        api_key_getter=lambda: "test-key",
        structured_model=StructuredModel(candidate()),
    )

    provider.generate_script(req)

    assert req.model_dump(mode="json") == before

from langgraph.types import Command

from tk_script_agent_lab.domain import CreativeIdea, SourceUsage
from tk_script_agent_lab.langgraph_app import nodes
from tk_script_agent_lab.providers import (
    ModelCallRecord,
    OpenAICreativeResult,
)
from tk_script_agent_lab.workflow import WorkflowStatus

from phase_1c_helpers import (
    approved_resume,
    load_studio_input,
    make_graph,
    thread_config,
)


class StubOpenAICreativeProvider:
    calls = 0

    def __init__(self, *, model: str, prompt_version: str) -> None:
        self.model = model
        self.prompt_version = prompt_version

    def generate_creative_ideas(self, request) -> OpenAICreativeResult:  # type: ignore[no-untyped-def]
        type(self).calls += 1
        ideas = [
            CreativeIdea(
                creative_idea_id="idea_openai_stub_1",
                product_id=request.product_profile.product_id,
                title="OpenAI stub idea one",
                hook="OpenAI stub hook one",
                concept_summary="A stubbed OpenAI creative idea.",
                target_audience="Car owners",
                source_usages=[
                    SourceUsage(
                        source_usage_id="usage_openai_stub_sp",
                        source_type="selling_point",
                        source_id="sp_car_interior_cleanup_context",
                        usage_purpose="Use product angle.",
                    ),
                    SourceUsage(
                        source_usage_id="usage_openai_stub_insight",
                        source_type="reference_insight",
                        source_id="insight_car_mess_hook",
                        usage_purpose="Use manual insight.",
                    ),
                ],
                risk_notes=["No unverified specs."],
            ),
            CreativeIdea(
                creative_idea_id="idea_openai_stub_2",
                product_id=request.product_profile.product_id,
                title="OpenAI stub idea two",
                hook="OpenAI stub hook two",
                concept_summary="A second stubbed OpenAI creative idea.",
                target_audience="Drivers",
                source_usages=[
                    SourceUsage(
                        source_usage_id="usage_openai_stub_2_sp",
                        source_type="selling_point",
                        source_id="sp_car_interior_cleanup_context",
                        usage_purpose="Use product angle.",
                    ),
                    SourceUsage(
                        source_usage_id="usage_openai_stub_2_insight",
                        source_type="reference_insight",
                        source_id="insight_car_mess_hook",
                        usage_purpose="Use manual insight.",
                    ),
                ],
                risk_notes=["No performance claims."],
            ),
        ]
        return OpenAICreativeResult(
            creative_ideas=ideas,
            model_call_record=ModelCallRecord(
                operation="generate_creative_ideas",
                provider="openai",
                model=self.model,
                prompt_version=self.prompt_version,
                attempt=1,
                status="SUCCESS",
                response_id="stub-response",
                input_tokens=None,
                output_tokens=None,
                output_ids=[idea.creative_idea_id for idea in ideas],
                error_code=None,
            ),
        )


def test_default_fake_mode_still_reaches_interrupt() -> None:
    graph = make_graph()
    result = graph.invoke(load_studio_input(), config=thread_config("phase-2a-fake"))

    assert result["__interrupt__"]
    assert result["step_records"][2].executor == "FAKE_PROVIDER"
    assert result.get("model_call_records", []) == []


def test_openai_stub_mode_reaches_interrupt(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    StubOpenAICreativeProvider.calls = 0
    monkeypatch.setattr(nodes, "OpenAICreativeProvider", StubOpenAICreativeProvider)
    graph = make_graph()

    result = graph.invoke(
        load_studio_input(),
        config=thread_config("phase-2a-openai-stub"),
        context={"creative_provider": "openai", "creative_model": "stub-model"},
    )

    assert result["__interrupt__"]
    assert StubOpenAICreativeProvider.calls == 1
    assert [idea.creative_idea_id for idea in result["creative_ideas"]] == [
        "idea_openai_stub_1",
        "idea_openai_stub_2",
    ]
    assert result["step_records"][2].executor == "MODEL"
    assert len(result["model_call_records"]) == 1
    assert result.get("script_draft") is None


def test_openai_context_missing_model_fails_before_interrupt() -> None:
    graph = make_graph()

    result = graph.invoke(
        load_studio_input(),
        config=thread_config("phase-2a-openai-missing-model"),
        context={"creative_provider": "openai"},
    )

    assert result["status"] == WorkflowStatus.FAILED
    assert "__interrupt__" not in result
    assert "MODEL_CONFIGURATION_MISSING" in [
        error.code for error in result["validation_errors"]
    ]
    assert result["model_call_records"][0].status == "FAILED"


def test_openai_new_idea_approved_without_fixture_script_fails(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(nodes, "OpenAICreativeProvider", StubOpenAICreativeProvider)
    graph = make_graph()
    config = thread_config("phase-2a-openai-no-script")
    first = graph.invoke(
        load_studio_input(),
        config=config,
        context={"creative_provider": "openai", "creative_model": "stub-model"},
    )
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    result = graph.invoke(Command(resume=approved_resume(selected_id)), config=config)

    assert result["status"] == WorkflowStatus.FAILED
    assert result.get("script_draft") is None
    assert "SCRIPT_NOT_AVAILABLE" in [error.code for error in result["validation_errors"]]

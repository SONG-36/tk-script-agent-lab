from langgraph.types import Command

from tk_script_agent_lab.domain import CreativeIdea, ScriptDraft, ScriptScene, SourceUsage
from tk_script_agent_lab.langgraph_app import nodes
from tk_script_agent_lab.providers import ModelCallRecord, OpenAICreativeResult, OpenAIScriptResult
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
                creative_idea_id="idea_openai_stub_scriptable",
                product_id=request.product_profile.product_id,
                title="OpenAI scriptable idea",
                hook="OpenAI hook for script.",
                concept_summary="A scriptable OpenAI creative idea.",
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
                title="OpenAI second idea",
                hook="OpenAI second hook.",
                concept_summary="A second creative idea.",
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
                risk_notes=[],
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
                response_id="creative-response",
                input_tokens=None,
                output_tokens=None,
                output_ids=[idea.creative_idea_id for idea in ideas],
                error_code=None,
            ),
        )


class StubOpenAIScriptProvider:
    calls = 0

    def __init__(self, *, model: str, prompt_version: str) -> None:
        self.model = model
        self.prompt_version = prompt_version

    def generate_script(self, request) -> OpenAIScriptResult:  # type: ignore[no-untyped-def]
        type(self).calls += 1
        script = ScriptDraft(
            script_id=f"script_stub_{request.selected_idea.creative_idea_id}",
            product_id=request.product_profile.product_id,
            creative_idea_id=request.selected_idea.creative_idea_id,
            title="Stub OpenAI script",
            scenes=[
                ScriptScene(
                    scene_id="scene_stub_1",
                    sequence=1,
                    visual="Show the car mess.",
                    action="Frame the small debris.",
                    voiceover="Small mess in the car?",
                    on_screen_text="Small car mess",
                    duration_seconds=3,
                )
            ],
            caption="Clean up small car messes.",
            cta="Check the details.",
            source_usages=[
                SourceUsage(
                    source_usage_id="usage_script_stub_sp",
                    source_type="selling_point",
                    source_id="sp_car_interior_cleanup_context",
                    usage_purpose="Support product context.",
                ),
                SourceUsage(
                    source_usage_id="usage_script_stub_insight",
                    source_type="reference_insight",
                    source_id="insight_car_mess_hook",
                    usage_purpose="Use manual hook insight.",
                ),
            ],
        )
        return OpenAIScriptResult(
            script_draft=script,
            model_call_record=ModelCallRecord(
                operation="generate_script",
                provider="openai",
                model=self.model,
                prompt_version=self.prompt_version,
                attempt=1,
                status="SUCCESS",
                response_id="script-response",
                input_tokens=None,
                output_tokens=None,
                output_ids=[script.script_id],
                error_code=None,
            ),
        )


def test_fake_creative_openai_script_stub_completes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    StubOpenAIScriptProvider.calls = 0
    monkeypatch.setattr(nodes, "OpenAIScriptProvider", StubOpenAIScriptProvider)
    graph = make_graph()
    config = thread_config("phase-2b-fake-openai")
    first = graph.invoke(load_studio_input(), config=config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    result = graph.invoke(
        Command(resume=approved_resume(selected_id)),
        config=config,
        context={"script_provider": "openai", "script_model": "stub-script-model"},
    )

    assert StubOpenAIScriptProvider.calls == 1
    assert result["status"] == WorkflowStatus.COMPLETED
    assert result["script_draft"].creative_idea_id == selected_id
    assert [record.operation for record in result["model_call_records"]] == ["generate_script"]
    script_step = next(
        record for record in result["step_records"] if record.step_name == "generate_script"
    )
    assert script_step.executor == "MODEL"


def test_openai_creative_fake_script_keeps_phase_2a_boundary(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(nodes, "OpenAICreativeProvider", StubOpenAICreativeProvider)
    graph = make_graph()
    config = thread_config("phase-2b-openai-fake")
    first = graph.invoke(
        load_studio_input(),
        config=config,
        context={"creative_provider": "openai", "creative_model": "stub-creative-model"},
    )
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    result = graph.invoke(Command(resume=approved_resume(selected_id)), config=config)

    assert result["status"] == WorkflowStatus.FAILED
    assert result.get("script_draft") is None
    assert [record.operation for record in result["model_call_records"]] == [
        "generate_creative_ideas"
    ]
    assert "SCRIPT_NOT_AVAILABLE" in [error.code for error in result["validation_errors"]]


def test_openai_creative_openai_script_stub_completes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    StubOpenAICreativeProvider.calls = 0
    StubOpenAIScriptProvider.calls = 0
    monkeypatch.setattr(nodes, "OpenAICreativeProvider", StubOpenAICreativeProvider)
    monkeypatch.setattr(nodes, "OpenAIScriptProvider", StubOpenAIScriptProvider)
    graph = make_graph()
    config = thread_config("phase-2b-openai-openai")
    first = graph.invoke(
        load_studio_input(),
        config=config,
        context={"creative_provider": "openai", "creative_model": "stub-creative-model"},
    )
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    result = graph.invoke(
        Command(resume=approved_resume(selected_id)),
        config=config,
        context={
            "creative_provider": "openai",
            "creative_model": "stub-creative-model",
            "script_provider": "openai",
            "script_model": "stub-script-model",
        },
    )

    assert result["status"] == WorkflowStatus.COMPLETED
    assert StubOpenAICreativeProvider.calls == 1
    assert StubOpenAIScriptProvider.calls == 1
    assert [record.operation for record in result["model_call_records"]] == [
        "generate_creative_ideas",
        "generate_script",
    ]


def test_non_approved_review_does_not_call_openai_script(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    StubOpenAIScriptProvider.calls = 0
    monkeypatch.setattr(nodes, "OpenAIScriptProvider", StubOpenAIScriptProvider)
    graph = make_graph()
    config = thread_config("phase-2b-rejected-no-script")
    first = graph.invoke(load_studio_input(), config=config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    result = graph.invoke(
        Command(
            resume={
                "target_id": selected_id,
                "decision": "REJECTED",
                "reviewer": "test-reviewer",
                "comment": "No.",
            }
        ),
        config=config,
        context={"script_provider": "openai", "script_model": "stub-script-model"},
    )

    assert result["status"] == WorkflowStatus.IDEA_REJECTED
    assert StubOpenAIScriptProvider.calls == 0
    assert result.get("script_draft") is None


def test_openai_script_missing_model_keeps_configuration_error() -> None:
    graph = make_graph()
    config = thread_config("phase-2b-openai-script-missing-model")
    first = graph.invoke(load_studio_input(), config=config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    result = graph.invoke(
        Command(resume=approved_resume(selected_id)),
        config=config,
        context={"script_provider": "openai"},
    )

    assert result["status"] == WorkflowStatus.FAILED
    assert result.get("script_draft") is None
    assert [error.code for error in result["validation_errors"]] == [
        "MODEL_CONFIGURATION_MISSING"
    ]
    assert result["model_call_records"][0].operation == "generate_script"
    assert result["model_call_records"][0].status == "FAILED"

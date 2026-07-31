from tk_script_agent_lab.domain import CreativeIdea, SourceUsage
from tk_script_agent_lab.langgraph_app import nodes
from tk_script_agent_lab.providers import ModelCallRecord, OpenAICreativeResult
from tk_script_agent_lab.workflow import WorkflowStatus

from phase_1c_helpers import load_studio_input, make_graph, thread_config


class InvalidSourceOpenAIProvider:
    def __init__(self, *, model: str, prompt_version: str) -> None:
        self.model = model
        self.prompt_version = prompt_version

    def generate_creative_ideas(self, request) -> OpenAICreativeResult:  # type: ignore[no-untyped-def]
        idea = CreativeIdea(
            creative_idea_id="idea_bad_source",
            product_id=request.product_profile.product_id,
            title="Bad source idea",
            hook="Bad source hook",
            concept_summary="This idea has an invalid source.",
            target_audience="Car owners",
            source_usages=[
                SourceUsage(
                    source_usage_id="usage_bad_source",
                    source_type="product_fact",
                    source_id="missing_fact",
                    usage_purpose="Bad source.",
                )
            ],
            risk_notes=[],
        )
        return OpenAICreativeResult(
            creative_ideas=[idea],
            model_call_record=ModelCallRecord(
                operation="generate_creative_ideas",
                provider="openai",
                model=self.model,
                prompt_version=self.prompt_version,
                attempt=1,
                status="SUCCESS",
                response_id=None,
                input_tokens=None,
                output_tokens=None,
                output_ids=[idea.creative_idea_id],
                error_code=None,
            ),
        )


def test_illegal_openai_provider_output_does_not_enter_interrupt(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(nodes, "OpenAICreativeProvider", InvalidSourceOpenAIProvider)
    graph = make_graph()

    result = graph.invoke(
        load_studio_input(),
        config=thread_config("phase-2a-invalid-output"),
        context={"creative_provider": "openai", "creative_model": "stub-model"},
    )

    assert result["status"] == WorkflowStatus.FAILED
    assert "__interrupt__" not in result
    assert "FACT_NOT_FOUND" in [error.code for error in result["validation_errors"]]


def test_fake_mode_does_not_create_model_call_record() -> None:
    graph = make_graph()

    result = graph.invoke(load_studio_input(), config=thread_config("phase-2a-fake-records"))

    assert result.get("model_call_records", []) == []

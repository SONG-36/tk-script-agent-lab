from tk_script_agent_lab.langgraph_app import nodes
from tk_script_agent_lab.domain import CreativeIdea, SourceUsage
from tk_script_agent_lab.providers import ModelCallRecord, OpenAICreativeResult
from tk_script_agent_lab.workflow import WorkflowStatus

from tests.unit_tests.phase_1c_helpers import load_studio_input, make_graph, thread_config


class StubOpenAICreativeProvider:
    def __init__(self, *, model: str, prompt_version: str) -> None:
        self.model = model
        self.prompt_version = prompt_version

    def generate_creative_ideas(self, request) -> OpenAICreativeResult:  # type: ignore[no-untyped-def]
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


def test_phase_2a_graph_mocked_openai_reaches_human_gate(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(nodes, "OpenAICreativeProvider", StubOpenAICreativeProvider)
    graph = make_graph()

    result = graph.invoke(
        load_studio_input(),
        config=thread_config("phase-2a-mocked-openai"),
        context={"creative_provider": "openai", "creative_model": "stub-model"},
    )

    assert result["status"] == WorkflowStatus.AWAITING_IDEA_SELECTION
    assert result["__interrupt__"][0].value["type"] == "IDEA_SELECTION_REQUIRED"
    assert result["creative_ideas"][0].creative_idea_id == "idea_openai_stub_1"
    assert result.get("script_draft") is None
    assert result["model_call_records"][0].provider == "openai"

import os

import pytest

from tk_script_agent_lab.providers import OpenAIScriptProvider, ScriptGenerationRequest

from tests.unit_tests.phase_1b_helpers import load_phase_1b


def _live_enabled() -> bool:
    return bool(
        os.environ.get("RUN_OPENAI_SCRIPT_INTEGRATION") == "1"
        and os.environ.get("OPENAI_API_KEY")
        and os.environ.get("OPENAI_MODEL")
    )


@pytest.mark.skipif(
    not _live_enabled(),
    reason=(
        "OpenAI script live integration requires RUN_OPENAI_SCRIPT_INTEGRATION=1, "
        "OPENAI_API_KEY, and OPENAI_MODEL."
    ),
)
def test_openai_script_live_generates_one_script() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = OpenAIScriptProvider(model=os.environ["OPENAI_MODEL"])

    result = provider.generate_script(
        ScriptGenerationRequest(
            product_profile=workflow_input.product_profile,
            product_facts=workflow_input.product_facts,
            selling_points=workflow_input.selling_points,
            reference_insights=fixtures.reference_insights,
            selected_idea=fixtures.creative_ideas[0],
        )
    )

    assert result.script_draft.creative_idea_id == fixtures.creative_ideas[0].creative_idea_id
    assert result.model_call_record.operation == "generate_script"
    assert result.model_call_record.status == "SUCCESS"

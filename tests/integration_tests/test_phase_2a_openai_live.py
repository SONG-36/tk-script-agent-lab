import os

import pytest

from tk_script_agent_lab.providers import OpenAICreativeProvider
from tk_script_agent_lab.golden_case import load_golden_case
from tk_script_agent_lab.providers import CreativeGenerationRequest
from tests.unit_tests.phase_1c_helpers import studio_input_path


@pytest.mark.skipif(
    not (
        os.environ.get("RUN_OPENAI_INTEGRATION") == "1"
        and os.environ.get("OPENAI_API_KEY")
        and os.environ.get("OPENAI_MODEL")
    ),
    reason="OpenAI live integration requires RUN_OPENAI_INTEGRATION=1, OPENAI_API_KEY, and OPENAI_MODEL.",
)
def test_phase_2a_openai_live_generates_creative_ideas() -> None:
    provider = OpenAICreativeProvider(model=os.environ["OPENAI_MODEL"])

    workflow_input, fixtures, _reviews = load_golden_case(studio_input_path().parent)
    result = provider.generate_creative_ideas(
        CreativeGenerationRequest(
            product_profile=workflow_input.product_profile,
            product_facts=workflow_input.product_facts,
            selling_points=workflow_input.selling_points,
            reference_insights=fixtures.reference_insights,
            idea_count=workflow_input.idea_count,
        )
    )

    assert len(result.creative_ideas) == 2
    assert result.model_call_record.provider == "openai"

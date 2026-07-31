import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(
    os.environ.get("RUN_PHASE_3A_CREATIVE_AB") != "1"
    or not os.environ.get("OPENAI_API_KEY")
    or not os.environ.get("OPENAI_MODEL"),
    reason="Phase 3A live A/B demo requires explicit env opt-in and OpenAI credentials.",
)
def test_phase_3a_creative_ab_demo_live_reaches_interrupt() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_phase_3a_creative_ab_demo.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "IDEA_SELECTION_REQUIRED" in result.stdout
    assert "script_draft_is_null" in result.stdout

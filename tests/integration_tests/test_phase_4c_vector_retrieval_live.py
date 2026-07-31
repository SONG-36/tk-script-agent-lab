import os

import pytest

from scripts.run_phase_4c_vector_retrieval_demo import main


@pytest.mark.skipif(
    os.environ.get("RUN_PHASE_4C_VECTOR_LIVE") != "1"
    or not os.environ.get("OPENAI_API_KEY")
    or not os.environ.get("OPENAI_EMBEDDING_MODEL"),
    reason="Phase 4C live vector retrieval requires explicit opt-in and OpenAI embedding config.",
)
def test_phase_4c_vector_retrieval_live() -> None:
    assert main(
        [
            "--confirm-live",
            "--embedding-model",
            os.environ["OPENAI_EMBEDDING_MODEL"],
            "--query",
            "cup holder crumbs",
            "--target-market",
            "US",
            "--product-category",
            "car vacuum cleaner",
            "--stage",
            "creative",
            "--limit",
            "3",
        ]
    ) == 0

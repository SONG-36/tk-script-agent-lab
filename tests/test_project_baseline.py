import json
from pathlib import Path


def test_package_imports() -> None:
    import tk_script_agent_lab

    assert tk_script_agent_lab.__version__ == "0.0.0"


def test_golden_case_json_files_load() -> None:
    case_dir = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "golden_cases"
        / "car_vacuum_v1"
    )
    json_files = [
        "product_profile.json",
        "product_facts.json",
        "selling_points.json",
        "reference_videos.json",
        "reference_insights.json",
        "creative_ideas.json",
        "script_drafts.json",
        "review_decisions.json",
        "workflow_input.json",
    ]

    for filename in json_files:
        with (case_dir / filename).open(encoding="utf-8") as file:
            payload = json.load(file)

        assert payload

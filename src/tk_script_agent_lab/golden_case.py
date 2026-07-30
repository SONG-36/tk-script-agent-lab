from pathlib import Path
import json

from pydantic import BaseModel, ConfigDict, Field

from tk_script_agent_lab.domain import (
    CreativeIdea,
    ProductFact,
    ProductProfile,
    ReferenceInsight,
    ReferenceVideo,
    ReviewDecision,
    ScriptDraft,
    SellingPoint,
)
from tk_script_agent_lab.providers import FakeProviderFixtures
from tk_script_agent_lab.workflow import WorkflowInput


class _WorkflowInputManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    idea_count: int = Field(ge=1)
    product_profile_file: str
    product_facts_file: str
    selling_points_file: str
    reference_videos_file: str


def load_golden_case(
    case_directory: Path,
) -> tuple[WorkflowInput, FakeProviderFixtures, list[ReviewDecision]]:
    case_root = case_directory.resolve()
    manifest = _WorkflowInputManifest.model_validate(
        _load_json(_safe_child(case_root, "workflow_input.json"))
    )

    product_profile = ProductProfile.model_validate(
        _load_json(_safe_child(case_root, manifest.product_profile_file))
    )
    product_facts = [
        ProductFact.model_validate(item)
        for item in _load_json(_safe_child(case_root, manifest.product_facts_file))[
            "product_facts"
        ]
    ]
    selling_points = [
        SellingPoint.model_validate(item)
        for item in _load_json(_safe_child(case_root, manifest.selling_points_file))[
            "selling_points"
        ]
    ]
    reference_videos = [
        ReferenceVideo.model_validate(item)
        for item in _load_json(_safe_child(case_root, manifest.reference_videos_file))[
            "reference_videos"
        ]
    ]
    reference_insights = [
        ReferenceInsight.model_validate(item)
        for item in _load_json(_safe_child(case_root, "reference_insights.json"))[
            "reference_insights"
        ]
    ]
    creative_ideas = [
        CreativeIdea.model_validate(item)
        for item in _load_json(_safe_child(case_root, "creative_ideas.json"))[
            "creative_ideas"
        ]
    ]
    script_drafts = [
        ScriptDraft.model_validate(item)
        for item in _load_json(_safe_child(case_root, "script_drafts.json"))[
            "script_drafts"
        ]
    ]
    review_decisions = [
        ReviewDecision.model_validate(item)
        for item in _load_json(_safe_child(case_root, "review_decisions.json"))[
            "review_decisions"
        ]
    ]

    workflow_input = WorkflowInput(
        run_id=manifest.run_id,
        product_profile=product_profile,
        product_facts=product_facts,
        selling_points=selling_points,
        reference_videos=reference_videos,
        idea_count=manifest.idea_count,
    )
    fixtures = FakeProviderFixtures(
        reference_insights=reference_insights,
        creative_ideas=creative_ideas,
        script_drafts=script_drafts,
    )
    return workflow_input, fixtures, review_decisions


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _safe_child(case_root: Path, filename: str) -> Path:
    path = (case_root / filename).resolve()
    if case_root not in path.parents and path != case_root:
        raise ValueError(f"Refusing to read outside case directory: {filename}")
    return path

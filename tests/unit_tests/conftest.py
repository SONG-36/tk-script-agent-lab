from collections.abc import Iterator
from pathlib import Path
import json

import pytest

from tk_script_agent_lab.domain import (
    CreativeIdea,
    DomainDataset,
    ProductFact,
    ProductProfile,
    ReferenceInsight,
    ReferencePlatform,
    ReferenceVideo,
    ReviewDecision,
    ReviewDecisionType,
    ScriptDraft,
    ScriptScene,
    SellingPoint,
    SourceUsage,
    VerificationStatus,
)


def make_product_profile() -> ProductProfile:
    return ProductProfile(
        product_id="prod_1",
        product_name="Fixture Car Vacuum",
        category="car vacuum cleaner",
        target_market="schema tests",
        target_audiences=["Car owners"],
        usage_scenarios=["Car interior cleanup"],
        prohibited_claims=["No unverified suction claims"],
        notes=None,
    )


def make_verified_fact(fact_id: str = "fact_1", product_id: str = "prod_1") -> ProductFact:
    return ProductFact(
        fact_id=fact_id,
        product_id=product_id,
        field_name="category",
        value="car vacuum cleaner",
        unit=None,
        status=VerificationStatus.VERIFIED,
        source_ids=["source_1"],
        notes=None,
    )


def make_unverified_fact(
    fact_id: str = "fact_unverified",
    product_id: str = "prod_1",
) -> ProductFact:
    return ProductFact(
        fact_id=fact_id,
        product_id=product_id,
        field_name="power_watts",
        value=None,
        unit="W",
        status=VerificationStatus.UNVERIFIED,
        source_ids=[],
        notes=None,
    )


def make_rejected_fact(fact_id: str = "fact_rejected") -> ProductFact:
    return ProductFact(
        fact_id=fact_id,
        product_id="prod_1",
        field_name="claim",
        value="rejected claim",
        unit=None,
        status=VerificationStatus.REJECTED,
        source_ids=["source_1"],
        notes=None,
    )


def make_selling_point(
    selling_point_id: str = "sp_1",
    fact_ids: list[str] | None = None,
    product_id: str = "prod_1",
) -> SellingPoint:
    return SellingPoint(
        selling_point_id=selling_point_id,
        product_id=product_id,
        title="Interior cleanup",
        description="Focus on the car interior cleanup context.",
        fact_ids=fact_ids or ["fact_1"],
        target_pain_points=["Small debris in a car"],
        priority=3,
    )


def make_reference_video(reference_video_id: str = "ref_1") -> ReferenceVideo:
    return ReferenceVideo(
        reference_video_id=reference_video_id,
        platform=ReferencePlatform.LOCAL,
        url=None,
        title="Local fixture",
        transcript=None,
        creator_name=None,
        published_at=None,
        notes=None,
    )


def make_reference_insight(
    insight_id: str = "insight_1",
    reference_video_id: str = "ref_1",
) -> ReferenceInsight:
    return ReferenceInsight(
        insight_id=insight_id,
        reference_video_id=reference_video_id,
        insight_type="HOOK",
        description="Show the mess first.",
        evidence_text=None,
        start_second=0,
        end_second=2,
    )


def make_source_usage(
    source_usage_id: str,
    source_type: str,
    source_id: str,
) -> SourceUsage:
    return SourceUsage(
        source_usage_id=source_usage_id,
        source_type=source_type,  # type: ignore[arg-type]
        source_id=source_id,
        usage_purpose="Support test output.",
    )


def make_creative_idea(
    creative_idea_id: str = "idea_1",
    product_id: str = "prod_1",
) -> CreativeIdea:
    return CreativeIdea(
        creative_idea_id=creative_idea_id,
        product_id=product_id,
        title="Before after cleanup",
        hook="Show the car mess.",
        concept_summary="Use verified context only.",
        target_audience="Car owners",
        source_usages=[
            make_source_usage("usage_1", "selling_point", "sp_1"),
            make_source_usage("usage_2", "reference_insight", "insight_1"),
        ],
        risk_notes=[],
    )


def make_script_draft(
    script_id: str = "script_1",
    product_id: str = "prod_1",
    creative_idea_id: str = "idea_1",
) -> ScriptDraft:
    return ScriptDraft(
        script_id=script_id,
        product_id=product_id,
        creative_idea_id=creative_idea_id,
        title="Schema script",
        scenes=[
            ScriptScene(
                scene_id="scene_1",
                sequence=1,
                visual="Show debris.",
                action="Frame the problem.",
                voiceover=None,
                on_screen_text=None,
                duration_seconds=2.0,
            )
        ],
        caption=None,
        cta=None,
        source_usages=[
            make_source_usage("usage_script_1", "product_fact", "fact_1"),
        ],
    )


def make_review_decision(
    review_id: str = "review_1",
    target_type: str = "script_draft",
    target_id: str = "script_1",
) -> ReviewDecision:
    return ReviewDecision(
        review_id=review_id,
        target_type=target_type,  # type: ignore[arg-type]
        target_id=target_id,
        decision=ReviewDecisionType.PENDING,
        reviewer=None,
        comment=None,
    )


@pytest.fixture
def valid_dataset() -> Iterator[DomainDataset]:
    yield DomainDataset(
        product_profile=make_product_profile(),
        product_facts=[make_verified_fact(), make_unverified_fact()],
        selling_points=[make_selling_point()],
        reference_videos=[make_reference_video()],
        reference_insights=[make_reference_insight()],
        creative_ideas=[make_creative_idea()],
        script_drafts=[make_script_draft()],
        review_decisions=[make_review_decision()],
    )


def load_golden_case_dataset() -> DomainDataset:
    case_dir = Path(__file__).resolve().parents[2] / "data" / "golden_cases" / "car_vacuum_v1"

    def load_json(filename: str) -> dict[str, object]:
        with (case_dir / filename).open(encoding="utf-8") as file:
            return json.load(file)

    return DomainDataset(
        product_profile=ProductProfile.model_validate(load_json("product_profile.json")),
        product_facts=[
            ProductFact.model_validate(item)
            for item in load_json("product_facts.json")["product_facts"]  # type: ignore[index]
        ],
        selling_points=[
            SellingPoint.model_validate(item)
            for item in load_json("selling_points.json")["selling_points"]  # type: ignore[index]
        ],
        reference_videos=[
            ReferenceVideo.model_validate(item)
            for item in load_json("reference_videos.json")["reference_videos"]  # type: ignore[index]
        ],
        reference_insights=[
            ReferenceInsight.model_validate(item)
            for item in load_json("reference_insights.json")["reference_insights"]  # type: ignore[index]
        ],
        creative_ideas=[
            CreativeIdea.model_validate(item)
            for item in load_json("creative_ideas.json")["creative_ideas"]  # type: ignore[index]
        ],
        script_drafts=[
            ScriptDraft.model_validate(item)
            for item in load_json("script_drafts.json")["script_drafts"]  # type: ignore[index]
        ],
        review_decisions=[
            ReviewDecision.model_validate(item)
            for item in load_json("review_decisions.json")["review_decisions"]  # type: ignore[index]
        ],
    )

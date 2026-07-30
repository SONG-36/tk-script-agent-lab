from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from tk_script_agent_lab.domain.creative import CreativeIdea, SourceUsage
from tk_script_agent_lab.domain.enums import VerificationStatus
from tk_script_agent_lab.domain.errors import ValidationError
from tk_script_agent_lab.domain.product import ProductFact, ProductProfile, SellingPoint
from tk_script_agent_lab.domain.reference import ReferenceInsight, ReferenceVideo
from tk_script_agent_lab.domain.review import ReviewDecision
from tk_script_agent_lab.domain.script import ScriptDraft


class DomainDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_profile: ProductProfile
    product_facts: list[ProductFact]
    selling_points: list[SellingPoint]
    reference_videos: list[ReferenceVideo]
    reference_insights: list[ReferenceInsight]
    creative_ideas: list[CreativeIdea]
    script_drafts: list[ScriptDraft]
    review_decisions: list[ReviewDecision]


def validate_domain_dataset(dataset: DomainDataset) -> list[ValidationError]:
    errors: list[ValidationError] = []

    fact_by_id = {fact.fact_id: fact for fact in dataset.product_facts}
    selling_point_by_id = {
        selling_point.selling_point_id: selling_point
        for selling_point in dataset.selling_points
    }
    reference_video_by_id = {
        video.reference_video_id: video for video in dataset.reference_videos
    }
    reference_insight_by_id = {
        insight.insight_id: insight for insight in dataset.reference_insights
    }
    creative_idea_by_id = {
        idea.creative_idea_id: idea for idea in dataset.creative_ideas
    }
    script_draft_by_id = {
        script.script_id: script for script in dataset.script_drafts
    }

    errors.extend(
        _duplicate_id_errors(
            "ProductFact",
            ((fact.fact_id, fact.fact_id) for fact in dataset.product_facts),
        )
    )
    errors.extend(
        _duplicate_id_errors(
            "SellingPoint",
            (
                (selling_point.selling_point_id, selling_point.selling_point_id)
                for selling_point in dataset.selling_points
            ),
        )
    )
    errors.extend(
        _duplicate_id_errors(
            "ReferenceVideo",
            (
                (video.reference_video_id, video.reference_video_id)
                for video in dataset.reference_videos
            ),
        )
    )
    errors.extend(
        _duplicate_id_errors(
            "ReferenceInsight",
            ((insight.insight_id, insight.insight_id) for insight in dataset.reference_insights),
        )
    )
    errors.extend(
        _duplicate_id_errors(
            "CreativeIdea",
            ((idea.creative_idea_id, idea.creative_idea_id) for idea in dataset.creative_ideas),
        )
    )
    errors.extend(
        _duplicate_id_errors(
            "ScriptDraft",
            ((script.script_id, script.script_id) for script in dataset.script_drafts),
        )
    )
    errors.extend(
        _duplicate_id_errors(
            "ReviewDecision",
            ((review.review_id, review.review_id) for review in dataset.review_decisions),
        )
    )

    product_id = dataset.product_profile.product_id
    for fact in dataset.product_facts:
        if fact.product_id != product_id:
            errors.append(
                _error(
                    "PRODUCT_ID_MISMATCH",
                    "ProductFact belongs to a different product.",
                    "ProductFact",
                    fact.fact_id,
                    "product_id",
                    fact.product_id,
                )
            )
    for selling_point in dataset.selling_points:
        if selling_point.product_id != product_id:
            errors.append(
                _error(
                    "PRODUCT_ID_MISMATCH",
                    "SellingPoint belongs to a different product.",
                    "SellingPoint",
                    selling_point.selling_point_id,
                    "product_id",
                    selling_point.product_id,
                )
            )
    for idea in dataset.creative_ideas:
        if idea.product_id != product_id:
            errors.append(
                _error(
                    "PRODUCT_ID_MISMATCH",
                    "CreativeIdea belongs to a different product.",
                    "CreativeIdea",
                    idea.creative_idea_id,
                    "product_id",
                    idea.product_id,
                )
            )
    for script in dataset.script_drafts:
        if script.product_id != product_id:
            errors.append(
                _error(
                    "PRODUCT_ID_MISMATCH",
                    "ScriptDraft belongs to a different product.",
                    "ScriptDraft",
                    script.script_id,
                    "product_id",
                    script.product_id,
                )
            )

    for selling_point in dataset.selling_points:
        for fact_id in selling_point.fact_ids:
            fact = fact_by_id.get(fact_id)
            if fact is None:
                errors.append(
                    _error(
                        "FACT_NOT_FOUND",
                        "SellingPoint references a missing ProductFact.",
                        "SellingPoint",
                        selling_point.selling_point_id,
                        "fact_ids",
                        fact_id,
                    )
                )
                continue
            errors.extend(
                _fact_availability_errors(
                    fact,
                    "SellingPoint",
                    selling_point.selling_point_id,
                    "fact_ids",
                    fact_id,
                )
            )
            if fact.product_id != selling_point.product_id:
                errors.append(
                    _error(
                        "PRODUCT_ID_MISMATCH",
                        "SellingPoint references a ProductFact for a different product.",
                        "SellingPoint",
                        selling_point.selling_point_id,
                        "fact_ids",
                        fact_id,
                    )
                )

    for insight in dataset.reference_insights:
        if insight.reference_video_id not in reference_video_by_id:
            errors.append(
                _error(
                    "REFERENCE_VIDEO_NOT_FOUND",
                    "ReferenceInsight references a missing ReferenceVideo.",
                    "ReferenceInsight",
                    insight.insight_id,
                    "reference_video_id",
                    insight.reference_video_id,
                )
            )

    for idea in dataset.creative_ideas:
        for usage in idea.source_usages:
            errors.extend(
                _validate_source_usage(
                    usage,
                    owner_type="CreativeIdea",
                    owner_id=idea.creative_idea_id,
                    owner_product_id=idea.product_id,
                    fact_by_id=fact_by_id,
                    selling_point_by_id=selling_point_by_id,
                    reference_insight_by_id=reference_insight_by_id,
                    missing_as_generic_source=False,
                )
            )

    for script in dataset.script_drafts:
        idea = creative_idea_by_id.get(script.creative_idea_id)
        if idea is None:
            errors.append(
                _error(
                    "CREATIVE_IDEA_NOT_FOUND",
                    "ScriptDraft references a missing CreativeIdea.",
                    "ScriptDraft",
                    script.script_id,
                    "creative_idea_id",
                    script.creative_idea_id,
                )
            )
        elif idea.product_id != script.product_id:
            errors.append(
                _error(
                    "PRODUCT_ID_MISMATCH",
                    "ScriptDraft references a CreativeIdea for a different product.",
                    "ScriptDraft",
                    script.script_id,
                    "creative_idea_id",
                    script.creative_idea_id,
                )
            )
        for usage in script.source_usages:
            errors.extend(
                _validate_source_usage(
                    usage,
                    owner_type="ScriptDraft",
                    owner_id=script.script_id,
                    owner_product_id=script.product_id,
                    fact_by_id=fact_by_id,
                    selling_point_by_id=selling_point_by_id,
                    reference_insight_by_id=reference_insight_by_id,
                    missing_as_generic_source=True,
                )
            )

    for review in dataset.review_decisions:
        if (
            review.target_type == "creative_idea"
            and review.target_id not in creative_idea_by_id
        ):
            errors.append(
                _error(
                    "CREATIVE_IDEA_NOT_FOUND",
                    "ReviewDecision references a missing CreativeIdea.",
                    "ReviewDecision",
                    review.review_id,
                    "target_id",
                    review.target_id,
                )
            )
        if review.target_type == "script_draft" and review.target_id not in script_draft_by_id:
            errors.append(
                _error(
                    "SCRIPT_DRAFT_NOT_FOUND",
                    "ReviewDecision references a missing ScriptDraft.",
                    "ReviewDecision",
                    review.review_id,
                    "target_id",
                    review.target_id,
                )
            )

    return errors


def _duplicate_id_errors(
    object_type: str,
    ids: Iterable[tuple[str, str]],
) -> list[ValidationError]:
    seen: set[str] = set()
    errors: list[ValidationError] = []
    for object_id, related_id in ids:
        if related_id in seen:
            errors.append(
                _error(
                    "DUPLICATE_ID",
                    f"{object_type} id is duplicated.",
                    object_type,
                    object_id,
                    "id",
                    related_id,
                )
            )
        seen.add(related_id)
    return errors


def _validate_source_usage(
    usage: SourceUsage,
    *,
    owner_type: str,
    owner_id: str,
    owner_product_id: str,
    fact_by_id: dict[str, ProductFact],
    selling_point_by_id: dict[str, SellingPoint],
    reference_insight_by_id: dict[str, ReferenceInsight],
    missing_as_generic_source: bool,
) -> list[ValidationError]:
    errors: list[ValidationError] = []

    if usage.source_type == "product_fact":
        fact = fact_by_id.get(usage.source_id)
        if fact is None:
            code = "SOURCE_NOT_FOUND" if missing_as_generic_source else "FACT_NOT_FOUND"
            errors.append(
                _error(
                    code,
                    f"{owner_type} references a missing ProductFact.",
                    owner_type,
                    owner_id,
                    "source_usages",
                    usage.source_id,
                )
            )
            return errors
        errors.extend(
            _fact_availability_errors(
                fact,
                owner_type,
                owner_id,
                "source_usages",
                usage.source_id,
            )
        )
        if fact.product_id != owner_product_id:
            errors.append(
                _error(
                    "PRODUCT_ID_MISMATCH",
                    f"{owner_type} references a ProductFact for a different product.",
                    owner_type,
                    owner_id,
                    "source_usages",
                    usage.source_id,
                )
            )
    elif usage.source_type == "selling_point":
        selling_point = selling_point_by_id.get(usage.source_id)
        if selling_point is None:
            code = "SOURCE_NOT_FOUND" if missing_as_generic_source else "SELLING_POINT_NOT_FOUND"
            errors.append(
                _error(
                    code,
                    f"{owner_type} references a missing SellingPoint.",
                    owner_type,
                    owner_id,
                    "source_usages",
                    usage.source_id,
                )
            )
            return errors
        if selling_point.product_id != owner_product_id:
            errors.append(
                _error(
                    "PRODUCT_ID_MISMATCH",
                    f"{owner_type} references a SellingPoint for a different product.",
                    owner_type,
                    owner_id,
                    "source_usages",
                    usage.source_id,
                )
            )
    elif usage.source_type == "reference_insight":
        if usage.source_id not in reference_insight_by_id:
            code = "SOURCE_NOT_FOUND" if missing_as_generic_source else "REFERENCE_INSIGHT_NOT_FOUND"
            errors.append(
                _error(
                    code,
                    f"{owner_type} references a missing ReferenceInsight.",
                    owner_type,
                    owner_id,
                    "source_usages",
                    usage.source_id,
                )
            )
    else:
        errors.append(
            _error(
                "SOURCE_NOT_FOUND",
                f"{owner_type} uses an unsupported source type.",
                owner_type,
                owner_id,
                "source_usages",
                usage.source_id,
            )
        )

    return errors


def _fact_availability_errors(
    fact: ProductFact,
    owner_type: str,
    owner_id: str,
    field: str,
    related_id: str,
) -> list[ValidationError]:
    if fact.status == VerificationStatus.REJECTED:
        return [
            _error(
                "FACT_REJECTED",
                "Referenced ProductFact is rejected.",
                owner_type,
                owner_id,
                field,
                related_id,
            )
        ]
    if fact.status != VerificationStatus.VERIFIED:
        return [
            _error(
                "FACT_NOT_VERIFIED",
                "Referenced ProductFact is not verified.",
                owner_type,
                owner_id,
                field,
                related_id,
            )
        ]
    return []


def _error(
    code: str,
    message: str,
    object_type: str,
    object_id: str | None,
    field: str | None,
    related_id: str | None,
) -> ValidationError:
    return ValidationError(
        code=code,
        message=message,
        object_type=object_type,
        object_id=object_id,
        field=field,
        related_id=related_id,
    )

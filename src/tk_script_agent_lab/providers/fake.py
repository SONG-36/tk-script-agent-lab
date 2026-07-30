from tk_script_agent_lab.domain import (
    CreativeIdea,
    ProductFact,
    ReferenceInsight,
    ScriptDraft,
    SellingPoint,
    VerificationStatus,
)
from tk_script_agent_lab.domain.errors import ValidationError
from tk_script_agent_lab.providers.base import (
    CreativeGenerationRequest,
    ProviderOutputError,
    ReferenceAnalysisRequest,
    ScriptGenerationRequest,
)
from tk_script_agent_lab.providers.fixtures import FakeProviderFixtures


class FakeContentProvider:
    def __init__(self, fixtures: FakeProviderFixtures) -> None:
        self._fixtures = fixtures.model_copy(deep=True)

    def analyze_references(
        self,
        request: ReferenceAnalysisRequest,
    ) -> list[ReferenceInsight]:
        video_ids = {video.reference_video_id for video in request.reference_videos}
        insights = [
            insight
            for insight in self._fixtures.reference_insights
            if insight.reference_video_id in video_ids
        ]
        return [_clone(insight) for insight in insights]

    def generate_creative_ideas(
        self,
        request: CreativeGenerationRequest,
    ) -> list[CreativeIdea]:
        product_id = request.product_profile.product_id
        candidates = [
            idea
            for idea in self._fixtures.creative_ideas
            if idea.product_id == product_id
        ]
        valid_candidates = [
            idea for idea in candidates if _idea_is_eligible(idea, request)
        ]
        selected = valid_candidates[: request.idea_count]
        if not selected:
            raise ProviderOutputError(
                ValidationError(
                    code="NO_CREATIVE_IDEAS",
                    message="Fake provider has no eligible creative ideas for this request.",
                    object_type="FakeContentProvider",
                    object_id=None,
                    field="creative_ideas",
                    related_id=product_id,
                )
            )
        return [_clone(idea) for idea in selected]

    def generate_script(
        self,
        request: ScriptGenerationRequest,
    ) -> ScriptDraft:
        selected_idea_id = request.selected_idea.creative_idea_id
        product_id = request.product_profile.product_id
        for script in self._fixtures.script_drafts:
            if script.creative_idea_id != selected_idea_id:
                continue
            if script.product_id != product_id:
                raise ProviderOutputError(
                    ValidationError(
                        code="SCRIPT_PRODUCT_MISMATCH",
                        message="Fake provider script belongs to a different product.",
                        object_type="ScriptDraft",
                        object_id=script.script_id,
                        field="product_id",
                        related_id=script.product_id,
                    )
                )
            return _clone(script)
        raise ProviderOutputError(
            ValidationError(
                code="SCRIPT_NOT_AVAILABLE",
                message="Fake provider has no script for the selected creative idea.",
                object_type="FakeContentProvider",
                object_id=None,
                field="script_drafts",
                related_id=selected_idea_id,
            )
        )


def _idea_is_eligible(
    idea: CreativeIdea,
    request: CreativeGenerationRequest,
) -> bool:
    fact_by_id = {fact.fact_id: fact for fact in request.product_facts}
    selling_point_by_id = {
        selling_point.selling_point_id: selling_point
        for selling_point in request.selling_points
    }
    insight_ids = {insight.insight_id for insight in request.reference_insights}

    if idea.product_id != request.product_profile.product_id:
        return False
    for usage in idea.source_usages:
        if usage.source_type == "product_fact":
            fact = fact_by_id.get(usage.source_id)
            if not _fact_is_verified(fact):
                return False
            if fact.product_id != request.product_profile.product_id:
                return False
        elif usage.source_type == "selling_point":
            selling_point = selling_point_by_id.get(usage.source_id)
            if not _selling_point_is_valid(selling_point, fact_by_id):
                return False
        elif usage.source_type == "reference_insight":
            if usage.source_id not in insight_ids:
                return False
    return True


def _fact_is_verified(fact: ProductFact | None) -> bool:
    return fact is not None and fact.status == VerificationStatus.VERIFIED


def _selling_point_is_valid(
    selling_point: SellingPoint | None,
    fact_by_id: dict[str, ProductFact],
) -> bool:
    if selling_point is None:
        return False
    return all(_fact_is_verified(fact_by_id.get(fact_id)) for fact_id in selling_point.fact_ids)


def _clone[T](model: T) -> T:
    return type(model).model_validate(model.model_dump(mode="json"))

import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import InsightType, ReferenceInsight, ReferencePlatform, ReferenceVideo


def test_reference_video_allows_missing_url() -> None:
    video = ReferenceVideo(
        reference_video_id="ref_1",
        platform=ReferencePlatform.LOCAL,
        url=None,
        title=None,
        transcript=None,
        creator_name=None,
        published_at=None,
        notes=None,
    )

    assert video.url is None


def test_reference_insight_time_range_is_valid() -> None:
    insight = ReferenceInsight(
        insight_id="insight_1",
        reference_video_id="ref_1",
        insight_type=InsightType.HOOK,
        description="Show mess first.",
        evidence_text=None,
        start_second=1.0,
        end_second=2.0,
    )

    assert insight.start_second == 1.0


def test_reference_insight_start_after_end_fails() -> None:
    with pytest.raises(PydanticValidationError):
        ReferenceInsight(
            insight_id="insight_1",
            reference_video_id="ref_1",
            insight_type=InsightType.HOOK,
            description="Show mess first.",
            evidence_text=None,
            start_second=3.0,
            end_second=2.0,
        )

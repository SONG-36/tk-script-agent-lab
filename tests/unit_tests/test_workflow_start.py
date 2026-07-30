from tk_script_agent_lab.domain import SellingPoint
from tk_script_agent_lab.providers import FakeContentProvider
from tk_script_agent_lab.workflow import WorkflowStatus, start_workflow

from phase_1b_helpers import (
    load_phase_1b,
    with_bad_creative_idea,
    with_bad_reference_insight,
)


class CountingProvider(FakeContentProvider):
    def __init__(self, fixtures) -> None:  # type: ignore[no-untyped-def]
        super().__init__(fixtures)
        self.reference_calls = 0
        self.idea_calls = 0

    def analyze_references(self, request):  # type: ignore[no-untyped-def]
        self.reference_calls += 1
        return super().analyze_references(request)

    def generate_creative_ideas(self, request):  # type: ignore[no-untyped-def]
        self.idea_calls += 1
        return super().generate_creative_ideas(request)


class InvalidInsightProvider(FakeContentProvider):
    def analyze_references(self, request):  # type: ignore[no-untyped-def]
        return self._fixtures.reference_insights  # type: ignore[attr-defined]


class InvalidIdeaProvider(FakeContentProvider):
    def generate_creative_ideas(self, request):  # type: ignore[no-untyped-def]
        return self._fixtures.creative_ideas  # type: ignore[attr-defined]


class CountingInvalidInsightProvider(CountingProvider):
    def analyze_references(self, request):  # type: ignore[no-untyped-def]
        self.reference_calls += 1
        return self._fixtures.reference_insights  # type: ignore[attr-defined]


def test_start_workflow_enters_awaiting_selection() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    state = start_workflow(workflow_input, FakeContentProvider(fixtures))

    assert state.status == WorkflowStatus.AWAITING_IDEA_SELECTION
    assert state.script_draft is None
    assert len(state.creative_ideas) >= 2


def test_start_workflow_step_records_are_continuous() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    state = start_workflow(workflow_input, FakeContentProvider(fixtures))

    assert [record.sequence for record in state.step_records] == list(
        range(1, len(state.step_records) + 1)
    )
    assert state.step_records[-1].step_name == "await_human_selection"
    assert state.step_records[-1].status == "WAITING"


def test_start_workflow_invalid_input_does_not_call_provider() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    bad_sp = SellingPoint(
        selling_point_id="sp_bad",
        product_id=workflow_input.product_profile.product_id,
        title="Bad",
        description="Bad missing fact.",
        fact_ids=["missing_fact"],
        target_pain_points=["Bad input"],
        priority=3,
    )
    invalid_input = workflow_input.model_copy(update={"selling_points": [bad_sp]}, deep=True)
    provider = CountingProvider(fixtures)

    state = start_workflow(invalid_input, provider)

    assert state.status == WorkflowStatus.INPUT_INVALID
    assert provider.reference_calls == 0
    assert provider.idea_calls == 0
    assert "WORKFLOW_INPUT_INVALID" in [error.code for error in state.validation_errors]


def test_start_workflow_invalid_provider_insight_stops_before_ideas() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = CountingInvalidInsightProvider(with_bad_reference_insight(fixtures))

    state = start_workflow(workflow_input, provider)

    assert state.status == WorkflowStatus.FAILED
    assert provider.reference_calls == 1
    assert provider.idea_calls == 0
    assert "REFERENCE_VIDEO_NOT_FOUND" in [error.code for error in state.validation_errors]


def test_start_workflow_invalid_provider_idea_stops_before_human_gate() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    state = start_workflow(workflow_input, InvalidIdeaProvider(with_bad_creative_idea(fixtures)))

    assert state.status == WorkflowStatus.FAILED
    assert state.script_draft is None
    assert "FACT_NOT_FOUND" in [error.code for error in state.validation_errors]


def test_start_workflow_does_not_modify_workflow_input() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    before = workflow_input.model_dump(mode="json")

    start_workflow(workflow_input, FakeContentProvider(fixtures))

    assert workflow_input.model_dump(mode="json") == before


def test_start_workflow_multiple_runs_are_consistent() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    provider = FakeContentProvider(fixtures)

    first = start_workflow(workflow_input, provider)
    second = start_workflow(workflow_input, provider)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")

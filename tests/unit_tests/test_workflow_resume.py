from tk_script_agent_lab.providers import FakeContentProvider
from tk_script_agent_lab.workflow import WorkflowStatus, resume_with_review

from phase_1b_helpers import (
    approved_review,
    fixtures_with_script,
    load_phase_1b,
    start_golden_workflow,
)


def test_script_draft_binds_to_selected_idea() -> None:
    state, provider, _reviews = start_golden_workflow()
    selected_id = state.creative_ideas[1].creative_idea_id

    completed = resume_with_review(state, approved_review(selected_id), provider)

    assert completed.script_draft is not None
    assert completed.script_draft.creative_idea_id == selected_id


def test_script_draft_product_id_matches_input() -> None:
    state, provider, _reviews = start_golden_workflow()

    completed = resume_with_review(
        state,
        approved_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )

    assert completed.script_draft is not None
    assert completed.script_draft.product_id == state.workflow_input.product_profile.product_id


def test_script_source_usages_are_valid() -> None:
    state, provider, _reviews = start_golden_workflow()

    completed = resume_with_review(
        state,
        approved_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )

    assert completed.status == WorkflowStatus.COMPLETED
    assert completed.validation_errors == []


def test_provider_wrong_script_idea_id_is_blocked() -> None:
    workflow_input, fixtures, _reviews = load_phase_1b()
    state = start_golden_workflow()[0]
    wrong_script = fixtures.script_drafts[0].model_copy(
        update={"creative_idea_id": "idea_driver_cleanup_moment"},
        deep=True,
    )
    provider = FakeContentProvider(fixtures_with_script(fixtures, wrong_script))

    result = resume_with_review(
        state,
        approved_review("idea_before_after_cleanup"),
        provider,
    )

    assert workflow_input.product_profile.product_id
    assert "SCRIPT_NOT_AVAILABLE" in [error.code for error in result.validation_errors]


def test_provider_wrong_script_product_id_is_blocked() -> None:
    _workflow_input, fixtures, _reviews = load_phase_1b()
    state = start_golden_workflow()[0]
    wrong_script = fixtures.script_drafts[0].model_copy(
        update={"product_id": "other_product"},
        deep=True,
    )
    provider = FakeContentProvider(fixtures_with_script(fixtures, wrong_script))

    result = resume_with_review(
        state,
        approved_review("idea_before_after_cleanup"),
        provider,
    )

    assert "SCRIPT_PRODUCT_MISMATCH" in [error.code for error in result.validation_errors]


def test_provider_without_matching_script_fails() -> None:
    _workflow_input, fixtures, _reviews = load_phase_1b()
    state = start_golden_workflow()[0]
    provider = FakeContentProvider(fixtures.model_copy(update={"script_drafts": []}, deep=True))

    result = resume_with_review(
        state,
        approved_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )

    assert result.status == WorkflowStatus.FAILED
    assert "SCRIPT_NOT_AVAILABLE" in [error.code for error in result.validation_errors]


def test_completed_status_has_no_blocking_errors() -> None:
    state, provider, _reviews = start_golden_workflow()

    completed = resume_with_review(
        state,
        approved_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )

    assert completed.status == WorkflowStatus.COMPLETED
    assert completed.validation_errors == []

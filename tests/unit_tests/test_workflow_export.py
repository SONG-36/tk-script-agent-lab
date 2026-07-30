import json

import pytest

from tk_script_agent_lab.workflow import (
    WorkflowStatus,
    export_completed_workflow,
    resume_with_review,
)

from phase_1b_helpers import approved_review, start_golden_workflow


def completed_state():
    state, provider, _reviews = start_golden_workflow()
    return resume_with_review(
        state,
        approved_review(state.creative_ideas[0].creative_idea_id),
        provider,
    )


def test_completed_state_can_export(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = completed_state()

    json_path, markdown_path = export_completed_workflow(state, tmp_path)

    assert json_path.name == "workflow_result.json"
    assert markdown_path.name == "script.md"
    assert json_path.exists()
    assert markdown_path.exists()


def test_non_completed_state_rejects_export(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state, _provider, _reviews = start_golden_workflow()

    with pytest.raises(ValueError, match="EXPORT_REQUIRES_COMPLETED_STATE"):
        export_completed_workflow(state, tmp_path)


def test_exported_json_can_reload(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = completed_state()
    json_path, _markdown_path = export_completed_workflow(state, tmp_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["status"] == WorkflowStatus.COMPLETED
    assert payload["step_records"][-1]["step_name"] == "export_result"


def test_exported_markdown_contains_idea_scene_and_sources(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = completed_state()
    _json_path, markdown_path = export_completed_workflow(state, tmp_path)

    content = markdown_path.read_text(encoding="utf-8")

    assert "选中创意" in content
    assert "Scene 1" in content
    assert "SourceUsage" in content


def test_export_does_not_modify_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = completed_state()
    before = state.model_dump(mode="json")

    export_completed_workflow(state, tmp_path)

    assert state.model_dump(mode="json") == before

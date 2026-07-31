import json
from types import SimpleNamespace

import pytest

from scripts import run_phase_3a_creative_ab_demo as demo
from scripts.run_phase_3a_creative_ab_demo import _summarize, _validation_error_detail
from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.workflow import WorkflowStatus


def test_validation_error_detail_preserves_related_id() -> None:
    error = ValidationError(
        code="MODEL_OUTPUT_SOURCE_INVALID",
        message="Model output referenced a source_id outside the allowed set.",
        object_type="OpenAICreativeProvider",
        object_id=None,
        field="source_usages",
        related_id="ck_hook_visible_micro_mess",
    )

    assert _validation_error_detail(error) == {
        "code": "MODEL_OUTPUT_SOURCE_INVALID",
        "field": "source_usages",
        "related_id": "ck_hook_visible_micro_mess",
        "message": "Model output referenced a source_id outside the allowed set.",
    }


def test_validation_error_detail_uses_null_for_missing_related_id() -> None:
    error = ValidationError(
        code="MODEL_OUTPUT_SOURCE_INVALID",
        message="Each model-generated idea must reference at least one reference insight.",
        object_type="OpenAICreativeProvider",
        object_id=None,
        field="source_usages",
        related_id=None,
    )

    payload = _validation_error_detail(error)

    assert payload["related_id"] is None
    assert json.loads(json.dumps(payload))["related_id"] is None


def test_summary_keeps_validation_errors_and_adds_safe_details() -> None:
    error = ValidationError(
        code="MODEL_OUTPUT_SOURCE_INVALID",
        message="Model output referenced a source_id outside the allowed set.",
        object_type="OpenAICreativeProvider",
        object_id=None,
        field="source_usages",
        related_id="missing_source",
    )
    result = {
        "status": WorkflowStatus.FAILED,
        "validation_errors": [error],
        "creative_ideas": [],
        "model_call_records": [],
        "raw_model_response": "RAW_MODEL_RESPONSE_SHOULD_NOT_APPEAR",
    }

    summary = _summarize(result)
    encoded = json.dumps(summary, ensure_ascii=False)

    assert summary["validation_errors"] == ["MODEL_OUTPUT_SOURCE_INVALID"]
    assert summary["validation_error_details"] == [
        {
            "code": "MODEL_OUTPUT_SOURCE_INVALID",
            "field": "source_usages",
            "related_id": "missing_source",
            "message": "Model output referenced a source_id outside the allowed set.",
        }
    ]
    assert "RAW_MODEL_RESPONSE_SHOULD_NOT_APPEAR" not in encoded


def fail_if_env_is_read() -> tuple[str | None, str | None]:
    raise AssertionError("OpenAI environment should not be read")


def test_help_does_not_read_env_or_run_variant(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(demo, "_openai_environment", fail_if_env_is_read)
    monkeypatch.setattr(
        demo,
        "_run_variant",
        lambda *args, **kwargs: pytest.fail("variant should not run for --help"),
    )

    with pytest.raises(SystemExit) as exc_info:
        demo.main(["--help"])

    assert exc_info.value.code == 0
    assert "--confirm-live" in capsys.readouterr().out


def test_missing_confirm_live_does_not_read_env_or_run_variant(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(demo, "_openai_environment", fail_if_env_is_read)
    monkeypatch.setattr(
        demo,
        "_run_variant",
        lambda *args, **kwargs: pytest.fail("variant should not run without confirmation"),
    )

    result = demo.main([])

    assert result == 2
    assert "--confirm-live" in capsys.readouterr().err


def test_control_mode_runs_only_control(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []
    _patch_safe_live_dependencies(monkeypatch, calls)

    result = demo.main(["--mode", "control", "--confirm-live"])
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert calls == ["phase-3a-control"]
    assert "control" in payload
    assert "treatment" not in payload


def test_treatment_mode_runs_only_treatment(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []
    _patch_safe_live_dependencies(monkeypatch, calls)

    result = demo.main(["--mode", "treatment", "--confirm-live"])
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert calls == ["phase-3a-treatment"]
    assert "control" not in payload
    assert "treatment" in payload


def test_both_mode_runs_control_and_treatment(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []
    _patch_safe_live_dependencies(monkeypatch, calls)

    result = demo.main(["--mode", "both", "--confirm-live"])
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert calls == ["phase-3a-control", "phase-3a-treatment"]
    assert "control" in payload
    assert "treatment" in payload


def test_invalid_mode_does_not_read_env_or_run_variant(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(demo, "_openai_environment", fail_if_env_is_read)
    monkeypatch.setattr(
        demo,
        "_run_variant",
        lambda *args, **kwargs: pytest.fail("variant should not run for invalid args"),
    )

    with pytest.raises(SystemExit) as exc_info:
        demo.main(["--mode", "invalid", "--confirm-live"])

    assert exc_info.value.code == 2


def _patch_safe_live_dependencies(monkeypatch, calls: list[str]) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        demo,
        "_openai_environment",
        lambda: ("test-placeholder-key", "test-placeholder-model"),
    )
    monkeypatch.setattr(
        demo,
        "_run_variant",
        lambda graph_input, *, thread_id, context: _fake_result(calls, thread_id),
    )


def _fake_result(calls: list[str], thread_id: str) -> dict:
    calls.append(thread_id)
    return {
        "status": WorkflowStatus.AWAITING_IDEA_SELECTION,
        "__interrupt__": [
            SimpleNamespace(value={"type": "IDEA_SELECTION_REQUIRED"}),
        ],
        "validation_errors": [],
        "creative_ideas": [],
        "model_call_records": [],
    }

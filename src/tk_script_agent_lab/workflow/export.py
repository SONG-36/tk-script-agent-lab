from pathlib import Path
import json

from tk_script_agent_lab.workflow.models import (
    WorkflowState,
    WorkflowStatus,
    WorkflowStepRecord,
)
from tk_script_agent_lab.workflow.runner import _workflow_error


def export_completed_workflow(
    state: WorkflowState,
    output_directory: Path,
) -> tuple[Path, Path]:
    if state.status != WorkflowStatus.COMPLETED:
        raise ValueError("EXPORT_REQUIRES_COMPLETED_STATE")
    if state.script_draft is None or state.idea_review is None:
        raise ValueError("EXPORT_REQUIRES_COMPLETED_STATE")

    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / "workflow_result.json"
    markdown_path = output_directory / "script.md"

    export_step = WorkflowStepRecord(
        sequence=len(state.step_records) + 1,
        step_name="export_result",
        executor="IO",
        status="SUCCESS",
        input_ids=[state.run_id],
        output_ids=[json_path.name, markdown_path.name],
        error_codes=[],
    )
    exported_steps = [
        record.model_dump(mode="json") for record in [*state.step_records, export_step]
    ]

    payload = {
        "run_id": state.run_id,
        "status": state.status,
        "product_id": state.workflow_input.product_profile.product_id,
        "selected_idea_id": state.selected_idea_id,
        "idea_review": state.idea_review.model_dump(mode="json"),
        "reference_insights": [
            insight.model_dump(mode="json") for insight in state.reference_insights
        ],
        "creative_ideas": [
            idea.model_dump(mode="json") for idea in state.creative_ideas
        ],
        "script_draft": state.script_draft.model_dump(mode="json"),
        "validation_errors": [
            error.model_dump(mode="json") for error in state.validation_errors
        ],
        "step_records": exported_steps,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_script_markdown(state), encoding="utf-8")
    return json_path, markdown_path


def export_requires_completed_error() -> object:
    return _workflow_error(
        "EXPORT_REQUIRES_COMPLETED_STATE",
        "Workflow export requires COMPLETED state.",
        object_type="Workflow",
        field="status",
    )


def _render_script_markdown(state: WorkflowState) -> str:
    assert state.script_draft is not None
    assert state.idea_review is not None
    selected_idea = next(
        idea
        for idea in state.creative_ideas
        if idea.creative_idea_id == state.selected_idea_id
    )
    script = state.script_draft

    lines = [
        f"# {script.title}",
        "",
        f"商品名称: {state.workflow_input.product_profile.product_name}",
        f"选中创意: {selected_idea.title}",
        f"Hook: {selected_idea.hook}",
        f"脚本标题: {script.title}",
        "",
        "## 场景",
    ]
    for scene in sorted(script.scenes, key=lambda item: item.sequence):
        lines.extend(
            [
                "",
                f"### Scene {scene.sequence}: {scene.scene_id}",
                f"画面: {scene.visual}",
                f"动作: {scene.action}",
                f"旁白: {scene.voiceover or ''}",
                f"屏幕文字: {scene.on_screen_text or ''}",
                f"时长: {scene.duration_seconds}",
            ]
        )
    lines.extend(
        [
            "",
            f"Caption: {script.caption or ''}",
            f"CTA: {script.cta or ''}",
            "",
            "## SourceUsage",
        ]
    )
    for usage in script.source_usages:
        lines.append(
            f"- {usage.source_type}:{usage.source_id} - {usage.usage_purpose}"
        )
    lines.extend(
        [
            "",
            "## 人工审核信息",
            f"Review ID: {state.idea_review.review_id}",
            f"Decision: {state.idea_review.decision}",
            f"Reviewer: {state.idea_review.reviewer or ''}",
            f"Comment: {state.idea_review.comment or ''}",
            "",
        ]
    )
    return "\n".join(lines)

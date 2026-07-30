from argparse import ArgumentParser
from pathlib import Path

from tk_script_agent_lab.domain import ReviewDecision, ReviewDecisionType
from tk_script_agent_lab.golden_case import load_golden_case
from tk_script_agent_lab.providers import FakeContentProvider
from tk_script_agent_lab.workflow import (
    WorkflowStatus,
    export_completed_workflow,
    resume_with_review,
    start_workflow,
)


def main() -> None:
    parser = ArgumentParser(description="Run the Phase 1B deterministic demo.")
    parser.add_argument("--selected-idea-id")
    parser.add_argument("--reviewer")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    case_dir = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "golden_cases"
        / "car_vacuum_v1"
    )
    workflow_input, fixtures, _reviews = load_golden_case(case_dir)
    provider = FakeContentProvider(fixtures)
    state = start_workflow(workflow_input, provider)

    print(f"run_id={state.run_id}")
    print(f"status={state.status}")
    print(f"script_draft={state.script_draft}")
    for idea in state.creative_ideas:
        print(f"creative_idea_id={idea.creative_idea_id}")
        print(f"title={idea.title}")
        print(f"hook={idea.hook}")

    if not args.selected_idea_id:
        print("AWAITING_IDEA_SELECTION")
        return

    if not args.reviewer:
        raise SystemExit("--reviewer is required when --selected-idea-id is provided")
    if not args.output_dir:
        raise SystemExit("--output-dir is required when --selected-idea-id is provided")
    if state.status != WorkflowStatus.AWAITING_IDEA_SELECTION:
        raise SystemExit(f"Cannot resume from status {state.status}")

    review = ReviewDecision(
        review_id="demo_approved_review",
        target_type="creative_idea",
        target_id=args.selected_idea_id,
        decision=ReviewDecisionType.APPROVED,
        reviewer=args.reviewer,
        comment=None,
    )
    completed = resume_with_review(state, review, provider)
    print(f"resumed_status={completed.status}")
    if completed.validation_errors:
        for error in completed.validation_errors:
            print(f"error={error.code}:{error.message}")
        raise SystemExit(1)
    json_path, markdown_path = export_completed_workflow(completed, args.output_dir)
    print(f"workflow_result={json_path}")
    print(f"script_markdown={markdown_path}")


if __name__ == "__main__":
    main()

from langgraph.types import Command

from tk_script_agent_lab.workflow import WorkflowStatus

from phase_1c_helpers import (
    approved_resume,
    load_studio_input,
    make_graph,
    thread_config,
)


def test_graph_runs_to_interrupt_without_script() -> None:
    graph = make_graph()
    result = graph.invoke(load_studio_input(), config=thread_config("interrupt-test"))

    interrupt_payload = result["__interrupt__"][0].value

    assert interrupt_payload["type"] == "IDEA_SELECTION_REQUIRED"
    assert len(interrupt_payload["creative_ideas"]) == 2
    assert "script_draft" not in result or result["script_draft"] is None


def test_interrupt_payload_does_not_auto_select_idea() -> None:
    graph = make_graph()
    result = graph.invoke(load_studio_input(), config=thread_config("no-auto-select"))

    state = graph.get_state(thread_config("no-auto-select"))

    assert result["__interrupt__"]
    assert state.values.get("selected_idea_id") is None


def test_approved_resume_generates_selected_script() -> None:
    graph = make_graph()
    config = thread_config("approved-resume")
    first = graph.invoke(load_studio_input(), config=config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    completed = graph.invoke(Command(resume=approved_resume(selected_id)), config=config)

    assert completed["status"] == WorkflowStatus.COMPLETED
    assert completed["script_draft"].creative_idea_id == selected_id


def test_rejected_resume_ends_without_script() -> None:
    graph = make_graph()
    config = thread_config("rejected-resume")
    first = graph.invoke(load_studio_input(), config=config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    result = graph.invoke(
        Command(
            resume={
                "target_id": selected_id,
                "decision": "REJECTED",
                "reviewer": "test-reviewer",
                "comment": "No.",
            }
        ),
        config=config,
    )

    assert result["status"] == WorkflowStatus.IDEA_REJECTED
    assert result.get("script_draft") is None


def test_revision_required_resume_ends_without_script() -> None:
    graph = make_graph()
    config = thread_config("revision-resume")
    first = graph.invoke(load_studio_input(), config=config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    result = graph.invoke(
        Command(
            resume={
                "target_id": selected_id,
                "decision": "REVISION_REQUIRED",
                "reviewer": "test-reviewer",
                "comment": "Revise.",
            }
        ),
        config=config,
    )

    assert result["status"] == WorkflowStatus.REVISION_REQUIRED
    assert result.get("script_draft") is None


def test_pending_resume_interrupts_again() -> None:
    graph = make_graph()
    config = thread_config("pending-resume")
    first = graph.invoke(load_studio_input(), config=config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    result = graph.invoke(
        Command(
            resume={
                "target_id": selected_id,
                "decision": "PENDING",
                "reviewer": None,
                "comment": None,
            }
        ),
        config=config,
    )

    assert result["__interrupt__"][0].value["type"] == "IDEA_SELECTION_REQUIRED"


def test_invalid_idea_resume_does_not_generate_script() -> None:
    graph = make_graph()
    config = thread_config("invalid-idea-resume")
    graph.invoke(load_studio_input(), config=config)

    result = graph.invoke(Command(resume=approved_resume("missing_idea")), config=config)

    assert result["status"] == WorkflowStatus.FAILED
    assert result.get("script_draft") is None
    assert "CREATIVE_IDEA_NOT_FOUND" in [error.code for error in result["validation_errors"]]


def test_wrong_target_type_is_rejected() -> None:
    graph = make_graph()
    config = thread_config("wrong-target-type")
    graph.invoke(load_studio_input(), config=config)

    result = graph.invoke(
        Command(
            resume={
                "target_type": "script_draft",
                "target_id": "script_schema_fixture_1",
                "decision": "PENDING",
                "reviewer": None,
                "comment": None,
            }
        ),
        config=config,
    )

    assert "REVIEW_TARGET_TYPE_INVALID" in [
        error.code for error in result["validation_errors"]
    ]


def test_different_thread_does_not_share_resume_state() -> None:
    graph = make_graph()
    first_config = thread_config("thread-one")
    second_config = thread_config("thread-two")
    first = graph.invoke(load_studio_input(), config=first_config)
    selected_id = first["__interrupt__"][0].value["creative_ideas"][0]["creative_idea_id"]

    second = graph.invoke(load_studio_input(), config=second_config)

    assert second["__interrupt__"]
    completed = graph.invoke(Command(resume=approved_resume(selected_id)), config=first_config)
    assert completed["status"] == WorkflowStatus.COMPLETED
    assert graph.get_state(second_config).values.get("script_draft") is None

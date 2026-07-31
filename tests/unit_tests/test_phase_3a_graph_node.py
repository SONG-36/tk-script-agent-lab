from tk_script_agent_lab.configuration import GraphConfiguration
from tk_script_agent_lab.langgraph_app.nodes import (
    select_creative_knowledge,
    validate_input,
    validate_manual_insights,
)
from tk_script_agent_lab.workflow import WorkflowStatus

from phase_1c_helpers import load_studio_input, make_graph, thread_config


class Runtime:
    def __init__(self, context: dict) -> None:
        self.context = context


def state_after_manual_insights() -> dict:
    state = validate_input(load_studio_input())
    state.update(validate_manual_insights(state))
    return state


def test_select_creative_knowledge_off_mode_records_empty_selection() -> None:
    state = state_after_manual_insights()

    result = select_creative_knowledge(state, Runtime(GraphConfiguration().model_dump()))

    assert result["creative_knowledge_items"] == []
    assert result["knowledge_selection_records"][0].mode == "off"
    assert result["knowledge_selection_records"][0].selected_ids == []
    assert result["step_records"][-1].executor == "DETERMINISTIC_CODE"


def test_select_creative_knowledge_static_mode_selects_pack_items() -> None:
    state = state_after_manual_insights()

    result = select_creative_knowledge(
        state,
        Runtime(
            {
                "knowledge_mode": "static",
                "creative_knowledge_pack": "tiktok_car_cleaning_v1",
                "creative_knowledge_limit": 6,
            }
        ),
    )

    assert [item.knowledge_id for item in result["creative_knowledge_items"]] == [
        "ck_claim_safety_no_unverified_performance",
        "ck_hook_visible_micro_mess",
        "ck_hook_action_consistency",
        "ck_diversity_distinct_angles",
        "ck_shootability_simple_actions",
        "ck_pattern_before_after_not_only_angle",
    ]
    assert result["knowledge_selection_records"][0].pack_id == "tiktok_car_cleaning_v1"
    assert result["validation_errors"] == []


def test_select_creative_knowledge_static_mode_requires_pack() -> None:
    state = state_after_manual_insights()

    result = select_creative_knowledge(state, Runtime({"knowledge_mode": "static"}))

    assert result["status"] == WorkflowStatus.FAILED
    assert [error.code for error in result["validation_errors"]] == [
        "KNOWLEDGE_SELECTION_FAILED"
    ]


def test_graph_static_knowledge_reaches_human_interrupt_with_fake_provider() -> None:
    graph = make_graph()
    result = graph.invoke(
        load_studio_input(),
        config=thread_config("phase-3a-static-fake"),
        context={
            "knowledge_mode": "static",
            "creative_knowledge_pack": "tiktok_car_cleaning_v1",
        },
    )

    assert result["__interrupt__"][0].value["type"] == "IDEA_SELECTION_REQUIRED"
    assert result["knowledge_selection_records"][0].mode == "static"
    assert result.get("model_call_records", []) == []
    assert [record.step_name for record in result["step_records"]][:4] == [
        "validate_input",
        "validate_manual_insights",
        "select_creative_knowledge",
        "generate_creative_ideas",
    ]

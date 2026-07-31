from tk_script_agent_lab.knowledge import StaticCreativeKnowledgeSelector
from tk_script_agent_lab.knowledge.loader import load_creative_knowledge_pack


def test_static_selector_is_deterministic_and_priority_sorted() -> None:
    pack = load_creative_knowledge_pack("tiktok_car_cleaning_v1")
    selector = StaticCreativeKnowledgeSelector(selector_version="static_selector_v1")

    first_items, first_record = selector.select(
        pack=pack,
        target_market="Schema validation fixture",
        product_category="car vacuum cleaner",
        limit=3,
    )
    second_items, second_record = selector.select(
        pack=pack,
        target_market="Schema validation fixture",
        product_category="car vacuum cleaner",
        limit=3,
    )

    assert [item.knowledge_id for item in first_items] == [
        "ck_claim_safety_no_unverified_performance",
        "ck_hook_visible_micro_mess",
        "ck_hook_action_consistency",
    ]
    assert first_record.selection_id == second_record.selection_id
    assert first_record.selected_ids == second_record.selected_ids
    assert {item.reason for item in first_record.excluded_items} == {"over_limit"}


def test_static_selector_records_mismatch_reasons() -> None:
    pack = load_creative_knowledge_pack("tiktok_car_cleaning_v1")
    selector = StaticCreativeKnowledgeSelector()

    selected, record = selector.select(
        pack=pack,
        target_market="Schema validation fixture",
        product_category="unrelated category",
        limit=6,
    )

    assert [item.knowledge_id for item in selected] == [
        "ck_claim_safety_no_unverified_performance",
        "ck_hook_action_consistency",
        "ck_diversity_distinct_angles",
    ]
    excluded = {item.knowledge_id: item.reason for item in record.excluded_items}
    assert excluded["ck_hook_visible_micro_mess"] == "category_mismatch"
    assert excluded["ck_shootability_simple_actions"] == "category_mismatch"
    assert excluded["ck_pattern_before_after_not_only_angle"] == "category_mismatch"


def test_off_mode_record_selects_no_items() -> None:
    selector = StaticCreativeKnowledgeSelector()

    record = selector.empty_record(
        target_market="Schema validation fixture",
        product_category="car vacuum cleaner",
        limit=6,
    )

    assert record.mode == "off"
    assert record.pack_id is None
    assert record.selected_ids == []
    assert record.candidate_ids == []

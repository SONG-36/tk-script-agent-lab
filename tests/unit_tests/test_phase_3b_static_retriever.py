from tk_script_agent_lab.knowledge import RetrievalRequest, StaticKnowledgeRetriever


def request(*, limit: int = 6, product_category: str = "car vacuum cleaner") -> RetrievalRequest:
    return RetrievalRequest(
        stage="creative",
        target_market="Schema validation fixture",
        product_category=product_category,
        query="Creative guidance for car vacuum.",
        limit=limit,
        filters={"product_id": "prod_car_vacuum_schema_fixture"},
    )


def test_static_retriever_reuses_loader_and_selector_for_stable_results() -> None:
    retriever = StaticKnowledgeRetriever(pack_id="tiktok_car_cleaning_v1")

    first = retriever.retrieve(request(limit=3))
    second = retriever.retrieve(request(limit=3))

    assert first.errors == []
    assert [item.knowledge_id for item in first.items] == [
        "ck_claim_safety_no_unverified_performance",
        "ck_hook_visible_micro_mess",
        "ck_hook_action_consistency",
    ]
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert {item.reason for item in first.trace.excluded} == {"over_limit"}


def test_static_retriever_missing_pack_returns_stable_error() -> None:
    result = StaticKnowledgeRetriever(pack_id="missing_pack").retrieve(request())

    assert result.items == []
    assert [error.code for error in result.errors] == ["KNOWLEDGE_PACK_NOT_FOUND"]
    assert result.trace.filters_applied["pack_id"] == "missing_pack"


def test_static_retriever_filter_mismatch_and_limit_are_deterministic() -> None:
    result = StaticKnowledgeRetriever(pack_id="tiktok_car_cleaning_v1").retrieve(
        request(limit=2, product_category="unrelated category")
    )

    assert [item.knowledge_id for item in result.items] == [
        "ck_claim_safety_no_unverified_performance",
        "ck_hook_action_consistency",
    ]
    excluded = {item.knowledge_id: item.reason for item in result.trace.excluded}
    assert excluded["ck_hook_visible_micro_mess"] == "category_mismatch"
    assert excluded["ck_diversity_distinct_angles"] == "over_limit"


def test_static_retriever_preserves_provenance_and_has_no_scores_or_network() -> None:
    result = StaticKnowledgeRetriever(pack_id="tiktok_car_cleaning_v1").retrieve(request(limit=1))
    item = result.items[0]

    assert item.provenance_type == "internal_working_rule"
    assert item.evidence_status == "hypothesis"
    assert item.score is None
    assert "positive_examples" in item.metadata

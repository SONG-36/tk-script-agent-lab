from tk_script_agent_lab.domain import (
    DomainDataset,
    ProductFact,
    ReferenceInsight,
    ReviewDecision,
    ReviewDecisionType,
    SellingPoint,
    VerificationStatus,
    validate_domain_dataset,
)

from conftest import (
    make_creative_idea,
    make_rejected_fact,
    make_review_decision,
    make_script_draft,
    make_selling_point,
    make_source_usage,
    make_verified_fact,
)


def error_codes(dataset: DomainDataset) -> list[str]:
    return [error.code for error in validate_domain_dataset(dataset)]


def test_valid_dataset_has_no_cross_reference_errors(valid_dataset: DomainDataset) -> None:
    assert validate_domain_dataset(valid_dataset) == []


def test_selling_point_referencing_missing_fact_returns_stable_code(
    valid_dataset: DomainDataset,
) -> None:
    dataset = valid_dataset.model_copy(
        update={"selling_points": [make_selling_point(fact_ids=["missing_fact"])]},
        deep=True,
    )

    assert "FACT_NOT_FOUND" in error_codes(dataset)


def test_selling_point_referencing_unverified_fact_returns_stable_code(
    valid_dataset: DomainDataset,
) -> None:
    dataset = valid_dataset.model_copy(
        update={"selling_points": [make_selling_point(fact_ids=["fact_unverified"])]},
        deep=True,
    )

    assert "FACT_NOT_VERIFIED" in error_codes(dataset)


def test_reference_insight_referencing_missing_video_returns_stable_code(
    valid_dataset: DomainDataset,
) -> None:
    broken_insight = ReferenceInsight(
        insight_id="insight_1",
        reference_video_id="missing_video",
        insight_type="HOOK",
        description="Show the mess first.",
        evidence_text=None,
        start_second=None,
        end_second=None,
    )
    dataset = valid_dataset.model_copy(
        update={"reference_insights": [broken_insight]},
        deep=True,
    )

    assert "REFERENCE_VIDEO_NOT_FOUND" in error_codes(dataset)


def test_creative_idea_referencing_missing_source_returns_stable_code(
    valid_dataset: DomainDataset,
) -> None:
    broken_idea = make_creative_idea().model_copy(
        update={
            "source_usages": [
                make_source_usage("usage_1", "selling_point", "missing_sp"),
            ]
        },
        deep=True,
    )
    dataset = valid_dataset.model_copy(update={"creative_ideas": [broken_idea]}, deep=True)

    assert "SELLING_POINT_NOT_FOUND" in error_codes(dataset)


def test_creative_idea_referencing_rejected_fact_returns_stable_code(
    valid_dataset: DomainDataset,
) -> None:
    rejected_fact = make_rejected_fact()
    broken_idea = make_creative_idea().model_copy(
        update={
            "source_usages": [
                make_source_usage("usage_1", "product_fact", rejected_fact.fact_id),
            ]
        },
        deep=True,
    )
    dataset = valid_dataset.model_copy(
        update={
            "product_facts": [make_verified_fact(), rejected_fact],
            "creative_ideas": [broken_idea],
        },
        deep=True,
    )

    assert "FACT_REJECTED" in error_codes(dataset)


def test_script_draft_referencing_missing_creative_idea_returns_stable_code(
    valid_dataset: DomainDataset,
) -> None:
    dataset = valid_dataset.model_copy(
        update={"script_drafts": [make_script_draft(creative_idea_id="missing_idea")]},
        deep=True,
    )

    assert "CREATIVE_IDEA_NOT_FOUND" in error_codes(dataset)


def test_product_id_mismatch_returns_stable_code(valid_dataset: DomainDataset) -> None:
    mismatched_fact = ProductFact(
        fact_id="fact_other_product",
        product_id="other_product",
        field_name="category",
        value="car vacuum cleaner",
        unit=None,
        status=VerificationStatus.VERIFIED,
        source_ids=["source_1"],
        notes=None,
    )
    dataset = valid_dataset.model_copy(
        update={"product_facts": [mismatched_fact], "selling_points": []},
        deep=True,
    )

    assert "PRODUCT_ID_MISMATCH" in error_codes(dataset)


def test_duplicate_id_returns_stable_code(valid_dataset: DomainDataset) -> None:
    dataset = valid_dataset.model_copy(
        update={"selling_points": [make_selling_point(), make_selling_point()]},
        deep=True,
    )

    assert "DUPLICATE_ID" in error_codes(dataset)


def test_review_decision_referencing_missing_object_returns_stable_code(
    valid_dataset: DomainDataset,
) -> None:
    missing_review = ReviewDecision(
        review_id="review_missing",
        target_type="creative_idea",
        target_id="missing_idea",
        decision=ReviewDecisionType.PENDING,
        reviewer=None,
        comment=None,
    )
    dataset = valid_dataset.model_copy(
        update={"review_decisions": [missing_review]},
        deep=True,
    )

    assert "CREATIVE_IDEA_NOT_FOUND" in error_codes(dataset)


def test_selling_point_referencing_fact_for_different_product_returns_stable_code(
    valid_dataset: DomainDataset,
) -> None:
    other_fact = make_verified_fact(fact_id="fact_other_product", product_id="other_product")
    selling_point = SellingPoint(
        selling_point_id="sp_1",
        product_id="prod_1",
        title="Interior cleanup",
        description="Use verified context.",
        fact_ids=["fact_other_product"],
        target_pain_points=["Small car messes"],
        priority=3,
    )
    dataset = valid_dataset.model_copy(
        update={
            "product_facts": [other_fact],
            "selling_points": [selling_point],
        },
        deep=True,
    )

    assert "PRODUCT_ID_MISMATCH" in error_codes(dataset)

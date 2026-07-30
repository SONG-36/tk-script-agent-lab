import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import ProductFact, ProductProfile, SellingPoint, VerificationStatus


def test_product_profile_deduplicates_target_lists() -> None:
    profile = ProductProfile(
        product_id="prod_1",
        product_name="Fixture",
        category="car vacuum cleaner",
        target_market="schema tests",
        target_audiences=["Car owners", "Car owners"],
        usage_scenarios=["Interior cleanup", "Interior cleanup"],
        prohibited_claims=["No unverified claims"],
        notes=None,
    )

    assert profile.target_audiences == ["Car owners"]
    assert profile.usage_scenarios == ["Interior cleanup"]


def test_product_profile_rejects_blank_list_items() -> None:
    with pytest.raises(PydanticValidationError):
        ProductProfile(
            product_id="prod_1",
            product_name="Fixture",
            category="car vacuum cleaner",
            target_market="schema tests",
            target_audiences=[" "],
            usage_scenarios=["Interior cleanup"],
            prohibited_claims=["No unverified claims"],
            notes=None,
        )


def test_verified_product_fact_requires_source() -> None:
    fact = ProductFact(
        fact_id="fact_1",
        product_id="prod_1",
        field_name="category",
        value="car vacuum cleaner",
        unit=None,
        status=VerificationStatus.VERIFIED,
        source_ids=["source_1"],
        notes=None,
    )

    assert fact.status == VerificationStatus.VERIFIED


def test_unverified_product_fact_can_have_null_value_without_source() -> None:
    fact = ProductFact(
        fact_id="fact_1",
        product_id="prod_1",
        field_name="power_watts",
        value=None,
        unit="W",
        status=VerificationStatus.UNVERIFIED,
        source_ids=[],
        notes=None,
    )

    assert fact.value is None


def test_verified_product_fact_without_source_fails() -> None:
    with pytest.raises(PydanticValidationError):
        ProductFact(
            fact_id="fact_1",
            product_id="prod_1",
            field_name="category",
            value="car vacuum cleaner",
            unit=None,
            status=VerificationStatus.VERIFIED,
            source_ids=[],
            notes=None,
        )


def test_verified_product_fact_with_null_value_fails() -> None:
    with pytest.raises(PydanticValidationError):
        ProductFact(
            fact_id="fact_1",
            product_id="prod_1",
            field_name="category",
            value=None,
            unit=None,
            status=VerificationStatus.VERIFIED,
            source_ids=["source_1"],
            notes=None,
        )


def test_selling_point_priority_range_is_valid() -> None:
    selling_point = SellingPoint(
        selling_point_id="sp_1",
        product_id="prod_1",
        title="Interior cleanup",
        description="Use verified context.",
        fact_ids=["fact_1"],
        target_pain_points=["Small car messes"],
        priority=5,
    )

    assert selling_point.priority == 5


def test_selling_point_priority_out_of_range_fails() -> None:
    with pytest.raises(PydanticValidationError):
        SellingPoint(
            selling_point_id="sp_1",
            product_id="prod_1",
            title="Interior cleanup",
            description="Use verified context.",
            fact_ids=["fact_1"],
            target_pain_points=["Small car messes"],
            priority=6,
        )

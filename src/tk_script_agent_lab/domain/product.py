from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain.enums import VerificationStatus

FactValue = str | int | float | bool | None


def _require_non_empty(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be empty")
    return value


def _require_non_empty_items(values: list[str]) -> list[str]:
    for value in values:
        _require_non_empty(value)
    return values


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


class ProductProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    product_name: str
    category: str
    target_market: str
    target_audiences: list[str]
    usage_scenarios: list[str]
    prohibited_claims: list[str]
    notes: str | None = None

    @field_validator("product_id", "product_name", "category", "target_market")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("target_audiences", "usage_scenarios", mode="after")
    @classmethod
    def validate_and_dedupe_lists(cls, values: list[str]) -> list[str]:
        _require_non_empty_items(values)
        return _dedupe_preserving_order(values)

    @field_validator("prohibited_claims", mode="after")
    @classmethod
    def validate_prohibited_claims(cls, values: list[str]) -> list[str]:
        return _require_non_empty_items(values)


class ProductFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str
    product_id: str
    field_name: str
    value: FactValue
    unit: str | None = None
    status: VerificationStatus
    source_ids: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("fact_id", "product_id", "field_name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("source_ids", mode="after")
    @classmethod
    def validate_source_ids(cls, values: list[str]) -> list[str]:
        return _require_non_empty_items(values)

    @model_validator(mode="after")
    def validate_fact_status(self) -> "ProductFact":
        if self.status == VerificationStatus.VERIFIED and not self.source_ids:
            raise ValueError("VERIFIED facts must include at least one source_id")
        if self.status == VerificationStatus.VERIFIED and self.value is None:
            raise ValueError("VERIFIED facts must have a non-null value")
        return self


class SellingPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selling_point_id: str
    product_id: str
    title: str
    description: str
    fact_ids: list[str] = Field(min_length=1)
    target_pain_points: list[str]
    priority: int = Field(ge=1, le=5)

    @field_validator("selling_point_id", "product_id", "title", "description")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("fact_ids", mode="after")
    @classmethod
    def validate_fact_ids(cls, values: list[str]) -> list[str]:
        _require_non_empty_items(values)
        if len(values) != len(set(values)):
            raise ValueError("fact_ids must be unique")
        return values

    @field_validator("target_pain_points", mode="after")
    @classmethod
    def validate_target_pain_points(cls, values: list[str]) -> list[str]:
        return _require_non_empty_items(values)

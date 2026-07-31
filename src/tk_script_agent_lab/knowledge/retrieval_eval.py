from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.domain.product import _require_non_empty
from tk_script_agent_lab.knowledge.contracts import RetrievalRequest, RetrievalResult


class RetrievalEvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    request: RetrievalRequest
    expected_ids: list[str]
    forbidden_ids: list[str]
    minimum_recall: float = Field(default=1.0, ge=0.0, le=1.0)
    expected_top_id: str | None = None

    @field_validator("case_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_ids(self) -> "RetrievalEvalCase":
        if len(self.expected_ids) != len(set(self.expected_ids)):
            raise ValueError("expected_ids must be unique")
        if len(self.forbidden_ids) != len(set(self.forbidden_ids)):
            raise ValueError("forbidden_ids must be unique")
        if set(self.expected_ids) & set(self.forbidden_ids):
            raise ValueError("same ID cannot be both expected and forbidden")
        return self


class RetrievalEvalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    passed: bool
    selected_ids: list[str]
    matched_expected_ids: list[str]
    missing_expected_ids: list[str]
    forbidden_hits: list[str]
    recall: float
    top_id_match: bool | None
    errors: list[ValidationError] = Field(default_factory=list)


class RetrievalEvalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    mean_recall: float = Field(ge=0.0, le=1.0)
    results: list[RetrievalEvalResult]


class RetrievalEvaluator:
    def evaluate_case(
        self,
        case: RetrievalEvalCase,
        result: RetrievalResult,
    ) -> RetrievalEvalResult:
        selected_ids = result.trace.selected_ids
        selected_set = set(selected_ids)
        expected_ids = set(case.expected_ids)
        matched_expected_ids = [item for item in case.expected_ids if item in selected_set]
        missing_expected_ids = [item for item in case.expected_ids if item not in selected_set]
        forbidden_hits = [item for item in case.forbidden_ids if item in selected_set]
        recall = len(matched_expected_ids) / len(expected_ids) if expected_ids else 1.0
        top_id_match = None
        if case.expected_top_id is not None:
            top_id_match = bool(selected_ids and selected_ids[0] == case.expected_top_id)
        passed = (
            recall >= case.minimum_recall
            and not forbidden_hits
            and (top_id_match is not False)
            and not result.errors
        )
        return RetrievalEvalResult(
            case_id=case.case_id,
            passed=passed,
            selected_ids=selected_ids,
            matched_expected_ids=matched_expected_ids,
            missing_expected_ids=missing_expected_ids,
            forbidden_hits=forbidden_hits,
            recall=recall,
            top_id_match=top_id_match,
            errors=result.errors,
        )

    def evaluate_many(
        self,
        pairs: list[tuple[RetrievalEvalCase, RetrievalResult]],
    ) -> RetrievalEvalSummary:
        results = [self.evaluate_case(case, result) for case, result in pairs]
        passed_cases = sum(1 for result in results if result.passed)
        mean_recall = (
            sum(result.recall for result in results) / len(results)
            if results
            else 0.0
        )
        return RetrievalEvalSummary(
            total_cases=len(results),
            passed_cases=passed_cases,
            failed_cases=len(results) - passed_cases,
            mean_recall=mean_recall,
            results=results,
        )

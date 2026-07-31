from hashlib import sha256
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain import CreativeIdea, SourceUsage
from tk_script_agent_lab.domain.product import _require_non_empty

CreativeCandidateSourceType = Literal[
    "product_fact",
    "selling_point",
    "reference_insight",
]


class CreativeSourceUsageCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: CreativeCandidateSourceType
    source_id: str
    usage_purpose: str

    @field_validator("source_id", "usage_purpose")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class CreativeIdeaCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    hook: str
    concept_summary: str
    target_audience: str
    source_usages: list[CreativeSourceUsageCandidate] = Field(min_length=1)
    risk_notes: list[str] = Field(default_factory=list)

    @field_validator("title", "hook", "concept_summary", "target_audience")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("risk_notes", mode="after")
    @classmethod
    def validate_risk_notes(cls, values: list[str]) -> list[str]:
        for value in values:
            _require_non_empty(value)
        return values


class CreativeIdeaBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ideas: list[CreativeIdeaCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_distinct_ideas(self) -> "CreativeIdeaBatch":
        titles = [idea.title.strip().casefold() for idea in self.ideas]
        hooks = [idea.hook.strip().casefold() for idea in self.ideas]
        if len(titles) != len(set(titles)):
            raise ValueError("creative idea titles must be unique")
        if len(hooks) != len(set(hooks)):
            raise ValueError("creative idea hooks must be unique")
        return self


class ModelCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["generate_creative_ideas"]
    provider: Literal["openai"]
    model: str
    prompt_version: str
    attempt: int
    status: Literal["SUCCESS", "FAILED"]
    response_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    output_ids: list[str]
    error_code: str | None


class OpenAICreativeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_ideas: list[CreativeIdea]
    model_call_record: ModelCallRecord


def map_candidate_to_creative_idea(
    *,
    product_id: str,
    candidate: CreativeIdeaCandidate,
    index: int,
) -> CreativeIdea:
    creative_idea_id = _creative_idea_id(product_id, candidate, index)
    source_usages: list[SourceUsage] = []
    seen: set[tuple[str, str]] = set()
    for usage in candidate.source_usages:
        key = (usage.source_type, usage.source_id)
        if key in seen:
            continue
        seen.add(key)
        source_usages.append(
            SourceUsage(
                source_usage_id=_source_usage_id(creative_idea_id, usage),
                source_type=usage.source_type,
                source_id=usage.source_id,
                usage_purpose=usage.usage_purpose,
            )
        )
    return CreativeIdea(
        creative_idea_id=creative_idea_id,
        product_id=product_id,
        title=candidate.title,
        hook=candidate.hook,
        concept_summary=candidate.concept_summary,
        target_audience=candidate.target_audience,
        source_usages=source_usages,
        risk_notes=candidate.risk_notes,
    )


def _creative_idea_id(
    product_id: str,
    candidate: CreativeIdeaCandidate,
    index: int,
) -> str:
    payload = {
        "index": index,
        "title": candidate.title.strip(),
        "hook": candidate.hook.strip(),
        "concept_summary": candidate.concept_summary.strip(),
        "target_audience": candidate.target_audience.strip(),
    }
    return f"idea_{product_id}_{_stable_hash(payload)}"


def _source_usage_id(
    creative_idea_id: str,
    usage: CreativeSourceUsageCandidate,
) -> str:
    payload = {
        "creative_idea_id": creative_idea_id,
        "source_type": usage.source_type,
        "source_id": usage.source_id,
    }
    return f"usage_{_stable_hash(payload)}"


def _stable_hash(payload: dict[str, object]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(normalized.encode("utf-8")).hexdigest()[:12]

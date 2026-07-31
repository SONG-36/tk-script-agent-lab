from hashlib import sha256
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain.product import _require_non_empty, _require_non_empty_items

CreativeKnowledgeKind = Literal[
    "hook_pattern",
    "idea_diversity_rule",
    "shootability_rule",
    "claim_safety_rule",
    "creative_pattern",
]
KnowledgeStage = Literal["creative"]
KnowledgeMode = Literal["off", "static"]
KnowledgeProvenanceType = Literal[
    "internal_working_rule",
    "experiment_observation",
    "official_policy",
]
KnowledgeEvidenceStatus = Literal["hypothesis", "observed", "verified"]
KnowledgeStatus = Literal["active", "draft", "disabled"]


class KnowledgeApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_stages: list[KnowledgeStage] = Field(min_length=1)
    target_markets: list[str] = Field(min_length=1)
    product_categories: list[str] = Field(min_length=1)

    @field_validator("target_markets", "product_categories", mode="after")
    @classmethod
    def validate_text_list(cls, values: list[str]) -> list[str]:
        return _require_non_empty_items(values)


class CreativeKnowledgeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_id: str
    title: str
    kind: CreativeKnowledgeKind
    instruction: str
    rationale: str | None = None
    positive_examples: list[str] = Field(default_factory=list)
    anti_examples: list[str] = Field(default_factory=list)
    priority: int = Field(ge=0, le=100)
    status: KnowledgeStatus
    applicability: KnowledgeApplicability
    provenance_type: KnowledgeProvenanceType
    evidence_status: KnowledgeEvidenceStatus
    source_reference: str | None = None

    @field_validator("knowledge_id", "title", "instruction")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("positive_examples", "anti_examples", mode="after")
    @classmethod
    def validate_examples(cls, values: list[str]) -> list[str]:
        return _require_non_empty_items(values)

    @model_validator(mode="after")
    def validate_provenance_boundary(self) -> "CreativeKnowledgeItem":
        if self.provenance_type == "official_policy" and not self.source_reference:
            raise ValueError("official_policy knowledge requires source_reference")
        if (
            self.provenance_type == "internal_working_rule"
            and self.evidence_status == "verified"
        ):
            raise ValueError("internal_working_rule knowledge cannot be verified")
        return self


class CreativeKnowledgePack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    version: str
    title: str
    description: str
    items: list[CreativeKnowledgeItem] = Field(min_length=1)

    @field_validator("pack_id", "version", "title", "description")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_unique_item_ids(self) -> "CreativeKnowledgePack":
        item_ids = [item.knowledge_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("knowledge_id values must be unique within a pack")
        return self


class KnowledgeSelectionInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_market: str
    product_category: str
    limit: int = Field(ge=1)

    @field_validator("target_market", "product_category")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class KnowledgeExclusion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_id: str
    reason: Literal[
        "disabled",
        "draft",
        "stage_mismatch",
        "market_mismatch",
        "category_mismatch",
        "over_limit",
    ]

    @field_validator("knowledge_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class KnowledgeSelectionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selection_id: str
    stage: KnowledgeStage
    mode: KnowledgeMode
    pack_id: str | None
    pack_version: str | None
    selector_version: str
    candidate_ids: list[str]
    selected_ids: list[str]
    excluded_items: list[KnowledgeExclusion]
    selection_inputs: KnowledgeSelectionInputs

    @field_validator("selection_id", "selector_version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


def stable_selection_id(
    *,
    mode: KnowledgeMode,
    pack_id: str | None,
    pack_version: str | None,
    selector_version: str,
    selection_inputs: KnowledgeSelectionInputs,
    selected_ids: list[str],
) -> str:
    payload = {
        "mode": mode,
        "pack_id": pack_id,
        "pack_version": pack_version,
        "selector_version": selector_version,
        "selection_inputs": selection_inputs.model_dump(mode="json"),
        "selected_ids": selected_ids,
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"ks_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"

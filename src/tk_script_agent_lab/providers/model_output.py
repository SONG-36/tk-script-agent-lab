from hashlib import sha256
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tk_script_agent_lab.domain import CreativeIdea, ScriptDraft, ScriptScene, SourceUsage
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


class ScriptSceneCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visual: str
    action: str
    voiceover: str | None = None
    on_screen_text: str | None = None
    duration_seconds: float = Field(gt=0)

    @field_validator("visual", "action")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class ScriptSourceUsageCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: CreativeCandidateSourceType
    source_id: str
    usage_purpose: str

    @field_validator("source_id", "usage_purpose")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)


class ScriptDraftCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    scenes: list[ScriptSceneCandidate] = Field(min_length=1)
    caption: str | None = None
    cta: str | None = None
    source_usages: list[ScriptSourceUsageCandidate] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @model_validator(mode="after")
    def validate_distinct_content(self) -> "ScriptDraftCandidate":
        scenes = [
            (
                scene.visual.strip().casefold(),
                scene.action.strip().casefold(),
                scene.voiceover.strip().casefold() if scene.voiceover else None,
                scene.on_screen_text.strip().casefold() if scene.on_screen_text else None,
            )
            for scene in self.scenes
        ]
        if len(scenes) != len(set(scenes)):
            raise ValueError("script scenes must be unique")
        usages = [(usage.source_type, usage.source_id) for usage in self.source_usages]
        if len(usages) != len(set(usages)):
            raise ValueError("script source_usages must not repeat source_type/source_id")
        return self


class ModelCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["generate_creative_ideas", "generate_script"]
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


class OpenAIScriptResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_draft: ScriptDraft
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


def map_candidate_to_script_draft(
    *,
    product_id: str,
    creative_idea_id: str,
    candidate: ScriptDraftCandidate,
) -> ScriptDraft:
    script_id = _script_id(product_id, creative_idea_id, candidate)
    scenes = [
        ScriptScene(
            scene_id=_scene_id(script_id, scene, sequence),
            sequence=sequence,
            visual=scene.visual,
            action=scene.action,
            voiceover=scene.voiceover,
            on_screen_text=scene.on_screen_text,
            duration_seconds=scene.duration_seconds,
        )
        for sequence, scene in enumerate(candidate.scenes, start=1)
    ]
    source_usages = [
        SourceUsage(
            source_usage_id=_script_source_usage_id(script_id, usage),
            source_type=usage.source_type,
            source_id=usage.source_id,
            usage_purpose=usage.usage_purpose,
        )
        for usage in candidate.source_usages
    ]
    return ScriptDraft(
        script_id=script_id,
        product_id=product_id,
        creative_idea_id=creative_idea_id,
        title=candidate.title,
        scenes=scenes,
        caption=candidate.caption,
        cta=candidate.cta,
        source_usages=source_usages,
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


def _script_id(
    product_id: str,
    creative_idea_id: str,
    candidate: ScriptDraftCandidate,
) -> str:
    payload = {
        "product_id": product_id,
        "creative_idea_id": creative_idea_id,
        "title": candidate.title.strip(),
        "scenes": [
            {
                "visual": scene.visual.strip(),
                "action": scene.action.strip(),
                "voiceover": scene.voiceover.strip() if scene.voiceover else None,
                "on_screen_text": scene.on_screen_text.strip() if scene.on_screen_text else None,
                "duration_seconds": scene.duration_seconds,
            }
            for scene in candidate.scenes
        ],
        "caption": candidate.caption.strip() if candidate.caption else None,
        "cta": candidate.cta.strip() if candidate.cta else None,
    }
    return f"script_{product_id}_{_stable_hash(payload)}"


def _scene_id(
    script_id: str,
    scene: ScriptSceneCandidate,
    sequence: int,
) -> str:
    payload = {
        "script_id": script_id,
        "sequence": sequence,
        "visual": scene.visual.strip(),
        "action": scene.action.strip(),
        "voiceover": scene.voiceover.strip() if scene.voiceover else None,
        "on_screen_text": scene.on_screen_text.strip() if scene.on_screen_text else None,
    }
    return f"scene_{_stable_hash(payload)}"


def _script_source_usage_id(
    script_id: str,
    usage: ScriptSourceUsageCandidate,
) -> str:
    payload = {
        "script_id": script_id,
        "source_type": usage.source_type,
        "source_id": usage.source_id,
    }
    return f"usage_{_stable_hash(payload)}"


def _stable_hash(payload: dict[str, object]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(normalized.encode("utf-8")).hexdigest()[:12]

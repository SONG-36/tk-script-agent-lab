from collections.abc import Callable
import os
from typing import Protocol

from langchain_openai import ChatOpenAI
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.providers.base import CreativeGenerationRequest, ProviderOutputError
from tk_script_agent_lab.providers.model_output import (
    CreativeIdeaBatch,
    ModelCallRecord,
    OpenAICreativeResult,
    map_candidate_to_creative_idea,
)
from tk_script_agent_lab.prompts import creative_idea_v1, creative_idea_v2


class StructuredCreativeModel(Protocol):
    def invoke(self, input: object) -> object:
        ...


class OpenAICreativeProvider:
    def __init__(
        self,
        *,
        model: str,
        prompt_version: str = creative_idea_v1.PROMPT_VERSION,
        api_key_getter: Callable[[], str | None] | None = None,
        structured_model: StructuredCreativeModel | None = None,
    ) -> None:
        self.model = model
        self.prompt_version = prompt_version
        self._api_key_getter = api_key_getter or (lambda: os.environ.get("OPENAI_API_KEY"))
        self._structured_model = structured_model

    def generate_creative_ideas(
        self,
        request: CreativeGenerationRequest,
    ) -> OpenAICreativeResult:
        if not self.model.strip():
            raise ProviderOutputError(
                _error(
                    "MODEL_CONFIGURATION_MISSING",
                    "creative_model is required for OpenAI creative provider.",
                    field="creative_model",
                )
            )
        api_key = self._api_key_getter()
        if self._structured_model is None and not api_key:
            raise ProviderOutputError(
                _error(
                    "MODEL_CONFIGURATION_MISSING",
                    "OPENAI_API_KEY is required for OpenAI creative provider.",
                    field="OPENAI_API_KEY",
                )
            )

        try:
            prompt_tools = _prompt_tools(self.prompt_version)
            context = prompt_tools.build_context(request)
            prompt = prompt_tools.build_prompt(request)
        except ValueError as exc:
            raise ProviderOutputError(
                _error(
                    "PROVIDER_OUTPUT_INVALID",
                    "Creative idea prompt context is invalid.",
                    field="prompt_context",
                    related_id=str(exc),
                )
            ) from exc

        try:
            raw_result = self._model(api_key).invoke(
                [
                    ("system", prompt_tools.system_instruction),
                    ("human", prompt),
                ]
            )
        except PydanticValidationError as exc:
            error_code = _schema_error_code(exc)
            raise ProviderOutputError(
                _error(
                    error_code,
                    "OpenAI structured output failed schema validation.",
                    field="structured_output",
                    related_id=exc.__class__.__name__,
                )
            ) from exc
        except Exception as exc:
            raise ProviderOutputError(
                _error(
                    "MODEL_CALL_FAILED",
                    "OpenAI creative idea generation failed.",
                    field="model_call",
                    related_id=exc.__class__.__name__,
                )
            ) from exc

        try:
            batch, raw_message, parsing_error = _parse_structured_result(raw_result)
        except PydanticValidationError as exc:
            error_code = _schema_error_code(exc)
            raise ProviderOutputError(
                _error(
                    error_code,
                    "OpenAI structured output failed schema validation.",
                    field="structured_output",
                    related_id=exc.__class__.__name__,
                )
            ) from exc
        if parsing_error is not None:
            raise ProviderOutputError(
                _error(
                    "MODEL_OUTPUT_SCHEMA_INVALID",
                    "OpenAI structured output could not be parsed.",
                    field="structured_output",
                    related_id=parsing_error.__class__.__name__,
                )
            )
        if len(batch.ideas) != request.idea_count:
            raise ProviderOutputError(
                _error(
                    "MODEL_OUTPUT_COUNT_INVALID",
                    "OpenAI returned a different number of ideas than requested.",
                    field="ideas",
                    related_id=str(len(batch.ideas)),
                )
            )

        allowed_source_ids = _allowed_source_ids(context)
        source_error = _source_validation_error(batch, allowed_source_ids)
        if source_error is not None:
            raise ProviderOutputError(source_error)

        creative_ideas = [
            map_candidate_to_creative_idea(
                product_id=request.product_profile.product_id,
                candidate=candidate,
                index=index,
            )
            for index, candidate in enumerate(batch.ideas, start=1)
        ]
        return OpenAICreativeResult(
            creative_ideas=creative_ideas,
            model_call_record=ModelCallRecord(
                operation="generate_creative_ideas",
                provider="openai",
                model=self.model,
                prompt_version=self.prompt_version,
                attempt=1,
                status="SUCCESS",
                response_id=_response_id(raw_message),
                input_tokens=_usage_value(raw_message, "input_tokens"),
                output_tokens=_usage_value(raw_message, "output_tokens"),
                output_ids=[idea.creative_idea_id for idea in creative_ideas],
                error_code=None,
            ),
        )

    def _model(self, api_key: str | None) -> StructuredCreativeModel:
        if self._structured_model is not None:
            return self._structured_model
        chat_model = ChatOpenAI(
            model=self.model,
            api_key=api_key,
            temperature=0,
        )
        return chat_model.with_structured_output(
            CreativeIdeaBatch,
            method="json_schema",
            include_raw=True,
        )


def failed_model_call_record(
    *,
    model: str,
    prompt_version: str,
    error_code: str,
) -> ModelCallRecord:
    return ModelCallRecord(
        operation="generate_creative_ideas",
        provider="openai",
        model=model,
        prompt_version=prompt_version,
        attempt=1,
        status="FAILED",
        response_id=None,
        input_tokens=None,
        output_tokens=None,
        output_ids=[],
        error_code=error_code,
    )


class _PromptTools:
    def __init__(
        self,
        *,
        system_instruction: str,
        build_context,
        build_prompt,
    ) -> None:
        self.system_instruction = system_instruction
        self.build_context = build_context
        self.build_prompt = build_prompt


def _prompt_tools(prompt_version: str) -> _PromptTools:
    if prompt_version == creative_idea_v1.PROMPT_VERSION:
        return _PromptTools(
            system_instruction=creative_idea_v1.SYSTEM_INSTRUCTION,
            build_context=creative_idea_v1.build_creative_idea_context,
            build_prompt=creative_idea_v1.build_creative_idea_prompt,
        )
    if prompt_version == creative_idea_v2.PROMPT_VERSION:
        return _PromptTools(
            system_instruction=creative_idea_v2.SYSTEM_INSTRUCTION,
            build_context=creative_idea_v2.build_creative_idea_context,
            build_prompt=creative_idea_v2.build_creative_idea_prompt,
        )
    raise ValueError(f"unsupported creative prompt version: {prompt_version}")


def _parse_structured_result(raw_result: object) -> tuple[CreativeIdeaBatch, object | None, object | None]:
    if isinstance(raw_result, CreativeIdeaBatch):
        return raw_result, None, None
    if isinstance(raw_result, dict) and "parsed" in raw_result:
        parsed = raw_result.get("parsed")
        if parsed is None:
            raise PydanticValidationError.from_exception_data(
                "CreativeIdeaBatch",
                [
                    {
                        "type": "missing",
                        "loc": ("parsed",),
                        "msg": "parsed structured output is missing",
                        "input": raw_result,
                    }
                ],
            )
        return (
            CreativeIdeaBatch.model_validate(parsed),
            raw_result.get("raw"),
            raw_result.get("parsing_error"),
        )
    return CreativeIdeaBatch.model_validate(raw_result)


def _allowed_source_ids(context: dict[str, object]) -> dict[str, set[str]]:
    constraints = context["constraints"]  # type: ignore[index]
    allowed = constraints["allowed_source_ids"]  # type: ignore[index]
    return {
        source_type: set(source_ids)
        for source_type, source_ids in allowed.items()
    }


def _source_validation_error(
    batch: CreativeIdeaBatch,
    allowed_source_ids: dict[str, set[str]],
) -> ValidationError | None:
    for idea in batch.ideas:
        source_types = {usage.source_type for usage in idea.source_usages}
        if not ({"product_fact", "selling_point"} & source_types):
            return _error(
                "MODEL_OUTPUT_SOURCE_INVALID",
                "Each model-generated idea must reference at least one product source.",
                field="source_usages",
            )
        if "reference_insight" not in source_types:
            return _error(
                "MODEL_OUTPUT_SOURCE_INVALID",
                "Each model-generated idea must reference at least one reference insight.",
                field="source_usages",
            )
        for usage in idea.source_usages:
            if usage.source_id not in allowed_source_ids[usage.source_type]:
                return _error(
                    "MODEL_OUTPUT_SOURCE_INVALID",
                    "Model output referenced a source_id outside the allowed set.",
                    field="source_usages",
                    related_id=usage.source_id,
                )
    return None


def _response_id(raw_message: object | None) -> str | None:
    if raw_message is None:
        return None
    response_metadata = getattr(raw_message, "response_metadata", None) or {}
    return (
        getattr(raw_message, "id", None)
        or response_metadata.get("id")
        or response_metadata.get("response_id")
    )


def _usage_value(raw_message: object | None, key: str) -> int | None:
    if raw_message is None:
        return None
    usage_metadata = getattr(raw_message, "usage_metadata", None) or {}
    response_metadata = getattr(raw_message, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage") or {}
    value = usage_metadata.get(key) or token_usage.get(key)
    if value is None and key == "input_tokens":
        value = token_usage.get("prompt_tokens")
    if value is None and key == "output_tokens":
        value = token_usage.get("completion_tokens")
    return value


def _schema_error_code(exc: PydanticValidationError) -> str:
    message = str(exc)
    if "creative idea titles must be unique" in message or "creative idea hooks must be unique" in message:
        return "MODEL_OUTPUT_DUPLICATE"
    return "MODEL_OUTPUT_SCHEMA_INVALID"


def _error(
    code: str,
    message: str,
    *,
    field: str | None = None,
    related_id: str | None = None,
) -> ValidationError:
    return ValidationError(
        code=code,
        message=message,
        object_type="OpenAICreativeProvider",
        object_id=None,
        field=field,
        related_id=related_id,
    )

from collections.abc import Callable
import os
from typing import Protocol

from langchain_openai import ChatOpenAI
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.providers.base import ProviderOutputError, ScriptGenerationRequest
from tk_script_agent_lab.providers.model_output import (
    ModelCallRecord,
    OpenAIScriptResult,
    ScriptDraftCandidate,
    map_candidate_to_script_draft,
)
from tk_script_agent_lab.prompts.script_draft_v1 import (
    PROMPT_VERSION,
    SYSTEM_INSTRUCTION,
    build_script_draft_context,
    build_script_draft_prompt,
)


class StructuredScriptModel(Protocol):
    def invoke(self, input: object) -> object:
        ...


class OpenAIScriptProvider:
    def __init__(
        self,
        *,
        model: str,
        prompt_version: str = PROMPT_VERSION,
        api_key_getter: Callable[[], str | None] | None = None,
        structured_model: StructuredScriptModel | None = None,
    ) -> None:
        self.model = model
        self.prompt_version = prompt_version
        self._api_key_getter = api_key_getter or (lambda: os.environ.get("OPENAI_API_KEY"))
        self._structured_model = structured_model

    def generate_script(
        self,
        request: ScriptGenerationRequest,
    ) -> OpenAIScriptResult:
        if not self.model.strip():
            raise ProviderOutputError(
                _error(
                    "MODEL_CONFIGURATION_MISSING",
                    "script_model is required for OpenAI script provider.",
                    field="script_model",
                )
            )
        api_key = self._api_key_getter()
        if self._structured_model is None and not api_key:
            raise ProviderOutputError(
                _error(
                    "MODEL_CONFIGURATION_MISSING",
                    "OPENAI_API_KEY is required for OpenAI script provider.",
                    field="OPENAI_API_KEY",
                )
            )

        try:
            context = build_script_draft_context(request)
            prompt = build_script_draft_prompt(request)
        except ValueError as exc:
            raise ProviderOutputError(
                _error(
                    "PROVIDER_OUTPUT_INVALID",
                    "Script prompt context is invalid.",
                    field="prompt_context",
                    related_id=str(exc),
                )
            ) from exc

        try:
            raw_result = self._model(api_key).invoke(
                [
                    ("system", SYSTEM_INSTRUCTION),
                    ("human", prompt),
                ]
            )
        except PydanticValidationError as exc:
            raise ProviderOutputError(
                _error(
                    _schema_error_code(exc),
                    "OpenAI script structured output failed schema validation.",
                    field="structured_output",
                    related_id=exc.__class__.__name__,
                )
            ) from exc
        except Exception as exc:
            raise ProviderOutputError(
                _error(
                    "MODEL_CALL_FAILED",
                    "OpenAI script generation failed.",
                    field="model_call",
                    related_id=exc.__class__.__name__,
                )
            ) from exc

        try:
            candidate, raw_message, parsing_error = _parse_structured_result(raw_result)
        except PydanticValidationError as exc:
            raise ProviderOutputError(
                _error(
                    _schema_error_code(exc),
                    "OpenAI script structured output failed schema validation.",
                    field="structured_output",
                    related_id=exc.__class__.__name__,
                )
            ) from exc
        if parsing_error is not None:
            raise ProviderOutputError(
                _error(
                    "MODEL_OUTPUT_SCHEMA_INVALID",
                    "OpenAI script structured output could not be parsed.",
                    field="structured_output",
                    related_id=parsing_error.__class__.__name__,
                )
            )

        source_error = _source_validation_error(candidate, _allowed_source_ids(context))
        if source_error is not None:
            raise ProviderOutputError(source_error)

        script = map_candidate_to_script_draft(
            product_id=request.product_profile.product_id,
            creative_idea_id=request.selected_idea.creative_idea_id,
            candidate=candidate,
        )
        return OpenAIScriptResult(
            script_draft=script,
            model_call_record=ModelCallRecord(
                operation="generate_script",
                provider="openai",
                model=self.model,
                prompt_version=self.prompt_version,
                attempt=1,
                status="SUCCESS",
                response_id=_response_id(raw_message),
                input_tokens=_usage_value(raw_message, "input_tokens"),
                output_tokens=_usage_value(raw_message, "output_tokens"),
                output_ids=[script.script_id],
                error_code=None,
            ),
        )

    def _model(self, api_key: str | None) -> StructuredScriptModel:
        if self._structured_model is not None:
            return self._structured_model
        chat_model = ChatOpenAI(
            model=self.model,
            api_key=api_key,
            temperature=0,
        )
        return chat_model.with_structured_output(
            ScriptDraftCandidate,
            method="json_schema",
            include_raw=True,
        )


def failed_script_model_call_record(
    *,
    model: str,
    prompt_version: str,
    error_code: str,
) -> ModelCallRecord:
    return ModelCallRecord(
        operation="generate_script",
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


def _parse_structured_result(raw_result: object) -> tuple[ScriptDraftCandidate, object | None, object | None]:
    if isinstance(raw_result, ScriptDraftCandidate):
        return raw_result, None, None
    if isinstance(raw_result, dict) and "parsed" in raw_result:
        parsed = raw_result.get("parsed")
        if parsed is None:
            raise PydanticValidationError.from_exception_data(
                "ScriptDraftCandidate",
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
            ScriptDraftCandidate.model_validate(parsed),
            raw_result.get("raw"),
            raw_result.get("parsing_error"),
        )
    return ScriptDraftCandidate.model_validate(raw_result), None, None


def _allowed_source_ids(context: dict[str, object]) -> dict[str, set[str]]:
    constraints = context["constraints"]  # type: ignore[index]
    allowed = constraints["allowed_source_ids"]  # type: ignore[index]
    return {
        source_type: set(source_ids)
        for source_type, source_ids in allowed.items()
    }


def _source_validation_error(
    candidate: ScriptDraftCandidate,
    allowed_source_ids: dict[str, set[str]],
) -> ValidationError | None:
    source_types = {usage.source_type for usage in candidate.source_usages}
    if not ({"product_fact", "selling_point"} & source_types):
        return _error(
            "MODEL_OUTPUT_SOURCE_INVALID",
            "Script output must reference at least one product source.",
            field="source_usages",
        )
    if "reference_insight" not in source_types:
        return _error(
            "MODEL_OUTPUT_SOURCE_INVALID",
            "Script output must reference at least one reference insight.",
            field="source_usages",
        )
    for usage in candidate.source_usages:
        if usage.source_id not in allowed_source_ids[usage.source_type]:
            return _error(
                "MODEL_OUTPUT_SOURCE_INVALID",
                "Script output referenced a source_id outside the allowed set.",
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
    if "script scenes must be unique" in message:
        return "SCRIPT_SCENE_INVALID"
    if "script source_usages must not repeat" in message:
        return "SCRIPT_SOURCE_USAGE_INVALID"
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
        object_type="OpenAIScriptProvider",
        object_id=None,
        field=field,
        related_id=related_id,
    )

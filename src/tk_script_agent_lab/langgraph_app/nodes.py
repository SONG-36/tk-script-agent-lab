from pathlib import Path

from langgraph.runtime import Runtime
from langgraph.types import interrupt
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.configuration import GraphConfiguration
from tk_script_agent_lab.domain import (
    DomainDataset,
    ReviewDecision,
    ReviewDecisionType,
    ValidationError,
    validate_domain_dataset,
)
from tk_script_agent_lab.golden_case import load_golden_case
from tk_script_agent_lab.langgraph_app.state import (
    GraphInputState,
    GraphState,
    ReviewResumePayload,
)
from tk_script_agent_lab.providers import (
    CreativeGenerationRequest,
    FakeContentProvider,
    OpenAICreativeProvider,
    ProviderOutputError,
    ScriptGenerationRequest,
)
from tk_script_agent_lab.providers.openai_creative import failed_model_call_record
from tk_script_agent_lab.workflow import WorkflowInput, WorkflowStatus, WorkflowStepRecord


def validate_input(state: GraphState) -> GraphState:
    records: list[WorkflowStepRecord] = []
    try:
        graph_input = GraphInputState.model_validate(state)
        workflow_input = WorkflowInput(
            run_id=graph_input.run_id,
            product_profile=graph_input.product_profile,
            product_facts=graph_input.product_facts,
            selling_points=graph_input.selling_points,
            reference_videos=graph_input.reference_videos,
            idea_count=graph_input.idea_count,
        )
        errors = _validate_dataset(
            workflow_input,
            reference_insights=[],
            creative_ideas=[],
            script_drafts=[],
            review_decisions=[],
        )
    except PydanticValidationError as exc:
        run_id = str(state.get("run_id") or "")
        errors = [
            _graph_error(
                "WORKFLOW_INPUT_INVALID",
                "Graph input failed Pydantic validation.",
                object_id=run_id or None,
                field="input",
                related_id=exc.errors()[0].get("loc", ["input"])[0],
            )
        ]
        records.append(
            _step(records, "validate_input", "DETERMINISTIC_CODE", "FAILED", error_codes=[error.code for error in errors])
        )
        return {
            "run_id": run_id,
            "status": WorkflowStatus.INPUT_INVALID,
            "validation_errors": errors,
            "step_records": records,
            "model_call_records": [],
        }

    records.append(
        _step(
            records,
            "validate_input",
            "DETERMINISTIC_CODE",
            "FAILED" if errors else "SUCCESS",
            input_ids=[workflow_input.product_profile.product_id],
            error_codes=[error.code for error in errors],
        )
    )
    if errors:
        return {
            "run_id": workflow_input.run_id,
            "status": WorkflowStatus.INPUT_INVALID,
            "workflow_input": workflow_input,
            "reference_insights": graph_input.reference_insights,
            "creative_ideas": [],
            "selected_idea_id": None,
            "idea_review": None,
            "script_draft": None,
            "validation_errors": [
                _graph_error("WORKFLOW_INPUT_INVALID", "Workflow input is invalid.")
            ]
            + errors,
            "step_records": records,
            "model_call_records": [],
        }
    return {
        "run_id": workflow_input.run_id,
        "status": WorkflowStatus.READY,
        "workflow_input": workflow_input,
        "reference_insights": graph_input.reference_insights,
        "creative_ideas": [],
        "selected_idea_id": None,
        "idea_review": None,
        "script_draft": None,
        "validation_errors": [],
        "step_records": records,
        "model_call_records": [],
    }


def validate_manual_insights(state: GraphState) -> GraphState:
    workflow_input = state["workflow_input"]
    records = _records(state)
    reference_insights = state.get("reference_insights", [])
    errors = _validate_dataset(
        workflow_input,
        reference_insights=reference_insights,
        creative_ideas=[],
        script_drafts=[],
        review_decisions=[],
    )
    records.append(
        _step(
            records,
            "validate_manual_insights",
            "DETERMINISTIC_CODE",
            "FAILED" if errors else "SUCCESS",
            input_ids=[insight.insight_id for insight in reference_insights],
            error_codes=[error.code for error in errors],
        )
    )
    return {
        "status": WorkflowStatus.FAILED if errors else WorkflowStatus.READY,
        "validation_errors": errors,
        "step_records": records,
    }


def generate_creative_ideas(
    state: GraphState,
    runtime: Runtime[GraphConfiguration] = None,  # type: ignore[assignment]
) -> GraphState:
    workflow_input = state["workflow_input"]
    records = _records(state)
    configuration = _configuration(runtime)
    request = CreativeGenerationRequest(
        product_profile=workflow_input.product_profile,
        product_facts=workflow_input.product_facts,
        selling_points=workflow_input.selling_points,
        reference_insights=state.get("reference_insights", []),
        idea_count=workflow_input.idea_count,
    )
    try:
        if configuration.creative_provider == "fake":
            ideas = _provider().generate_creative_ideas(request)
            model_call_records = state.get("model_call_records", [])
            executor = "FAKE_PROVIDER"
        else:
            if configuration.creative_model is None:
                raise ProviderOutputError(
                    _graph_error(
                        "MODEL_CONFIGURATION_MISSING",
                        "creative_model is required for OpenAI creative provider.",
                        object_type="GraphConfiguration",
                        field="creative_model",
                    )
                )
            result = OpenAICreativeProvider(
                model=configuration.creative_model,
                prompt_version=configuration.creative_prompt_version,
            ).generate_creative_ideas(request)
            ideas = result.creative_ideas
            model_call_records = [
                *state.get("model_call_records", []),
                result.model_call_record,
            ]
            executor = "MODEL"
        records.append(
            _step(
                records,
                "generate_creative_ideas",
                executor,
                "SUCCESS",
                input_ids=[insight.insight_id for insight in state.get("reference_insights", [])],
                output_ids=[idea.creative_idea_id for idea in ideas],
            )
        )
        return {
            "creative_ideas": ideas,
            "validation_errors": [],
            "step_records": records,
            "model_call_records": model_call_records,
        }
    except ProviderOutputError as exc:
        model_call_records = state.get("model_call_records", [])
        if configuration.creative_provider == "openai":
            model_call_records = [
                *model_call_records,
                failed_model_call_record(
                    model=configuration.creative_model or "",
                    prompt_version=configuration.creative_prompt_version,
                    error_code=exc.error.code,
                ),
            ]
        records.append(
            _step(
                records,
                "generate_creative_ideas",
                "MODEL" if configuration.creative_provider == "openai" else "FAKE_PROVIDER",
                "FAILED",
                error_codes=[exc.error.code],
            )
        )
        return {
            "status": WorkflowStatus.FAILED,
            "validation_errors": [exc.error],
            "step_records": records,
            "model_call_records": model_call_records,
        }


def validate_creative_ideas(state: GraphState) -> GraphState:
    workflow_input = state["workflow_input"]
    records = _records(state)
    ideas = state.get("creative_ideas", [])
    errors = _validate_dataset(
        workflow_input,
        reference_insights=state.get("reference_insights", []),
        creative_ideas=ideas,
        script_drafts=[],
        review_decisions=[],
    )
    if len(ideas) > workflow_input.idea_count:
        errors = [
            _graph_error(
                "PROVIDER_OUTPUT_INVALID",
                "Fake Provider returned more ideas than requested.",
                field="creative_ideas",
            )
        ] + errors
    if not ideas:
        errors = [_graph_error("NO_CREATIVE_IDEAS", "No creative ideas are available.")] + errors
    records.append(
        _step(
            records,
            "validate_creative_ideas",
            "DETERMINISTIC_CODE",
            "FAILED" if errors else "SUCCESS",
            input_ids=[idea.creative_idea_id for idea in ideas],
            error_codes=[error.code for error in errors],
        )
    )
    return {
        "status": WorkflowStatus.FAILED if errors else WorkflowStatus.AWAITING_IDEA_SELECTION,
        "validation_errors": errors,
        "step_records": records,
    }


def human_select_idea(state: GraphState) -> GraphState:
    payload = {
        "type": "IDEA_SELECTION_REQUIRED",
        "run_id": state["run_id"],
        "creative_ideas": [
            {
                "creative_idea_id": idea.creative_idea_id,
                "title": idea.title,
                "hook": idea.hook,
                "concept_summary": idea.concept_summary,
            }
            for idea in state.get("creative_ideas", [])
        ],
        "allowed_decisions": [
            "APPROVED",
            "REJECTED",
            "REVISION_REQUIRED",
            "PENDING",
        ],
    }
    resume_value = interrupt(payload)
    records = _records(state)
    records.append(
        _step(
            records,
            "human_select_idea",
            "HUMAN",
            "SUCCESS",
            input_ids=[state["run_id"]],
        )
    )
    return {
        "resume_payload": ReviewResumePayload.model_validate(resume_value),
        "step_records": records,
    }


def apply_human_review(state: GraphState) -> GraphState:
    records = _records(state)
    payload = state.get("resume_payload")
    if payload is None:
        error = _graph_error(
            "IDEA_SELECTION_REQUIRED",
            "Graph resume requires a human review payload.",
            object_id=state["run_id"],
        )
        records.append(
            _step(records, "apply_human_review", "HUMAN", "FAILED", error_codes=[error.code])
        )
        return {"status": WorkflowStatus.FAILED, "validation_errors": [error], "step_records": records}

    if payload.target_type != "creative_idea":
        error = _graph_error(
            "REVIEW_TARGET_TYPE_INVALID",
            "Review payload must target a creative idea.",
            field="target_type",
            related_id=payload.target_type,
        )
        records.append(
            _step(records, "apply_human_review", "HUMAN", "FAILED", error_codes=[error.code])
        )
        return {"status": WorkflowStatus.FAILED, "validation_errors": [error], "step_records": records}

    selected_idea = _find_idea(state, payload.target_id)
    if selected_idea is None:
        error = _graph_error(
            "CREATIVE_IDEA_NOT_FOUND",
            "Review payload references an unknown creative idea.",
            field="target_id",
            related_id=payload.target_id,
        )
        records.append(
            _step(records, "apply_human_review", "HUMAN", "FAILED", error_codes=[error.code])
        )
        return {"status": WorkflowStatus.FAILED, "validation_errors": [error], "step_records": records}

    try:
        review = ReviewDecision(
            review_id=f"graph_review_{state['run_id']}",
            target_type="creative_idea",
            target_id=payload.target_id,
            decision=ReviewDecisionType(payload.decision),
            reviewer=payload.reviewer,
            comment=payload.comment,
        )
    except (PydanticValidationError, ValueError) as exc:
        error = _graph_error(
            "PROVIDER_OUTPUT_INVALID",
            "Review payload failed validation.",
            object_type="ReviewDecision",
            field="review",
            related_id=str(exc),
        )
        records.append(
            _step(records, "apply_human_review", "HUMAN", "FAILED", error_codes=[error.code])
        )
        return {"status": WorkflowStatus.FAILED, "validation_errors": [error], "step_records": records}

    records.append(
        _step(
            records,
            "apply_human_review",
            "HUMAN",
            "SUCCESS",
            input_ids=[review.review_id],
            output_ids=[review.target_id],
        )
    )
    if review.decision == ReviewDecisionType.APPROVED:
        return {
            "status": WorkflowStatus.READY,
            "selected_idea_id": review.target_id,
            "idea_review": review,
            "script_draft": None,
            "validation_errors": [],
            "step_records": records,
        }
    if review.decision == ReviewDecisionType.REJECTED:
        return {
            "status": WorkflowStatus.IDEA_REJECTED,
            "selected_idea_id": None,
            "idea_review": review,
            "script_draft": None,
            "validation_errors": [],
            "step_records": records,
        }
    if review.decision == ReviewDecisionType.REVISION_REQUIRED:
        return {
            "status": WorkflowStatus.REVISION_REQUIRED,
            "selected_idea_id": None,
            "idea_review": review,
            "script_draft": None,
            "validation_errors": [],
            "step_records": records,
        }
    return {
        "status": WorkflowStatus.AWAITING_IDEA_SELECTION,
        "selected_idea_id": None,
        "idea_review": review,
        "script_draft": None,
        "validation_errors": [],
        "step_records": records,
    }


def generate_script(state: GraphState) -> GraphState:
    workflow_input = state["workflow_input"]
    records = _records(state)
    selected_idea = _find_idea(state, state.get("selected_idea_id"))
    if selected_idea is None:
        error = _graph_error(
            "CREATIVE_IDEA_NOT_FOUND",
            "Selected creative idea is missing.",
            field="selected_idea_id",
            related_id=state.get("selected_idea_id"),
        )
        records.append(
            _step(records, "generate_script", "FAKE_PROVIDER", "FAILED", error_codes=[error.code])
        )
        return {"status": WorkflowStatus.FAILED, "validation_errors": [error], "step_records": records}

    try:
        script = _provider().generate_script(
            ScriptGenerationRequest(
                product_profile=workflow_input.product_profile,
                product_facts=workflow_input.product_facts,
                selling_points=workflow_input.selling_points,
                reference_insights=state.get("reference_insights", []),
                selected_idea=selected_idea,
            )
        )
        records.append(
            _step(
                records,
                "generate_script",
                "FAKE_PROVIDER",
                "SUCCESS",
                input_ids=[selected_idea.creative_idea_id],
                output_ids=[script.script_id],
            )
        )
        return {"script_draft": script, "validation_errors": [], "step_records": records}
    except ProviderOutputError as exc:
        records.append(
            _step(records, "generate_script", "FAKE_PROVIDER", "FAILED", error_codes=[exc.error.code])
        )
        return {"status": WorkflowStatus.FAILED, "validation_errors": [exc.error], "step_records": records}


def validate_script(state: GraphState) -> GraphState:
    workflow_input = state["workflow_input"]
    records = _records(state)
    script = state.get("script_draft")
    selected_idea_id = state.get("selected_idea_id")
    errors: list[ValidationError] = []

    if script is None:
        errors.append(_graph_error("SCRIPT_NOT_AVAILABLE", "ScriptDraft is missing."))
    else:
        if script.creative_idea_id != selected_idea_id:
            errors.append(
                _graph_error(
                    "SCRIPT_IDEA_MISMATCH",
                    "ScriptDraft does not match the selected idea.",
                    object_type="ScriptDraft",
                    object_id=script.script_id,
                    field="creative_idea_id",
                    related_id=script.creative_idea_id,
                )
            )
        if script.product_id != workflow_input.product_profile.product_id:
            errors.append(
                _graph_error(
                    "SCRIPT_PRODUCT_MISMATCH",
                    "ScriptDraft product_id does not match input product.",
                    object_type="ScriptDraft",
                    object_id=script.script_id,
                    field="product_id",
                    related_id=script.product_id,
                )
            )
        if state.get("idea_review") is not None:
            errors.extend(
                _validate_dataset(
                    workflow_input,
                    reference_insights=state.get("reference_insights", []),
                    creative_ideas=state.get("creative_ideas", []),
                    script_drafts=[script],
                    review_decisions=[state["idea_review"]],
                )
            )

    records.append(
        _step(
            records,
            "validate_script",
            "DETERMINISTIC_CODE",
            "FAILED" if errors else "SUCCESS",
            input_ids=[script.script_id] if script else [],
            error_codes=[error.code for error in errors],
        )
    )
    return {
        "status": WorkflowStatus.FAILED if errors else WorkflowStatus.COMPLETED,
        "validation_errors": errors,
        "step_records": records,
    }


def finalize_result(state: GraphState) -> GraphState:
    records = _records(state)
    records.append(
        _step(
            records,
            "finalize_result",
            "DETERMINISTIC_CODE",
            "SUCCESS" if not state.get("validation_errors") else "FAILED",
            input_ids=[state["run_id"]],
            error_codes=[error.code for error in state.get("validation_errors", [])],
        )
    )
    return {"step_records": records}


def _validate_dataset(
    workflow_input: WorkflowInput,
    *,
    reference_insights: list,
    creative_ideas: list,
    script_drafts: list,
    review_decisions: list,
) -> list[ValidationError]:
    dataset = DomainDataset(
        product_profile=workflow_input.product_profile,
        product_facts=workflow_input.product_facts,
        selling_points=workflow_input.selling_points,
        reference_videos=workflow_input.reference_videos,
        reference_insights=reference_insights,
        creative_ideas=creative_ideas,
        script_drafts=script_drafts,
        review_decisions=review_decisions,
    )
    return validate_domain_dataset(dataset)


def _provider() -> FakeContentProvider:
    case_dir = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "golden_cases"
        / "car_vacuum_v1"
    )
    _workflow_input, fixtures, _reviews = load_golden_case(case_dir)
    return FakeContentProvider(fixtures)


def _configuration(
    runtime: Runtime[GraphConfiguration] | None,
) -> GraphConfiguration:
    if runtime is None or runtime.context is None:
        return GraphConfiguration()
    if isinstance(runtime.context, GraphConfiguration):
        return runtime.context
    return GraphConfiguration.model_validate(runtime.context)


def _find_idea(state: GraphState, idea_id: str | None):
    if idea_id is None:
        return None
    return next(
        (idea for idea in state.get("creative_ideas", []) if idea.creative_idea_id == idea_id),
        None,
    )


def _records(state: GraphState) -> list[WorkflowStepRecord]:
    return [record.model_copy(deep=True) for record in state.get("step_records", [])]


def _step(
    records: list[WorkflowStepRecord],
    step_name: str,
    executor: str,
    status: str,
    *,
    input_ids: list[str] | None = None,
    output_ids: list[str] | None = None,
    error_codes: list[str] | None = None,
) -> WorkflowStepRecord:
    return WorkflowStepRecord(
        sequence=len(records) + 1,
        step_name=step_name,
        executor=executor,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        input_ids=input_ids or [],
        output_ids=output_ids or [],
        error_codes=error_codes or [],
    )


def _graph_error(
    code: str,
    message: str,
    *,
    object_type: str = "Graph",
    object_id: str | None = None,
    field: str | None = None,
    related_id: object | None = None,
) -> ValidationError:
    return ValidationError(
        code=code,
        message=message,
        object_type=object_type,
        object_id=object_id,
        field=field,
        related_id=str(related_id) if related_id is not None else None,
    )

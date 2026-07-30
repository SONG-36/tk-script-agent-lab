from tk_script_agent_lab.domain import (
    DomainDataset,
    ReviewDecision,
    ReviewDecisionType,
    ScriptDraft,
    ValidationError,
    validate_domain_dataset,
)
from tk_script_agent_lab.providers import (
    ContentProvider,
    CreativeGenerationRequest,
    ProviderOutputError,
    ReferenceAnalysisRequest,
    ScriptGenerationRequest,
)
from tk_script_agent_lab.workflow.models import (
    WorkflowInput,
    WorkflowState,
    WorkflowStatus,
    WorkflowStepRecord,
)


def start_workflow(
    workflow_input: WorkflowInput,
    provider: ContentProvider,
) -> WorkflowState:
    base_input = workflow_input.model_copy(deep=True)
    records: list[WorkflowStepRecord] = []

    input_errors = _validate_dataset(
        base_input,
        reference_insights=[],
        creative_ideas=[],
        script_drafts=[],
        review_decisions=[],
    )
    records.append(
        _step(
            records,
            "validate_input",
            "DETERMINISTIC_CODE",
            "FAILED" if input_errors else "SUCCESS",
            input_ids=[base_input.product_profile.product_id],
            error_codes=[error.code for error in input_errors],
        )
    )
    if input_errors:
        return WorkflowState(
            run_id=base_input.run_id,
            status=WorkflowStatus.INPUT_INVALID,
            workflow_input=base_input,
            validation_errors=[
                _workflow_error("WORKFLOW_INPUT_INVALID", "Workflow input is invalid.")
            ]
            + input_errors,
            step_records=records,
        )

    try:
        reference_insights = provider.analyze_references(
            ReferenceAnalysisRequest(
                product_profile=base_input.product_profile,
                product_facts=base_input.product_facts,
                reference_videos=base_input.reference_videos,
            )
        )
        records.append(
            _step(
                records,
                "analyze_references",
                "FAKE_PROVIDER",
                "SUCCESS",
                input_ids=[video.reference_video_id for video in base_input.reference_videos],
                output_ids=[insight.insight_id for insight in reference_insights],
            )
        )
    except ProviderOutputError as exc:
        records.append(
            _step(
                records,
                "analyze_references",
                "FAKE_PROVIDER",
                "FAILED",
                input_ids=[video.reference_video_id for video in base_input.reference_videos],
                error_codes=[exc.error.code],
            )
        )
        return _failed_state(base_input, records, [exc.error])

    insight_errors = _validate_dataset(
        base_input,
        reference_insights=reference_insights,
        creative_ideas=[],
        script_drafts=[],
        review_decisions=[],
    )
    records.append(
        _step(
            records,
            "validate_reference_insights",
            "DETERMINISTIC_CODE",
            "FAILED" if insight_errors else "SUCCESS",
            input_ids=[insight.insight_id for insight in reference_insights],
            error_codes=[error.code for error in insight_errors],
        )
    )
    if insight_errors:
        return _failed_state(
            base_input,
            records,
            [_workflow_error("PROVIDER_OUTPUT_INVALID", "Reference insight output is invalid.")]
            + insight_errors,
            reference_insights=reference_insights,
        )

    try:
        creative_ideas = provider.generate_creative_ideas(
            CreativeGenerationRequest(
                product_profile=base_input.product_profile,
                product_facts=base_input.product_facts,
                selling_points=base_input.selling_points,
                reference_insights=reference_insights,
                idea_count=base_input.idea_count,
            )
        )
        records.append(
            _step(
                records,
                "generate_creative_ideas",
                "FAKE_PROVIDER",
                "SUCCESS",
                input_ids=[insight.insight_id for insight in reference_insights],
                output_ids=[idea.creative_idea_id for idea in creative_ideas],
            )
        )
    except ProviderOutputError as exc:
        records.append(
            _step(
                records,
                "generate_creative_ideas",
                "FAKE_PROVIDER",
                "FAILED",
                input_ids=[insight.insight_id for insight in reference_insights],
                error_codes=[exc.error.code],
            )
        )
        return _failed_state(base_input, records, [exc.error], reference_insights=reference_insights)

    idea_errors = _validate_dataset(
        base_input,
        reference_insights=reference_insights,
        creative_ideas=creative_ideas,
        script_drafts=[],
        review_decisions=[],
    )
    if not creative_ideas:
        idea_errors = [
            _workflow_error("NO_CREATIVE_IDEAS", "Provider returned no creative ideas.")
        ] + idea_errors
    records.append(
        _step(
            records,
            "validate_creative_ideas",
            "DETERMINISTIC_CODE",
            "FAILED" if idea_errors else "SUCCESS",
            input_ids=[idea.creative_idea_id for idea in creative_ideas],
            error_codes=[error.code for error in idea_errors],
        )
    )
    if idea_errors:
        return _failed_state(
            base_input,
            records,
            [_workflow_error("PROVIDER_OUTPUT_INVALID", "Creative idea output is invalid.")]
            + idea_errors,
            reference_insights=reference_insights,
            creative_ideas=creative_ideas,
        )

    records.append(
        _step(
            records,
            "await_human_selection",
            "HUMAN",
            "WAITING",
            output_ids=[idea.creative_idea_id for idea in creative_ideas],
        )
    )
    return WorkflowState(
        run_id=base_input.run_id,
        status=WorkflowStatus.AWAITING_IDEA_SELECTION,
        workflow_input=base_input,
        reference_insights=reference_insights,
        creative_ideas=creative_ideas,
        script_draft=None,
        validation_errors=[],
        step_records=records,
    )


def resume_with_review(
    state: WorkflowState,
    review: ReviewDecision,
    provider: ContentProvider,
) -> WorkflowState:
    current = state.model_copy(deep=True)
    records = [record.model_copy(deep=True) for record in current.step_records]

    if current.status != WorkflowStatus.AWAITING_IDEA_SELECTION:
        error = _workflow_error(
            "INVALID_WORKFLOW_STATE",
            "Workflow can only resume from AWAITING_IDEA_SELECTION.",
            object_id=current.run_id,
            field="status",
            related_id=current.status,
        )
        records.append(
            _step(
                records,
                "apply_human_review",
                "HUMAN",
                "FAILED",
                input_ids=[current.run_id],
                error_codes=[error.code],
            )
        )
        return current.model_copy(
            update={
                "status": WorkflowStatus.FAILED,
                "validation_errors": [error],
                "step_records": records,
            },
            deep=True,
        )

    if review.target_type != "creative_idea":
        error = _workflow_error(
            "REVIEW_TARGET_TYPE_INVALID",
            "ReviewDecision for workflow resume must target a creative idea.",
            object_id=review.review_id,
            field="target_type",
            related_id=review.target_type,
        )
        records.append(
            _step(
                records,
                "apply_human_review",
                "HUMAN",
                "FAILED",
                input_ids=[review.review_id],
                error_codes=[error.code],
            )
        )
        return _resume_failure(current, records, review, [error])

    selected_idea = next(
        (idea for idea in current.creative_ideas if idea.creative_idea_id == review.target_id),
        None,
    )
    if selected_idea is None:
        error = _workflow_error(
            "CREATIVE_IDEA_NOT_FOUND",
            "ReviewDecision references a creative idea outside this workflow state.",
            object_id=review.review_id,
            field="target_id",
            related_id=review.target_id,
        )
        records.append(
            _step(
                records,
                "apply_human_review",
                "HUMAN",
                "FAILED",
                input_ids=[review.review_id],
                error_codes=[error.code],
            )
        )
        return _resume_failure(current, records, review, [error])

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

    if review.decision == ReviewDecisionType.REJECTED:
        return current.model_copy(
            update={
                "status": WorkflowStatus.IDEA_REJECTED,
                "idea_review": review,
                "selected_idea_id": None,
                "script_draft": None,
                "validation_errors": [],
                "step_records": records,
            },
            deep=True,
        )
    if review.decision == ReviewDecisionType.REVISION_REQUIRED:
        return current.model_copy(
            update={
                "status": WorkflowStatus.REVISION_REQUIRED,
                "idea_review": review,
                "selected_idea_id": None,
                "script_draft": None,
                "validation_errors": [],
                "step_records": records,
            },
            deep=True,
        )
    if review.decision == ReviewDecisionType.PENDING:
        return current.model_copy(
            update={
                "status": WorkflowStatus.AWAITING_IDEA_SELECTION,
                "idea_review": review,
                "selected_idea_id": None,
                "script_draft": None,
                "validation_errors": [],
                "step_records": records,
            },
            deep=True,
        )

    try:
        script = provider.generate_script(
            ScriptGenerationRequest(
                product_profile=current.workflow_input.product_profile,
                product_facts=current.workflow_input.product_facts,
                selling_points=current.workflow_input.selling_points,
                reference_insights=current.reference_insights,
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
    except ProviderOutputError as exc:
        records.append(
            _step(
                records,
                "generate_script",
                "FAKE_PROVIDER",
                "FAILED",
                input_ids=[selected_idea.creative_idea_id],
                error_codes=[exc.error.code],
            )
        )
        return _resume_failure(current, records, review, [exc.error])

    script_errors = _script_guard_errors(current, selected_idea.creative_idea_id, script)
    script_errors.extend(
        _validate_dataset(
            current.workflow_input,
            reference_insights=current.reference_insights,
            creative_ideas=current.creative_ideas,
            script_drafts=[script],
            review_decisions=[review],
        )
    )
    records.append(
        _step(
            records,
            "validate_script",
            "DETERMINISTIC_CODE",
            "FAILED" if script_errors else "SUCCESS",
            input_ids=[script.script_id],
            error_codes=[error.code for error in script_errors],
        )
    )
    if script_errors:
        return _resume_failure(current, records, review, script_errors, script)

    return current.model_copy(
        update={
            "status": WorkflowStatus.COMPLETED,
            "idea_review": review,
            "selected_idea_id": selected_idea.creative_idea_id,
            "script_draft": script,
            "validation_errors": [],
            "step_records": records,
        },
        deep=True,
    )


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


def _script_guard_errors(
    state: WorkflowState,
    selected_idea_id: str,
    script: ScriptDraft,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if script.creative_idea_id != selected_idea_id:
        errors.append(
            _workflow_error(
                "SCRIPT_IDEA_MISMATCH",
                "ScriptDraft does not bind to the selected CreativeIdea.",
                object_type="ScriptDraft",
                object_id=script.script_id,
                field="creative_idea_id",
                related_id=script.creative_idea_id,
            )
        )
    if script.product_id != state.workflow_input.product_profile.product_id:
        errors.append(
            _workflow_error(
                "SCRIPT_PRODUCT_MISMATCH",
                "ScriptDraft belongs to a different product.",
                object_type="ScriptDraft",
                object_id=script.script_id,
                field="product_id",
                related_id=script.product_id,
            )
        )
    return errors


def _failed_state(
    workflow_input: WorkflowInput,
    records: list[WorkflowStepRecord],
    errors: list[ValidationError],
    *,
    reference_insights: list | None = None,
    creative_ideas: list | None = None,
) -> WorkflowState:
    return WorkflowState(
        run_id=workflow_input.run_id,
        status=WorkflowStatus.FAILED,
        workflow_input=workflow_input,
        reference_insights=reference_insights or [],
        creative_ideas=creative_ideas or [],
        validation_errors=errors,
        step_records=records,
    )


def _resume_failure(
    state: WorkflowState,
    records: list[WorkflowStepRecord],
    review: ReviewDecision,
    errors: list[ValidationError],
    script: ScriptDraft | None = None,
) -> WorkflowState:
    return state.model_copy(
        update={
            "status": WorkflowStatus.FAILED,
            "idea_review": review,
            "script_draft": script,
            "validation_errors": errors,
            "step_records": records,
        },
        deep=True,
    )


def _workflow_error(
    code: str,
    message: str,
    *,
    object_type: str = "Workflow",
    object_id: str | None = None,
    field: str | None = None,
    related_id: str | None = None,
) -> ValidationError:
    return ValidationError(
        code=code,
        message=message,
        object_type=object_type,
        object_id=object_id,
        field=field,
        related_id=related_id,
    )


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

import inspect
import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import AsyncSessionLocal, get_db
from app.models.user import User
from app.repositories.case_repository import CaseRepository
from app.repositories.rubric_repository import RubricRepository
from app.schemas import rubric as rubric_schemas
from app.services import cancel_store, log_stream

CompareDraftRequest = rubric_schemas.CompareDraftRequest
RubricApproveRequest = rubric_schemas.RubricApproveRequest
RubricCreate = rubric_schemas.RubricCreate
RubricOut = rubric_schemas.RubricOut


class _SelectVariationRequest(BaseModel):
    selected_lane_code: Literal["A1", "A2", "A3", "A4", "B1", "B2"] | None = None


SelectVariationRequest = getattr(
    rubric_schemas,
    "SelectVariationRequest",
    _SelectVariationRequest,
)


class VariationOptionOut(BaseModel):
    lane_code: str
    label: str
    what_changes: str
    why_it_fits: str
    expected_answer_reuse: str
    main_red_flag: str


router = APIRouter(prefix="/rubrics", tags=["rubrics"])
_INTERMEDIATE_FI_STATUSES = {"awaiting_review", "variation_pending"}


def _filter_kwargs(method: object, kwargs: dict) -> dict:
    parameters = inspect.signature(method).parameters
    return {key: value for key, value in kwargs.items() if key in parameters}


async def _call_repo_method(method: object, **kwargs: object) -> object:
    return await method(**_filter_kwargs(method, kwargs))


async def _build_rubric_background(
    rubric_id: uuid.UUID, question: str, case_text: str | None = None
) -> None:
    """Run rubric construction pipeline in the background."""
    from app.services import rubric_service  # noqa: PLC0415

    sid = str(rubric_id)
    try:
        payload = await rubric_service.build_rubric(
            stream_id=sid, question=question, case_text=case_text
        )
    except Exception as exc:  # noqa: BLE001
        log_stream.log(sid, f"[ERROR] Rubric pipeline failed: {exc}")
        async with AsyncSessionLocal() as db:
            repo = RubricRepository(db)
            await repo.set_status(rubric_id, "failed")
        return

    if cancel_store.is_cancelled(sid):
        return

    # FI path: Phase A paused for human review — save intermediate results without freezing.
    if payload.get("fi_status") == "awaiting_review":
        async with AsyncSessionLocal() as db:
            repo = RubricRepository(db)
            await _call_repo_method(
                repo.save_fi_intermediate,
                rubric_id=rubric_id,
                fi_status="awaiting_review",
                fi_stream_id=payload.get("fi_stream_id"),
                gold_answer=payload.get("gold_answer"),
                weak_reference_text=payload.get("weak_reference_text"),
                self_audit_result=payload.get("self_audit_result"),
                screening_result=payload.get("screening_result"),
                source_extraction=payload.get("source_extraction"),
                routing_metadata=payload.get("routing_metadata"),
                doctrine_pack=payload.get("doctrine_pack"),
                gold_packet_mapping=payload.get("gold_packet_mapping"),
                predicted_failure_modes=payload.get("predicted_failure_modes"),
                question_analysis=payload.get("question_analysis"),
                controller_card=payload.get("controller_card"),
                controller_card_version=payload.get("controller_card_version"),
                workflow_source_case_name=payload.get("workflow_source_case_name"),
                workflow_source_case_citation=payload.get("workflow_source_case_citation"),
                case_citation_verification_mode=payload.get(
                    "case_citation_verification_mode",
                    False,
                ),
            )
        log_stream.log(sid, "[GATE] Intermediate results saved. Awaiting human review.")
        return

    # Non-FI path (or FI fallback): freeze and persist the full rubric.
    async with AsyncSessionLocal() as db:
        repo = RubricRepository(db)
        await _call_repo_method(
            repo.update_rubric_data,
            rubric_id=rubric_id,
            criteria=payload["criteria"],
            decomposition_tree=payload.get("decomposition_tree"),
            refinement_passes=payload.get("refinement_passes"),
            stopping_metadata=payload.get("stopping_metadata"),
            conditioning_sample=payload.get("conditioning_sample"),
            setup_responses=payload.get("setup_responses"),
            strong_reference_text=payload.get("strong_reference_text"),
            weak_reference_text=payload.get("weak_reference_text"),
            screening_result=payload.get("screening_result"),
            source_extraction=payload.get("source_extraction"),
            routing_metadata=payload.get("routing_metadata"),
            doctrine_pack=payload.get("doctrine_pack"),
            gold_packet_mapping=payload.get("gold_packet_mapping"),
            predicted_failure_modes=payload.get("predicted_failure_modes"),
            gold_answer=payload.get("gold_answer"),
            question_analysis=payload.get("question_analysis"),
            controller_card=payload.get("controller_card"),
            controller_card_version=payload.get("controller_card_version"),
            selected_lane_code=payload.get("selected_lane_code"),
            dual_rubric_mode=payload.get("dual_rubric_mode"),
            base_question=payload.get("base_question"),
            base_gold_answer=payload.get("base_gold_answer"),
            variation_question=payload.get("variation_question"),
            variation_criteria=payload.get("variation_criteria"),
            delta_log=payload.get("delta_log"),
        )
    log_stream.log(sid, "Rubric frozen and persisted.")


@router.post("", response_model=RubricOut, status_code=status.HTTP_201_CREATED)
async def create_rubric(
    body: RubricCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RubricOut:
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(body.case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    repo = RubricRepository(db)
    rubric = await repo.create_standalone(case_id=body.case_id, question=body.question)

    background_tasks.add_task(_build_rubric_background, rubric.id, body.question, case.raw_text)
    return RubricOut.model_validate(rubric)


@router.get("", response_model=list[RubricOut])
async def list_rubrics(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[RubricOut]:
    repo = RubricRepository(db)
    rubrics = await repo.list_all()
    return [RubricOut.model_validate(r) for r in rubrics]


@router.get("/frozen", response_model=list[RubricOut])
async def list_frozen_rubrics(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[RubricOut]:
    repo = RubricRepository(db)
    rubrics = await repo.list_frozen()
    return [RubricOut.model_validate(r) for r in rubrics]


@router.get("/evaluation/{evaluation_id}", response_model=RubricOut)
async def get_rubric_by_evaluation(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RubricOut:
    rubric = await RubricRepository(db).get_by_evaluation_id(evaluation_id)
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rubric found for this evaluation.",
        )
    return RubricOut.model_validate(rubric)


@router.get("/{rubric_id}/logs")
async def get_rubric_logs(
    rubric_id: uuid.UUID,
    offset: int = 0,
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Return pipeline log lines for a rubric build, optionally from a given offset."""
    lines = log_stream.get_lines(str(rubric_id), offset)
    return {"lines": lines, "total": log_stream.total(str(rubric_id))}


@router.post("/{rubric_id}/stop", response_model=RubricOut)
async def stop_rubric_build(
    rubric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> RubricOut:
    """Cancel a running rubric build."""
    repo = RubricRepository(db)
    rubric = await repo.get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")

    if rubric.status not in ("building",):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric is not currently building.",
        )

    cancel_store.cancel(str(rubric_id))
    await repo.set_status(rubric_id, "failed")
    log_stream.log(str(rubric_id), "[stopped] Rubric build stopped by user.")

    rubric = await repo.get_by_id(rubric_id)
    return RubricOut.model_validate(rubric)


@router.post("/{rubric_id}/rerun", response_model=RubricOut)
async def rerun_rubric(
    rubric_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> RubricOut:
    """Re-run a failed rubric build, reusing the same case and question."""
    repo = RubricRepository(db)
    rubric = await repo.get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")

    if rubric.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Can only re-run a failed rubric.",
        )

    question = rubric.question

    cancel_store.clear(str(rubric_id))
    log_stream.clear(str(rubric_id))

    await repo.reset_for_rerun(rubric_id)

    # Re-fetch case_text so the FI pipeline can run if the case has source material.
    case_text: str | None = None
    if rubric.case_id:
        case = await CaseRepository(db).get_by_id(rubric.case_id)
        if case:
            case_text = case.raw_text

    background_tasks.add_task(_build_rubric_background, rubric.id, question, case_text)

    rubric = await repo.get_by_id(rubric_id)
    return RubricOut.model_validate(rubric)


@router.get("/{rubric_id}", response_model=RubricOut)
async def get_rubric(
    rubric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RubricOut:
    rubric = await RubricRepository(db).get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    return RubricOut.model_validate(rubric)


async def _build_rubric_phase_b_background(
    rubric_id: uuid.UUID,
    variation_context: dict | None = None,
) -> None:
    """Resume Phase B of the FI rubric pipeline after human approval."""
    from app.services import rubric_service  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        rubric = await RubricRepository(db).get_by_id(rubric_id)
        if not rubric:
            return
        sid = rubric.fi_stream_id or str(rubric_id)
        question = rubric.question
        gold_answer = rubric.gold_answer
        weak_text = rubric.weak_reference_text
        source_extraction = rubric.source_extraction
        doctrine_pack = rubric.doctrine_pack
        controller_card = (
            variation_context.get("controller_card")
            if variation_context is not None
            else getattr(rubric, "controller_card", None)
        )
        selected_lane_code = (
            variation_context.get("selected_lane_code")
            if variation_context is not None
            else getattr(rubric, "selected_lane_code", None)
        )
        dual_rubric_mode = (
            bool(variation_context.get("dual_rubric_mode"))
            if variation_context is not None
            else bool(getattr(rubric, "dual_rubric_mode", False))
        )
        base_question = (
            variation_context.get("base_question")
            if variation_context is not None
            else getattr(rubric, "question", None)
        )
        base_gold_answer = (
            variation_context.get("base_gold_answer")
            if variation_context is not None
            else gold_answer
        )

    if not gold_answer:
        log_stream.log(str(rubric_id), "[ERROR] Phase B: no gold_answer found. Aborting.")
        async with AsyncSessionLocal() as db:
            await RubricRepository(db).set_status(rubric_id, "failed")
        return

    log_stream.log(sid, "[Phase B] Background task started.")
    try:
        payload = await rubric_service.build_rubric_phase_b(
            stream_id=sid,
            question=base_question or question,
            gold_answer=base_gold_answer or gold_answer,
            weak_text=weak_text,
            source_extraction=source_extraction,
            doctrine_pack=doctrine_pack,
            controller_card=controller_card,
            selected_lane_code=selected_lane_code,
            dual_rubric_mode=dual_rubric_mode,
        )
    except Exception as exc:  # noqa: BLE001
        log_stream.log(sid, f"[ERROR] Phase B pipeline failed: {exc}")
        async with AsyncSessionLocal() as db:
            await RubricRepository(db).set_status(rubric_id, "failed")
        return

    if cancel_store.is_cancelled(sid):
        return

    async with AsyncSessionLocal() as db:
        repo = RubricRepository(db)
        rubric_snap = await repo.get_by_id(rubric_id)
        await _call_repo_method(
            repo.update_rubric_data,
            rubric_id=rubric_id,
            criteria=payload["criteria"],
            decomposition_tree=payload.get("decomposition_tree"),
            refinement_passes=payload.get("refinement_passes"),
            stopping_metadata=payload.get("stopping_metadata"),
            conditioning_sample=payload.get("conditioning_sample"),
            setup_responses=payload.get("setup_responses"),
            strong_reference_text=payload.get("strong_reference_text"),
            weak_reference_text=payload.get("weak_reference_text"),
            gold_answer=payload.get("gold_answer"),
            # Preserve Phase A fields already on the rubric.
            screening_result=rubric_snap.screening_result if rubric_snap else None,
            source_extraction=payload.get("source_extraction"),
            routing_metadata=rubric_snap.routing_metadata if rubric_snap else None,
            doctrine_pack=payload.get("doctrine_pack"),
            gold_packet_mapping=rubric_snap.gold_packet_mapping if rubric_snap else None,
            predicted_failure_modes=rubric_snap.predicted_failure_modes if rubric_snap else None,
            self_audit_result=rubric_snap.self_audit_result if rubric_snap else None,
            controller_card=payload.get("controller_card") or controller_card,
            controller_card_version=payload.get("controller_card_version"),
            selected_lane_code=payload.get("selected_lane_code") or selected_lane_code,
            dual_rubric_mode=payload.get("dual_rubric_mode", dual_rubric_mode),
            base_question=payload.get("base_question") or base_question,
            base_gold_answer=payload.get("base_gold_answer") or base_gold_answer,
            variation_question=payload.get("variation_question"),
            variation_criteria=payload.get("variation_criteria"),
            delta_log=payload.get("delta_log"),
        )
        await repo.approve_fi(rubric_id, fi_status="completed")
    log_stream.log(sid, "Rubric frozen and persisted (Phase B complete).")


@router.post("/{rubric_id}/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_rubric(
    rubric_id: uuid.UUID,
    body: RubricApproveRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> dict:
    """Record a human review decision for a rubric paused at the HITL gate.

    Actions:
    - ``approve``: Launch Phase B (setup responses -> cluster -> refine -> freeze).
    - ``reject``:  Mark rubric as failed so it can be re-run via POST /rerun.
    - ``reroute``: Clear gold-answer fields and restart the full FI pipeline with a
                   different doctrine pack (re-runs from the beginning).

    Returns 202 for approve/reroute (background work started) or 200 for reject.
    """
    repo = RubricRepository(db)
    rubric = await repo.get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    if rubric.fi_status != "awaiting_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rubric is not awaiting review.",
        )

    if body.action == "approve":
        await repo.approve_fi(rubric_id, fi_status="variation_pending", review_notes=body.notes)
        return {"status": "approved", "rubric_id": str(rubric_id)}

    if body.action == "reject":
        await repo.approve_fi(rubric_id, fi_status="rejected", review_notes=body.notes)
        await repo.set_status(rubric_id, "failed")
        return {"status": "rejected", "rubric_id": str(rubric_id)}

    if body.action == "reroute":
        # Clear gold-answer fields and restart the full FI pipeline.
        cancel_store.clear(str(rubric_id))
        log_stream.clear(str(rubric_id))
        await repo.reset_for_rerun(rubric_id)
        await repo.approve_fi(rubric_id, fi_status=None, review_notes=body.notes)

        question = rubric.question
        case_text: str | None = None
        if rubric.case_id:
            case = await CaseRepository(db).get_by_id(rubric.case_id)
            if case:
                case_text = case.raw_text

        background_tasks.add_task(_build_rubric_background, rubric_id, question, case_text)
        return {"status": "rerouting", "rubric_id": str(rubric_id)}

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unknown action: {body.action!r}",
    )


@router.post(
    "/{rubric_id}/variation-menu",
    response_model=list[VariationOptionOut],
    status_code=status.HTTP_200_OK,
)
async def get_variation_menu(
    rubric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> list[VariationOptionOut]:
    from app.services import frank_service  # noqa: PLC0415

    rubric = await RubricRepository(db).get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    if rubric.fi_status != "variation_pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Variation menu is only available after approval.",
        )
    controller_card = getattr(rubric, "controller_card", None)
    if not controller_card:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric has no controller_card. Complete Phase A first.",
        )
    if not rubric.doctrine_pack:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric has no doctrine_pack. Complete Phase A first.",
        )

    options = await frank_service.generate_variation_menu(
        rubric.fi_stream_id or str(rubric_id),
        controller_card,
        rubric.doctrine_pack,
    )
    return [VariationOptionOut.model_validate(option) for option in options]


@router.post(
    "/{rubric_id}/select-variation",
    response_model=RubricOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def select_variation(
    rubric_id: uuid.UUID,
    body: SelectVariationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> RubricOut:
    from app.services import frank_service  # noqa: PLC0415

    repo = RubricRepository(db)
    rubric = await repo.get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    if rubric.fi_status != "variation_pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rubric is not waiting for a variation selection.",
        )

    try:
        variation_context = await frank_service.apply_variation_selection(
            rubric_id,
            body.selected_lane_code,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    background_tasks.add_task(_build_rubric_phase_b_background, rubric_id, variation_context)
    refreshed = await repo.get_by_id(rubric_id)
    if not refreshed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    return RubricOut.model_validate(refreshed)


@router.post("/{rubric_id}/validate-question", status_code=status.HTTP_200_OK)
async def validate_rubric_question(
    rubric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> dict:
    """Run FI question-writing checklist against the rubric's question.

    Returns a JSON object with keys: checks, red_flags, overall_pass, suggestions.
    Requires the rubric to have source_extraction populated (run after FI Phase 2).
    Returns 422 when source_extraction is not available.
    """
    from app.services import rubric_service  # noqa: PLC0415

    repo = RubricRepository(db)
    rubric = await repo.get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    if not rubric.source_extraction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric has no source_extraction. Run FI Phase 2 first.",
        )
    result = await rubric_service.validate_question(
        stream_id=None,
        question=rubric.question or "",
        source_extraction=rubric.source_extraction,
        doctrine_pack=rubric.doctrine_pack,
    )
    # Persist the result on the rubric row
    rubric.question_analysis = result
    await db.commit()
    return result


@router.post("/{rubric_id}/generate-question", status_code=status.HTTP_200_OK)
async def generate_rubric_question(
    rubric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> dict:
    """Generate a new neutral exam-style question from source extraction and gold packet mapping.

    Returns a JSON object with keys: question, internal_notes.
    Requires source_extraction and gold_packet_mapping to be populated.
    Returns 422 when either is missing.
    """
    from app.services import rubric_service  # noqa: PLC0415

    repo = RubricRepository(db)
    rubric = await repo.get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    if not rubric.source_extraction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric has no source_extraction. Run FI Phase 2 first.",
        )
    if not rubric.gold_packet_mapping:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric has no gold_packet_mapping. Run FI Phase 4 first.",
        )
    result = await rubric_service.generate_question(
        stream_id=None,
        source_extraction=rubric.source_extraction,
        gold_packet_mapping=rubric.gold_packet_mapping,
        doctrine_pack=rubric.doctrine_pack,
    )
    # Persist the generated question on the rubric row
    if result.get("question"):
        rubric.generated_question = result["question"]
    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Phase 12: Operating modes A, C, E
# ---------------------------------------------------------------------------


@router.post("/{rubric_id}/extract-only", status_code=status.HTTP_200_OK)
async def extract_only(
    rubric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> dict:
    """Mode A: run source intake screening + extraction + routing only.

    Returns screening_result, source_extraction, routing_metadata, doctrine_pack.
    Requires the rubric to have a case with raw_text.
    Returns 422 when no case_text is available.
    """
    from app.services import rubric_service  # noqa: PLC0415

    repo = RubricRepository(db)
    rubric = await repo.get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")

    case_text: str | None = None
    if rubric.case_id:
        case = await CaseRepository(db).get_by_id(rubric.case_id)
        if case:
            case_text = case.raw_text

    if not case_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric has no case with raw_text. Upload a case first.",
        )

    result = await rubric_service.run_mode_a(
        stream_id=str(rubric_id),
        case_text=case_text,
        question=rubric.question or "",
    )

    # Persist intermediate extraction results on the rubric row
    rubric.screening_result = result.get("screening_result")
    rubric.source_extraction = result.get("source_extraction")
    rubric.routing_metadata = result.get("routing_metadata")
    rubric.doctrine_pack = result.get("doctrine_pack")
    await db.commit()
    return result


@router.post("/{rubric_id}/compare-draft", status_code=status.HTTP_200_OK)
async def compare_draft(
    rubric_id: uuid.UUID,
    body: CompareDraftRequest,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> dict:
    """Mode C: compare a draft answer against the rubric's source extraction.

    Returns an 8-heading comparison dict.
    Requires the rubric to have source_extraction populated.
    Returns 422 when source_extraction is not available.
    """
    from app.services import rubric_service  # noqa: PLC0415

    repo = RubricRepository(db)
    rubric = await repo.get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    if not rubric.source_extraction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric has no source_extraction. Run extract-only or build the rubric first.",
        )

    return await rubric_service.compare_draft_to_source(
        stream_id=None,
        draft_text=body.draft_text,
        source_extraction=rubric.source_extraction,
        doctrine_pack=rubric.doctrine_pack,
    )


@router.post("/{rubric_id}/draft-failure-modes", status_code=status.HTTP_200_OK)
async def draft_failure_modes(
    rubric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> list:
    """Mode E: predict failure modes from source extraction and doctrine pack.

    Uses existing gold_packet_mapping if present; generates it on the fly if not.
    Requires the rubric to have source_extraction and doctrine_pack populated.
    Returns 422 when source_extraction is not available.
    """
    from app.services import rubric_service  # noqa: PLC0415

    repo = RubricRepository(db)
    rubric = await repo.get_by_id(rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    if not rubric.source_extraction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric has no source_extraction. Run extract-only or build the rubric first.",
        )
    if not rubric.doctrine_pack:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric has no doctrine_pack. Run extract-only or build the rubric first.",
        )

    failure_modes = await rubric_service.run_mode_e(
        stream_id=str(rubric_id),
        source_extraction=rubric.source_extraction,
        doctrine_pack=rubric.doctrine_pack,
        gold_packet_mapping=rubric.gold_packet_mapping,
        question=rubric.question or "",
    )

    # Persist failure modes on the rubric row
    rubric.predicted_failure_modes = failure_modes
    await db.commit()
    return failure_modes

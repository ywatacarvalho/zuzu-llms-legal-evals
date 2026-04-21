import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import AsyncSessionLocal, get_db
from app.models.evaluation import StatusEnum
from app.models.response import ModelResponse
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.rubric_repository import RubricRepository
from app.schemas.analysis import AnalysisOut, AnalysisRunRequest
from app.services import analysis_service, log_stream

# In-memory tracker for background analysis runs (single-server deployment).
_running: set[str] = set()
_failed: set[str] = set()
_judge_models_param: dict[str, list[str]] = {}  # evaluation_id -> judge_models


async def _load_responses(db: AsyncSession, evaluation_id: uuid.UUID) -> list:
    result = await db.execute(
        select(ModelResponse)
        .where(ModelResponse.evaluation_id == evaluation_id)
        .order_by(ModelResponse.run_index)
    )
    return list(result.scalars().all())


async def _load_responses_by_version(
    db: AsyncSession, evaluation_id: uuid.UUID, question_version: str
) -> list:
    result = await db.execute(
        select(ModelResponse)
        .where(ModelResponse.evaluation_id == evaluation_id)
        .where(ModelResponse.question_version == question_version)
        .order_by(ModelResponse.run_index)
    )
    return list(result.scalars().all())


async def _run_analysis_background(
    evaluation_id: uuid.UUID,
    judge_models: list[str] | None = None,
) -> None:
    """Background task: run the full analysis pipeline and persist the result."""
    eid = str(evaluation_id)
    try:
        # Load inputs in a short-lived session so the connection is released
        # before the long-running embedding + scoring phase begins.
        async with AsyncSessionLocal() as db:
            evaluation = await EvaluationRepository(db).get_by_id(evaluation_id)
            if not evaluation:
                log_stream.log(eid, "[analysis][ERROR] Evaluation not found.")
                return

            rubric_repo = RubricRepository(db)
            rubric = (
                await rubric_repo.get_by_id(evaluation.rubric_id)
                if evaluation.rubric_id
                else await rubric_repo.get_by_evaluation_id(evaluation_id)
            )
            if not rubric or not rubric.criteria:
                log_stream.log(eid, "[analysis][ERROR] No frozen rubric found.")
                return

            question = evaluation.question
            criteria = rubric.criteria
            doctrine_pack = getattr(rubric, "doctrine_pack", None)
            controller_card = getattr(rubric, "controller_card", None)
            case_citation_verification_mode = (
                getattr(rubric, "case_citation_verification_mode", False) or False
            )
            workflow_source_case_name = getattr(rubric, "workflow_source_case_name", None)
            workflow_source_case_citation = getattr(rubric, "workflow_source_case_citation", None)
            dual_rubric_mode = getattr(rubric, "dual_rubric_mode", False) or False
            variation_criteria = getattr(rubric, "variation_criteria", None)
            variation_question = getattr(rubric, "variation_question", None)

            if dual_rubric_mode and variation_question:
                responses = await _load_responses_by_version(db, evaluation_id, "base")
                variation_responses = await _load_responses_by_version(
                    db, evaluation_id, "variation"
                )
            else:
                responses = await _load_responses(db, evaluation_id)
                variation_responses = None

            if not responses:
                log_stream.log(eid, "[analysis][ERROR] No responses found.")
                return

        # Run the CPU/network-heavy pipeline with no DB connection held.
        data = await analysis_service.run_analysis(
            question=question,
            responses=responses,
            rubric_criteria=criteria,
            evaluation_id=eid,
            doctrine_pack=doctrine_pack,
            judge_models=judge_models,
            controller_card=controller_card,
            case_citation_verification_mode=case_citation_verification_mode,
            workflow_source_case_name=workflow_source_case_name,
            workflow_source_case_citation=workflow_source_case_citation,
            dual_rubric_mode=dual_rubric_mode,
            variation_criteria=variation_criteria,
            variation_question=variation_question,
            variation_responses=variation_responses,
        )

        # Persist the result in a fresh short-lived session.
        async with AsyncSessionLocal() as db:
            await AnalysisRepository(db).create(
                evaluation_id=evaluation_id,
                k=data["k"],
                clusters=data["clusters"],
                centroid_indices=data["centroid_indices"],
                scores=data["scores"],
                winning_cluster=data["winning_cluster"],
                model_shares=data["model_shares"],
                weighting_mode=data.get("weighting_mode"),
                baseline_scores=data.get("baseline_scores"),
                weighting_comparison=data.get("weighting_comparison"),
                silhouette_scores_by_k=data.get("silhouette_scores_by_k"),
                failure_tags=data.get("failure_tags"),
                centroid_composition=data.get("centroid_composition"),
                penalties_applied=data.get("penalties_applied"),
                cap_status=data.get("cap_status"),
                final_scores=data.get("final_scores"),
                case_citation_metadata=data.get("case_citation_metadata"),
                judge_panel=data.get("judge_panel"),
                judge_votes=data.get("judge_votes"),
                zak_review_flag=data.get("zak_review_flag"),
                variation_scores=data.get("variation_scores"),
            )
        log_stream.log(eid, "[analysis] Analysis saved.")
    except Exception as exc:  # noqa: BLE001
        log_stream.log(eid, f"[analysis][ERROR] {exc}")
        _failed.add(eid)
    finally:
        _running.discard(eid)
        _judge_models_param.pop(eid, None)


router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/{evaluation_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_analysis(
    evaluation_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    response: Response,
    body: AnalysisRunRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> dict:
    """
    Kick off the analysis pipeline in a background task (steps 5-8).
    Returns 202 immediately. Poll GET /status to track progress.
    Idempotent: returns the existing Analysis record (200) if one already exists.
    Accepts optional body with judge_models (validated against JUDGE_MODELS allowlist).
    """
    from app.services.frank_instructions import JUDGE_MODELS  # noqa: PLC0415

    eid = str(evaluation_id)
    analysis_repo = AnalysisRepository(db)

    existing = await analysis_repo.get_by_evaluation_id(evaluation_id)
    if existing:
        response.status_code = status.HTTP_200_OK
        return AnalysisOut.model_validate(existing).model_dump(mode="json")

    if eid in _running:
        return {"status": "running"}

    judge_models: list[str] | None = None
    if body and body.judge_models:
        invalid = [m for m in body.judge_models if m not in JUDGE_MODELS]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"judge_models contains models not in the JUDGE_MODELS allowlist: {invalid}",
            )
        judge_models = body.judge_models

    evaluation = await EvaluationRepository(db).get_by_id(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    if evaluation.status != StatusEnum.done:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Evaluation must be in 'done' status before running analysis.",
        )

    rubric_repo = RubricRepository(db)
    rubric = (
        await rubric_repo.get_by_id(evaluation.rubric_id)
        if evaluation.rubric_id
        else await rubric_repo.get_by_evaluation_id(evaluation_id)
    )
    if not rubric or not rubric.criteria:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No frozen rubric found for this evaluation.",
        )

    responses = await _load_responses(db, evaluation_id)
    if not responses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No responses found for this evaluation.",
        )

    _running.add(eid)
    _failed.discard(eid)
    log_stream.log(eid, "[analysis] Pipeline queued.")
    background_tasks.add_task(_run_analysis_background, evaluation_id, judge_models)
    return {"status": "running"}


@router.get("/{evaluation_id}/status")
async def get_analysis_status(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> dict:
    """Return the current analysis status: done, running, failed, or not_started."""
    eid = str(evaluation_id)
    existing = await AnalysisRepository(db).get_by_evaluation_id(evaluation_id)
    if existing:
        return {"status": "done"}
    if eid in _running:
        return {"status": "running"}
    if eid in _failed:
        return {"status": "failed"}
    return {"status": "not_started"}


@router.get("/{evaluation_id}/logs")
async def get_analysis_logs(
    evaluation_id: uuid.UUID,
    offset: int = 0,
    _: object = Depends(get_current_user),
) -> dict:
    """Return analysis pipeline log lines, optionally from a given offset."""
    lines = log_stream.get_lines(str(evaluation_id), offset)
    return {"lines": lines, "total": log_stream.total(str(evaluation_id))}


@router.get("/{evaluation_id}", response_model=AnalysisOut)
async def get_analysis(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> AnalysisOut:
    analysis = await AnalysisRepository(db).get_by_evaluation_id(evaluation_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return AnalysisOut.model_validate(analysis)

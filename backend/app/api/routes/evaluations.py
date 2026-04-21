import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.evaluation import StatusEnum
from app.models.response import ModelResponse
from app.models.user import User
from app.repositories.evaluation_repository import EvaluationRepository
from app.schemas.evaluation import EvaluationCreate, EvaluationOut, ModelInfoOut, ModelResponseOut
from app.services import cancel_store, log_stream
from app.services.available_models import AVAILABLE_MODELS
from app.services.response_service import run_evaluation_pipeline

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("/models", response_model=list[ModelInfoOut])
async def list_available_models(
    _current_user: User = Depends(get_current_user),
) -> list[ModelInfoOut]:
    return [ModelInfoOut(id=m.id, name=m.name, provider=m.provider) for m in AVAILABLE_MODELS]


@router.post("", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    body: EvaluationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> EvaluationOut:
    from app.repositories.rubric_repository import RubricRepository  # noqa: PLC0415

    rubric_repo = RubricRepository(db)
    rubric = await rubric_repo.get_by_id(body.rubric_id)
    if not rubric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    if rubric.status != "frozen":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric is not frozen yet.",
        )

    repo = EvaluationRepository(db)
    evaluation = await repo.create(
        rubric_id=rubric.id,
        case_id=rubric.case_id,
        question=rubric.question,
        model_names=body.model_names,
    )

    # Link rubric to evaluation
    rubric.evaluation_id = evaluation.id
    await db.commit()

    await repo.set_status(evaluation.id, StatusEnum.running)
    await db.refresh(evaluation)

    background_tasks.add_task(
        run_evaluation_pipeline,
        evaluation_id=evaluation.id,
        question=rubric.question,
        model_names=body.model_names,
        variation_question=getattr(rubric, "variation_question", None),
    )

    out = EvaluationOut.model_validate(evaluation)
    return out


@router.get("", response_model=list[EvaluationOut])
async def list_evaluations(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[EvaluationOut]:
    repo = EvaluationRepository(db)
    evaluations = await repo.list_all()
    results = []
    for e in evaluations:
        out = EvaluationOut.model_validate(e)
        out.response_count = await repo.count_responses(e.id)
        results.append(out)
    return results


@router.get("/{evaluation_id}/responses", response_model=list[ModelResponseOut])
async def list_responses(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[ModelResponseOut]:
    """Return all model responses for an evaluation, ordered by model then run_index."""
    result = await db.execute(
        select(ModelResponse)
        .where(ModelResponse.evaluation_id == evaluation_id)
        .order_by(ModelResponse.model_name, ModelResponse.run_index)
    )
    rows = list(result.scalars().all())
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No responses found")
    return [ModelResponseOut.model_validate(r) for r in rows]


@router.get("/{evaluation_id}/logs")
async def get_evaluation_logs(
    evaluation_id: uuid.UUID,
    offset: int = 0,
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Return pipeline log lines for an evaluation, optionally from a given offset."""
    lines = log_stream.get_lines(str(evaluation_id), offset)
    return {"lines": lines, "total": log_stream.total(str(evaluation_id))}


@router.post("/{evaluation_id}/stop", response_model=EvaluationOut)
async def stop_evaluation(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> EvaluationOut:
    """Cancel a running evaluation. Sets status to failed and raises a cancellation flag."""
    repo = EvaluationRepository(db)
    evaluation = await repo.get_by_id(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    _ACTIVE = {StatusEnum.running}
    if evaluation.status not in _ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Evaluation is not currently running.",
        )

    cancel_store.cancel(str(evaluation_id))
    await repo.set_status(evaluation_id, StatusEnum.failed)
    log_stream.log(str(evaluation_id), "[stopped] Pipeline stopped by user.")

    evaluation = await repo.get_by_id(evaluation_id)
    await db.refresh(evaluation)
    out = EvaluationOut.model_validate(evaluation)
    out.response_count = await repo.count_responses(evaluation_id)
    return out


@router.post(
    "/{evaluation_id}/rerun",
    response_model=EvaluationOut,
    status_code=status.HTTP_201_CREATED,
)
async def rerun_evaluation(
    evaluation_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> EvaluationOut:
    """Re-run comparison responses for a completed or failed evaluation.

    Preserves the frozen rubric; only wipes analysis + model responses.
    """
    repo = EvaluationRepository(db)
    evaluation = await repo.get_by_id(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    _TERMINAL = {StatusEnum.done, StatusEnum.failed}
    if evaluation.status not in _TERMINAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Can only re-run a completed or failed evaluation.",
        )

    # Read before the first commit
    question = evaluation.question
    model_names = evaluation.model_names or []

    from app.repositories.rubric_repository import RubricRepository  # noqa: PLC0415

    rubric_repo = RubricRepository(db)
    rerun_rubric = (
        await rubric_repo.get_by_id(evaluation.rubric_id) if evaluation.rubric_id else None
    )
    variation_question = getattr(rerun_rubric, "variation_question", None)

    # Clear flags and logs
    cancel_store.clear(str(evaluation_id))
    log_stream.clear(str(evaluation_id))

    # Wipe dependent data: analysis + responses only (keep rubric)
    await db.execute(delete(Analysis).where(Analysis.evaluation_id == evaluation_id))
    await db.execute(delete(ModelResponse).where(ModelResponse.evaluation_id == evaluation_id))
    await db.commit()

    await repo.set_status(evaluation_id, StatusEnum.running)

    background_tasks.add_task(
        run_evaluation_pipeline,
        evaluation_id=evaluation_id,
        question=question,
        model_names=model_names,
        variation_question=variation_question,
    )

    evaluation = await repo.get_by_id(evaluation_id)
    await db.refresh(evaluation)
    out = EvaluationOut.model_validate(evaluation)
    out.response_count = 0
    return out


@router.get("/{evaluation_id}", response_model=EvaluationOut)
async def get_evaluation(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> EvaluationOut:
    repo = EvaluationRepository(db)
    evaluation = await repo.get_by_id(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    out = EvaluationOut.model_validate(evaluation)
    out.response_count = await repo.count_responses(evaluation_id)
    return out

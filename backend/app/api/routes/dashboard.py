from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.case import LegalCase
from app.models.evaluation import Evaluation
from app.schemas.dashboard import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> DashboardStats:
    total_cases = (await db.execute(select(func.count()).select_from(LegalCase))).scalar_one()
    evaluations_run = (await db.execute(select(func.count()).select_from(Evaluation))).scalar_one()

    model_names_rows = (await db.execute(select(Evaluation.model_names))).scalars().all()
    unique_models: set[str] = set()
    for names in model_names_rows:
        if isinstance(names, list):
            unique_models.update(names)
    models_evaluated = len(unique_models)

    avg_k_result = (await db.execute(select(func.avg(Analysis.k)))).scalar_one()
    avg_clusters = round(float(avg_k_result), 1) if avg_k_result is not None else 0.0

    return DashboardStats(
        total_cases=total_cases,
        evaluations_run=evaluations_run,
        models_evaluated=models_evaluated,
        avg_clusters=avg_clusters,
    )

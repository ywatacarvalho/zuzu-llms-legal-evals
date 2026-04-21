import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation, StatusEnum
from app.models.response import ModelResponse


class EvaluationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        rubric_id: uuid.UUID,
        case_id: uuid.UUID,
        question: str,
        model_names: list[str],
    ) -> Evaluation:
        evaluation = Evaluation(
            rubric_id=rubric_id,
            case_id=case_id,
            question=question,
            model_names=model_names,
            status=StatusEnum.pending,
        )
        self.db.add(evaluation)
        await self.db.commit()
        await self.db.refresh(evaluation)
        return evaluation

    async def get_by_id(self, evaluation_id: uuid.UUID) -> Evaluation | None:
        return await self.db.get(Evaluation, evaluation_id)

    async def list_all(self) -> list[Evaluation]:
        result = await self.db.execute(select(Evaluation).order_by(desc(Evaluation.created_at)))
        return list(result.scalars().all())

    async def set_status(self, evaluation_id: uuid.UUID, status: StatusEnum) -> None:
        evaluation = await self.db.get(Evaluation, evaluation_id)
        if evaluation:
            evaluation.status = status
            await self.db.commit()

    async def count_responses(self, evaluation_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).where(ModelResponse.evaluation_id == evaluation_id)
        )
        return result.scalar_one()

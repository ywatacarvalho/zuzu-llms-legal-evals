import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import LegalCase


class CaseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, title: str, filename: str, raw_text: str | None) -> LegalCase:
        case = LegalCase(title=title, filename=filename, raw_text=raw_text)
        self.db.add(case)
        await self.db.commit()
        await self.db.refresh(case)
        return case

    async def get_by_id(self, case_id: uuid.UUID) -> LegalCase | None:
        result = await self.db.execute(select(LegalCase).where(LegalCase.id == case_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[LegalCase]:
        result = await self.db.execute(
            select(LegalCase).order_by(desc(LegalCase.created_at))
        )
        return list(result.scalars().all())

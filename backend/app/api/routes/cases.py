import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.case_repository import CaseRepository
from app.schemas.case import CaseOut
from app.services.case_service import derive_title, extract_text_from_pdf

router = APIRouter(prefix="/cases", tags=["cases"])

_ALLOWED_CONTENT_TYPES = {"application/pdf"}


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def upload_case(
    file: UploadFile,
    title: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> CaseOut:
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only PDF files are accepted.",
        )

    filename = file.filename or "upload.pdf"
    case_title = title.strip() if title.strip() else derive_title(filename)
    raw_text = await extract_text_from_pdf(file)

    repo = CaseRepository(db)
    case = await repo.create(
        title=case_title,
        filename=filename,
        raw_text=raw_text or None,
    )
    return CaseOut.model_validate(case)


@router.get("", response_model=list[CaseOut])
async def list_cases(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[CaseOut]:
    repo = CaseRepository(db)
    cases = await repo.list_all()
    return [CaseOut.model_validate(c) for c in cases]


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> CaseOut:
    repo = CaseRepository(db)
    case = await repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return CaseOut.model_validate(case)

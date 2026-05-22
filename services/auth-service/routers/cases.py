from datetime import datetime

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Case, CaseAssignment

router = APIRouter(prefix="/cases", tags=["cases"])


class CaseOut(BaseModel):
    id: str
    case_number: str
    title: str
    description: str | None
    status: str
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[CaseOut])
async def list_assigned_open_cases(
    x_user_id: str | None = Header(default=None, alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Returns OPEN cases the requesting user is assigned to. Used by upload form dropdown."""
    result = await db.execute(
        select(Case)
        .join(CaseAssignment, Case.id == CaseAssignment.case_id)
        .where(Case.status == "OPEN")
        .where(CaseAssignment.username == x_user_id)
        .where(CaseAssignment.is_active == True)
        .order_by(Case.case_number)
    )
    return result.scalars().all()

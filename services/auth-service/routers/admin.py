import bcrypt
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import Case, CaseAssignment, User

router = APIRouter(prefix="/admin", tags=["admin"])

ALLOWED_ROLES = {"investigator", "forensic_analyst", "legal_reviewer"}
ASSIGNABLE_ROLES = {"investigator", "forensic_analyst", "legal_reviewer"}


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreateUserIn(BaseModel):
    username: str
    password: str
    role: str


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


class CreateCaseIn(BaseModel):
    case_number: str
    title: str
    description: str | None = None


class AssignmentOut(BaseModel):
    id: str
    case_id: str
    username: str
    role_in_case: str
    assigned_at: datetime
    assigned_by: str
    is_active: bool

    class Config:
        from_attributes = True


class CreateAssignmentIn(BaseModel):
    username: str
    role_in_case: str


def _require_admin(x_user_role: str | None) -> None:
    if x_user_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


@router.get("/users", response_model=list[UserOut])
async def list_users(
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserIn,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)

    if body.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role must be one of: {', '.join(sorted(ALLOWED_ROLES))}",
        )

    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = User(username=body.username, hashed_password=hashed, role=body.role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    x_username: str | None = Header(default=None, alias="x-username"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.username == x_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

    await db.delete(user)
    await db.commit()


# ── Cases ──────────────────────────────────────────────────────────────────────

@router.get("/cases", response_model=list[CaseOut])
async def list_cases(
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)
    result = await db.execute(select(Case).order_by(Case.created_at))
    return result.scalars().all()


@router.post("/cases", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CreateCaseIn,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    x_username: str | None = Header(default=None, alias="x-username"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)

    import re
    if not re.match(r"^CASE-\d{4}-\d{3}$", body.case_number):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="case_number must match CASE-YYYY-NNN format",
        )

    existing = await db.execute(select(Case).where(Case.case_number == body.case_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Case number already exists")

    case = Case(
        case_number=body.case_number,
        title=body.title,
        description=body.description,
        created_by=x_username or "admin",
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case


@router.patch("/cases/{case_id}", response_model=CaseOut)
async def update_case_status(
    case_id: str,
    body: dict,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)

    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    new_status = body.get("status")
    if new_status not in {"OPEN", "CLOSED"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="status must be OPEN or CLOSED")

    case.status = new_status
    await db.commit()
    await db.refresh(case)
    return case


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)

    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    await db.delete(case)
    await db.commit()


# ── Case Assignments ───────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/assignments", response_model=list[AssignmentOut])
async def list_assignments(
    case_id: str,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)
    result = await db.execute(
        select(CaseAssignment)
        .where(CaseAssignment.case_id == case_id)
        .where(CaseAssignment.is_active == True)
        .order_by(CaseAssignment.assigned_at)
    )
    return result.scalars().all()


@router.post("/cases/{case_id}/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    case_id: str,
    body: CreateAssignmentIn,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    x_username: str | None = Header(default=None, alias="x-username"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)

    if body.role_in_case not in ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role_in_case must be one of: {', '.join(sorted(ASSIGNABLE_ROLES))}",
        )

    case_result = await db.execute(select(Case).where(Case.id == case_id))
    if not case_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    user_result = await db.execute(select(User).where(User.username == body.username))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    assignment = CaseAssignment(
        case_id=case_id,
        username=body.username,
        role_in_case=body.role_in_case,
        assigned_by=x_username or "admin",
    )
    db.add(assignment)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already assigned to this case")
    await db.refresh(assignment)
    return assignment


@router.delete("/cases/{case_id}/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    case_id: str,
    assignment_id: str,
    x_user_role: str | None = Header(default=None, alias="x-user-role"),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(x_user_role)

    result = await db.execute(
        select(CaseAssignment)
        .where(CaseAssignment.id == assignment_id)
        .where(CaseAssignment.case_id == case_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await db.delete(assignment)
    await db.commit()

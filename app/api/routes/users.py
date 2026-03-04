from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.session import get_db
from app.db.models.all_models import User, UserRole
from app.schemas.schemas import UserResponse
from app.api.deps.auth import get_current_user, require_roles

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))]
)

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0, limit: int = 100, 
    role: UserRole = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    query = select(User)
    if role:
        query = query.filter(User.role == role)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

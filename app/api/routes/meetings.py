from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import uuid

from app.db.session import get_db
from app.db.models.all_models import Meeting, User, UserRole
from app.schemas.schemas import MeetingCreate, MeetingResponse, MeetingUpdate
from app.api.deps.auth import get_current_user, require_roles

router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/", response_model=List[MeetingResponse])
async def list_meetings(
    skip: int = 0, limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Meeting).options(selectinload(Meeting.case)).offset(skip).limit(limit)
    result = await db.execute(query)
    meetings = result.scalars().all()
    
    for meeting in meetings:
        if meeting.case:
            setattr(meeting, 'case_code', meeting.case.case_code)
            
    return meetings

@router.post("/", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    meeting_in: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    meeting = Meeting(**meeting_in.model_dump())
    meeting.created_by = current_user.id
    db.add(meeting)
    await db.flush()
    
    if not meeting.meet_url:
        meeting.meet_url = f"http://localhost:5173/meeting/{meeting.id}"
    if not meeting.portal_url:
        portal_token = str(uuid.uuid4())
        meeting.portal_url = f"http://localhost:5173/portal/{portal_token}"
        
    await db.commit()
    await db.refresh(meeting)
    
    # Optional: pre-populate case_code if we needed to return it in the schema response
    if meeting.case_id:
        from app.db.models.all_models import Case
        case_res = await db.execute(select(Case).where(Case.id == meeting.case_id))
        c = case_res.scalar_one_or_none()
        if c:
            setattr(meeting, 'case_code', c.case_code)
            
    return meeting

@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Meeting).options(selectinload(Meeting.case)).filter(Meeting.id == meeting_id))
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if meeting.case:
        setattr(meeting, 'case_code', meeting.case.case_code)
        
    return meeting

@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: int, 
    meeting_in: MeetingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    result = await db.execute(select(Meeting).filter(Meeting.id == meeting_id))
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    update_data = meeting_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(meeting, key, value)
        
    await db.commit()
    await db.refresh(meeting)
    return meeting

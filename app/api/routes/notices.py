from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List,Optional

from app.db.session import get_db
from app.db.models.all_models import Notice, User, UserRole, NoticeStatus, NoticeDelivery, DeliveryChannel, DeliveryStatus, Meeting, MeetingStatus, AuditLog, ActorType, CaseRuleState, CaseParty, PartyType, Case
from app.schemas.schemas import NoticeCreate, NoticeResponse, NoticeUpdate
from app.api.deps.auth import get_current_user, require_roles
import uuid
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/notices",
    tags=["Notices"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/", response_model=List[NoticeResponse])
async def list_notices(
    skip: int = 0, limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.db.models.all_models import NoticeAttachment
    query = select(Notice).options(
        selectinload(Notice.case),
        selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
        selectinload(Notice.deliveries)
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    notices = result.scalars().all()
    
    # Attach case_code to response
    for notice in notices:
        if notice.case:
            setattr(notice, 'case_code', notice.case.case_code)
            
    return notices

@router.post("/", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
async def create_notice(
    notice_in: NoticeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    from app.services.notice_service import notice_service
    try:
        notice = await notice_service.create_notice(db, notice_in, current_user.id)
        
        # Rule State Check (Notice Count >= 3 enables closure)
        from app.db.models.all_models import CaseRuleState
        rule_res = await db.execute(select(CaseRuleState).where(CaseRuleState.case_id == notice.case_id))
        rule_state = rule_res.scalar_one_or_none()
        
        if not rule_state:
            rule_state = CaseRuleState(case_id=notice.case_id, notice_count=1, closure_enabled=False)
            db.add(rule_state)
        else:
            rule_state.notice_count += 1
            
        if rule_state.notice_count >= 3:
            rule_state.closure_enabled = True
            rule_state.closure_enabled_at = datetime.utcnow()
            
        await db.commit()
        return notice
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# @router.post("/", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
# async def create_notice(
#     notice_in: NoticeCreate,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
# ):
#     # 1. Ensure Case Exists and fetch parties
#     case_res = await db.execute(select(Case).where(Case.id == notice_in.case_id).options(selectinload(Case.parties)))
#     case = case_res.scalar_one_or_none()
#     if not case:
#         raise HTTPException(status_code=404, detail="Case not found")
        
#     # 2. Generate secure tokens
#     portal_token = str(uuid.uuid4())
#     meeting_id = str(uuid.uuid4())
#     meeting_url = f"http://localhost:5173/meeting/{meeting_id}"
#     portal_link = f"http://localhost:5173/portal/{portal_token}"
    
#     meeting = Meeting(
#         id=meeting_id,
#         case_id=case.id,
#         created_by=current_user.id,
#         scheduled_at=datetime.utcnow() + timedelta(days=7),
#         meet_url=meeting_url,
#         portal_url=portal_link,
#         status=MeetingStatus.scheduled,
#         notes=f"Automatically scheduled virtual hearing for Notice N-{notice_in.notice_no}"
#     )
#     db.add(meeting)
    
#     # 3. Create Notice
#     notice_content = notice_in.content or {}
#     notice_content.update({
#         "portal_token": portal_token,
#         "portal_link": portal_link,
#         "meeting_url": meeting_url
#     })
    
#     notice = Notice(
#         case_id=notice_in.case_id,
#         notice_no=notice_in.notice_no,
#         notice_type=notice_in.notice_type,
#         content=notice_content,
#         created_by=current_user.id,
#         status=NoticeStatus.draft
#     )
#     db.add(notice)
#     await db.flush()
    
#     # 4. Mock Delivery
#     applicants = [p for p in case.parties if p.party_type == PartyType.applicant]
#     for applicant in applicants:
#         target_phone = applicant.phone or applicant.phone_2 or "0000000000"
#         delivery = NoticeDelivery(
#             notice_id=notice.id,
#             channel=DeliveryChannel.sms,
#             to_address=target_phone,
#             status=DeliveryStatus.sent,
#             sent_at=datetime.utcnow(),
#             provider_message_id=str(uuid.uuid4())
#         )
#         db.add(delivery)
        
#     # 5. Audit Logs
#     audit1 = AuditLog(
#         actor_type=ActorType.internal,
#         actor_user_id=current_user.id,
#         action="NOTICE_CREATED",
#         entity_type="Notice",
#         entity_id=notice.id,
#         after={"notice_no": notice.notice_no}
#     )
#     audit2 = AuditLog(
#         actor_type=ActorType.system,
#         actor_user_id=current_user.id,
#         action="NOTICE_SENT",
#         entity_type="Notice",
#         entity_id=notice.id,
#         after={"status": "sent"}
#     )
#     db.add_all([audit1, audit2])
    
#     # 6. Rule State Check (Notice Count >= 3 enables closure)
#     rule_res = await db.execute(select(CaseRuleState).where(CaseRuleState.case_id == case.id))
#     rule_state = rule_res.scalar_one_or_none()
    
#     if not rule_state:
#         rule_state = CaseRuleState(case_id=case.id, notice_count=1, closure_enabled=False)
#         db.add(rule_state)
#     else:
#         rule_state.notice_count += 1
        
#     if rule_state.notice_count >= 3:
#         rule_state.closure_enabled = True
#         rule_state.closure_enabled_at = datetime.utcnow()
        
#     await db.commit()
#     await db.refresh(notice)
#     return notice

@router.get("/{notice_id}", response_model=NoticeResponse)
async def get_notice(
    notice_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.db.models.all_models import NoticeAttachment
    result = await db.execute(
        select(Notice).options(
            selectinload(Notice.case),
            selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
            selectinload(Notice.deliveries)
        ).filter(Notice.id == notice_id)
    )
    
    notice = result.scalars().first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
        
    if notice.case:
        setattr(notice, 'case_code', notice.case.case_code)
        
    return notice

@router.put("/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: int, 
    notice_in: NoticeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    result = await db.execute(select(Notice).filter(Notice.id == notice_id))
    notice = result.scalars().first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    
    update_data = notice_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(notice, key, value)
        
    await db.commit()
    await db.refresh(notice)
    return notice


@router.post("/{notice_id}/resend", response_model=NoticeResponse)
async def resend_notice(
    notice_id: uuid.UUID,
    channel: Optional[DeliveryChannel] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    from app.services.notice_service import notice_service
    try:
        notice = await notice_service.resend_notice(db, notice_id, channel)
        return notice
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
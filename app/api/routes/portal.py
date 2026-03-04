from fastapi import APIRouter, Depends, HTTPException, status, Header, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import random
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models.all_models import OtpSession, Notice, Case, Meeting, Document, DocSource, AuditLog, ActorType, VictimAccount, PartyType
from  app.core.security.jwt import( create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    get_user_id_from_payload,
    TokenType)
from app.api.deps.auth import oauth2_scheme

router = APIRouter(
    prefix="/portal",
    tags=["Portal"]
)

async def get_current_victim(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = decode_token(token)
    if not payload or payload.get("role") != "victim":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload

class OtpRequest(BaseModel):
    contact: str

class OtpVerify(BaseModel):
    contact: str
    otp: str

@router.post("/{token}/otp/request")
async def request_otp(token: str, req: OtpRequest, db: AsyncSession = Depends(get_db)):
    # Verify the portal token exists in a notice
    notice_res = await db.execute(select(Notice).where(Notice.content.op("->>")("portal_token") == token))
    notice = notice_res.scalars().first()
    if not notice:
        raise HTTPException(status_code=404, detail="Invalid portal link")
        
    # Generate OTP
    otp_code = str(random.randint(100000, 999999))
    
    # Store OTP session
    session_token = str(uuid.uuid4())
    otp_session = OtpSession(
        case_id=notice.case_id,
        victim_contact=req.contact,
        otp_hash=otp_code,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        session_token=session_token
    )
    db.add(otp_session)
    await db.commit()
    
    # Print for debugging since we don't have SMS setup
    print(f"OTP for {req.contact} is {otp_code}")
    
    return {"message": "OTP sent successfully"}


@router.post("/{token}/otp/verify")
async def verify_otp(token: str, req: OtpVerify, db: AsyncSession = Depends(get_db)):
    notice_res = await db.execute(select(Notice).where(Notice.content.op("->>")("portal_token") == token))
    notice = notice_res.scalars().first()
    if not notice:
        raise HTTPException(status_code=404, detail="Invalid portal link")
        
    # Find active OTP session
    otp_res = await db.execute(
        select(OtpSession)
        .where(
            OtpSession.case_id == notice.case_id,
            OtpSession.victim_contact == req.contact,
            OtpSession.expires_at > datetime.utcnow(),
            OtpSession.verified_at == None
        )
        .order_by(OtpSession.created_at.desc())
    )
    otp_session = otp_res.scalars().first()
    
    if not otp_session:
        raise HTTPException(status_code=400, detail="OTP expired or invalid")
        
    if otp_session.attempts >= 3:
        raise HTTPException(status_code=400, detail="Too many failed attempts")
        
    if otp_session.otp_hash != req.otp:
        otp_session.attempts += 1
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    otp_session.verified_at = datetime.utcnow()
    
    # Check if VictimAccount exists, else create
    va_res = await db.execute(select(VictimAccount).where(VictimAccount.case_id == notice.case_id, VictimAccount.phone == req.contact))
    victim_account = va_res.scalars().first()
    if not victim_account:
        victim_account = VictimAccount(case_id=notice.case_id, phone=req.contact)
        db.add(victim_account)
        await db.flush()
        
    # Generate JWT
    access_token = create_access_token(
        data={"sub": str(victim_account.id), "role": "victim", "case_id": str(notice.case_id)},
        expires_delta=timedelta(hours=2)
    )
    
    await db.commit()
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/case")
async def get_portal_case(victim: dict = Depends(get_current_victim), db: AsyncSession = Depends(get_db)):
    case_id = victim.get("case_id")
    case_res = await db.execute(select(Case).where(Case.id == case_id).options(selectinload(Case.parties)))
    case = case_res.scalars().first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    return {
        "id": case.id,
        "case_code": case.case_code,
        "status": case.status,
        "amount_financed": case.amount_financed,
        "claim_amount": case.claim_amount,
        "parties": [p for p in case.parties if p.party_type == PartyType.applicant]
    }

@router.get("/meetings")
async def get_portal_meetings(victim: dict = Depends(get_current_victim), db: AsyncSession = Depends(get_db)):
    case_id = victim.get("case_id")
    meet_res = await db.execute(select(Meeting).where(Meeting.case_id == case_id).order_by(Meeting.scheduled_at.desc()))
    return meet_res.scalars().all()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    victim: dict = Depends(get_current_victim),
    db: AsyncSession = Depends(get_db)
):
    case_id = victim.get("case_id")
    victim_account_id = victim.get("sub")
    
    doc = Document(
        case_id=case_id,
        uploaded_by_victim_id=victim_account_id,
        source=DocSource.victim,
        category=category,
        file_name=file.filename,
        mime_type=file.content_type,
        size_bytes=file.size or 1000,
        storage_key=f"victim_uploads/{uuid.uuid4()}_{file.filename}"
    )
    db.add(doc)
    await db.flush()
    
    audit = AuditLog(
        actor_type=ActorType.victim,
        actor_victim_id=victim_account_id,
        action="DOCUMENT_UPLOADED",
        entity_type="Document",
        entity_id=doc.id,
        after={"file_name": file.filename}
    )
    db.add(audit)
    
    await db.commit()
    return {"message": "File uploaded successfully", "id": doc.id}

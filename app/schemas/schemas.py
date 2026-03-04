from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime, date
from uuid import UUID
from app.db.models.all_models import UserRole, UserStatus, PartyType, NoticeStatus, DeliveryChannel, DeliveryStatus, MeetingStatus, MeetProvider, DocSource, DocCategory, MilestoneType, ImportStatus, ImportRowStatus, ActorType

# --- Auth & Users ---
class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole
    designation: Optional[str] = None
    department: Optional[str] = None
    status: Optional[UserStatus] = UserStatus.active
    employee_id: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# --- Case Core ---
class CaseBase(BaseModel):
    case_code: str
    ref_no: Optional[str] = None
    mode: Optional[str] = None
    agreement_no: Optional[str] = None
    agreement_date: Optional[date] = None
    status: Optional[str] = "NEW"
    assigned_advocate_id: Optional[UUID] = None
    allocated_at: Optional[date] = None
    claim_amount: Optional[float] = None
    claim_date: Optional[date] = None
    amount_financed: Optional[float] = None
    finance_charge: Optional[float] = None
    agreement_value: Optional[float] = None
    award_amount: Optional[float] = None
    award_amount_words: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    engine_no: Optional[str] = None
    chassis_no: Optional[str] = None
    reg_no: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseImportResponse(BaseModel):
    message: str
    total_rows: int
    success_rows: int
    failed_rows: int

class CaseResponse(CaseBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Parties ---
class CasePartyBase(BaseModel):
    case_id: UUID
    party_type: PartyType
    name: str
    father_name: Optional[str] = None
    address: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class CasePartyCreate(CasePartyBase):
    pass

class CasePartyResponse(CasePartyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Notices ---
class NoticeBase(BaseModel):
    case_id: UUID
    notice_no: int
    notice_type: Optional[str] = None
    content: Optional[dict] = None
    status: Optional[NoticeStatus] = NoticeStatus.draft

class NoticeCreate(NoticeBase):
    pass

class NoticeUpdate(BaseModel):
    notice_type: Optional[str] = None
    content: Optional[dict] = None
    status: Optional[NoticeStatus] = None

class NoticeResponse(NoticeBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Meetings ---
class MeetingBase(BaseModel):
    case_id: UUID
    scheduled_at: datetime
    meet_provider: Optional[MeetProvider] = MeetProvider.google_meet
    meet_url: Optional[str] = None
    portal_url: Optional[str] = None
    status: Optional[MeetingStatus] = MeetingStatus.scheduled
    notes: Optional[str] = None

class MeetingCreate(MeetingBase):
    pass

class MeetingUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    meet_provider: Optional[MeetProvider] = None
    meet_url: Optional[str] = None
    portal_url: Optional[str] = None
    status: Optional[MeetingStatus] = None
    notes: Optional[str] = None

class MeetingResponse(MeetingBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Recordings ---
class RecordingBase(BaseModel):
    meeting_id: Optional[UUID] = None
    case_id: UUID
    storage_key: str
    file_name: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    is_downloadable_internal: Optional[bool] = True

class RecordingCreate(RecordingBase):
    pass

class RecordingResponse(RecordingBase):
    id: UUID
    uploaded_by: Optional[UUID] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True

# --- Documents ---
class DocumentBase(BaseModel):
    case_id: UUID
    source: DocSource
    category: Optional[DocCategory] = DocCategory.OTHER
    file_name: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    storage_key: str
    checksum_sha256: Optional[str] = None

class DocumentCreate(DocumentBase):
    uploaded_by_user_id: Optional[UUID] = None
    uploaded_by_victim_id: Optional[UUID] = None

class DocumentResponse(DocumentBase):
    id: UUID
    uploaded_by_user_id: Optional[UUID] = None
    uploaded_by_victim_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Audit Logs ---
class AuditLogBase(BaseModel):
    actor_type: ActorType
    actor_user_id: Optional[UUID] = None
    actor_victim_id: Optional[UUID] = None
    action: str
    entity_type: str
    entity_id: UUID
    before: Optional[dict] = None
    after: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogResponse(AuditLogBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
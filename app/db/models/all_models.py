import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, ForeignKey, Numeric, Text, Enum, BigInteger, JSON
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    case_manager = "case_manager"
    advocate = "advocate"
    staff = "staff"

class UserStatus(str, enum.Enum):
    active = "active"
    locked = "locked"
    disabled = "disabled"

class PartyType(str, enum.Enum):
    applicant = "applicant"
    co_applicant = "co_applicant"
    guarantor = "guarantor"

class NoticeStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    failed = "failed"

class DeliveryChannel(str, enum.Enum):
    sms = "sms"
    whatsapp = "whatsapp"
    email = "email"

class DeliveryStatus(str, enum.Enum):
    queued = "queued"
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"

class MeetingStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"

class MeetProvider(str, enum.Enum):
    google_meet = "google_meet"

class DocSource(str, enum.Enum):
    internal = "internal"
    victim = "victim"

class DocCategory(str, enum.Enum):
    ID_PROOF = "ID_PROOF"
    LOAN_DOC = "LOAN_DOC"
    NOTICE = "NOTICE"
    OTHER = "OTHER"

class MilestoneType(str, enum.Enum):
    FIRST_MEETING = "FIRST_MEETING"
    SECOND_MEETING = "SECOND_MEETING"
    THIRD_MEETING_EXPARTE = "THIRD_MEETING_EXPARTE"
    EVIDENCE_ARGUMENT = "EVIDENCE_ARGUMENT"
    AWARD_DATE = "AWARD_DATE"
    STAMP_PURCHASE_DATE = "STAMP_PURCHASE_DATE"
    
class ImportStatus(str, enum.Enum):
    uploaded = "uploaded"
    validated = "validated"
    imported = "imported"
    failed = "failed"

class ImportRowStatus(str, enum.Enum):
    success = "success"
    failed = "failed"

class ActorType(str, enum.Enum):
    internal = "internal"
    victim = "victim"
    system = "system"

class User(Base):
    __tablename__ = "users"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String, unique=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole, name="user_role",  create_type=False), nullable=False)
    designation = Column(String)
    department = Column(String)
    status = Column(Enum(UserStatus, name="user_status", create_type=False), nullable=False, default=UserStatus.active)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime(timezone=True))

    cases_assigned = relationship("Case", back_populates="assigned_advocate", foreign_keys="[Case.assigned_advocate_id]")
    cases_created = relationship("Case", back_populates="creator", foreign_keys="[Case.created_by]")


class Case(Base):
    __tablename__ = "cases"
  

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_code = Column(String, unique=True, nullable=False)
    ref_no = Column(String, index=True)
    mode = Column(String)
    agreement_no = Column(String, unique=True)
    agreement_date = Column(Date)
    status = Column(String, nullable=False, default="NEW", index=True)
    
    assigned_advocate_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    allocated_at = Column(Date)
    
    zone = Column(String)
    region = Column(String)
    branch_code = Column(String)
    branch_name = Column(String)
    product = Column(String)
    repossession_status = Column(String)
    dpd = Column(String)
    allocation_pos = Column(String)

    claim_amount = Column(Numeric(14, 2))
    claim_date = Column(Date)
    amount_financed = Column(Numeric(14, 2))
    finance_charge = Column(Numeric(14, 2))
    agreement_value = Column(Numeric(14, 2))
    award_amount = Column(Numeric(14, 2))
    award_amount_words = Column(String)

    make = Column(String)
    model = Column(String)
    engine_no = Column(String)
    chassis_no = Column(String)
    reg_no = Column(String)
    
    first_emi_date = Column(Date)
    last_emi_date = Column(Date)
    tenure = Column(Integer)
    sec_17_applied = Column(String)
    sec_17_applied_date = Column(Date)
    sec_17_received_date = Column(Date)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    assigned_advocate = relationship("User", foreign_keys=[assigned_advocate_id], back_populates="cases_assigned")
    creator = relationship("User", foreign_keys=[created_by], back_populates="cases_created")
    parties = relationship("CaseParty", back_populates="case", cascade="all, delete-orphan")
    arbitration = relationship("CaseArbitration", back_populates="case", uselist=False, cascade="all, delete-orphan")
    milestones = relationship("CaseMilestone", back_populates="case", cascade="all, delete-orphan")
    notices = relationship("Notice", back_populates="case", cascade="all, delete-orphan")
    meetings = relationship("Meeting", back_populates="case", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    victim_accounts = relationship("VictimAccount", back_populates="case", cascade="all, delete-orphan")
    rules_state = relationship("CaseRuleState", back_populates="case", uselist=False, cascade="all, delete-orphan")


class CaseParty(Base):
    __tablename__ = "case_parties"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    party_type = Column(Enum(PartyType, name="party_type",  create_type=False), nullable=False)
    name = Column(String, nullable=False)
    father_name = Column(String)
    address = Column(String)
    residence_address_2 = Column(String)
    residence_address_3 = Column(String)
    office_address_1 = Column(String)
    office_address_2 = Column(String)
    office_address_3 = Column(String)
    city = Column(String)
    state = Column(String)
    postal_code = Column(String)
    age = Column(Integer)
    phone = Column(String)
    phone_2 = Column(String)
    email = Column(String)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="parties")

class CaseArbitration(Base):
    __tablename__ = "case_arbitration"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), unique=True, nullable=False)
    institution_name = Column(String)
    arbitrator_name = Column(String)
    arbitrator_phone = Column(String)
    arbitrator_email = Column(String)
    arbitrator_address = Column(String)
    acceptance_date = Column(Date)
    arb_case_no = Column(String)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="arbitration")

class CaseMilestone(Base):
    __tablename__ = "case_milestones"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_type = Column(Enum(MilestoneType, name="milestone_type", create_type=False), nullable=False)
    planned_date = Column(Date)
    actual_date = Column(Date)
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="milestones")

class Notice(Base):
    __tablename__ = "notices"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    notice_no = Column(Integer, nullable=False)
    notice_type = Column(String)
    content = Column(JSONB)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(Enum(NoticeStatus, name="notice_status",create_type=False), nullable=False, default=NoticeStatus.draft)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="notices")
    deliveries = relationship("NoticeDelivery", back_populates="notice", cascade="all, delete-orphan")
    attachments = relationship("NoticeAttachment", back_populates="notice", cascade="all, delete-orphan")

class NoticeDelivery(Base):
    __tablename__ = "notice_deliveries"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notice_id = Column(UUID(as_uuid=True), ForeignKey("notices.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(Enum(DeliveryChannel, name="delivery_channel", create_type=False), nullable=False)
    to_address = Column(String, nullable=False)
    provider_message_id = Column(String)
    status = Column(Enum(DeliveryStatus, name="delivery_status", create_type=False), nullable=False, default=DeliveryStatus.queued)
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    notice = relationship("Notice", back_populates="deliveries")

class CaseRuleState(Base):
    __tablename__ = "case_rules_state"
    # __table_args__ = {"schema": "app"}

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    notice_count = Column(Integer, nullable=False, default=0)
    closure_enabled = Column(Boolean, nullable=False, default=False)
    closure_enabled_at = Column(DateTime(timezone=True))

    case = relationship("Case", back_populates="rules_state")

class Meeting(Base):
    __tablename__ = "meetings"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    meet_provider = Column(Enum(MeetProvider, name="meet_provider",create_type=False), nullable=False, default=MeetProvider.google_meet)
    meet_url = Column(String)
    portal_url = Column(String)
    status = Column(Enum(MeetingStatus, name="meeting_status", create_type=False), nullable=False, default=MeetingStatus.scheduled)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="meetings")

class Recording(Base):
    __tablename__ = "recordings"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="SET NULL"), index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    mime_type = Column(String)
    size_bytes = Column(BigInteger)
    checksum_sha256 = Column(String)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    is_downloadable_internal = Column(Boolean, default=True, nullable=False)

    case = relationship("Case", back_populates="recordings")
    meeting = relationship("Meeting")

class VictimAccount(Base):
    __tablename__ = "victim_accounts"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    phone = Column(String)
    email = Column(String)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    case = relationship("Case", back_populates="victim_accounts")

class Document(Base):
    __tablename__ = "documents"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_by_victim_id = Column(UUID(as_uuid=True), ForeignKey("victim_accounts.id", ondelete="SET NULL"))
    source = Column(Enum(DocSource, name="doc_source", create_type=False), nullable=False)
    category = Column(Enum(DocCategory, name="doc_category",  create_type=False), nullable=False, default=DocCategory.OTHER)
    file_name = Column(String, nullable=False)
    mime_type = Column(String)
    size_bytes = Column(BigInteger)
    storage_key = Column(String, nullable=False)
    checksum_sha256 = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    case = relationship("Case", back_populates="documents")

class DocumentAccessLog(Base):
    __tablename__ = "document_access_logs"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    viewer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = Column(String, nullable=False)
    ip_address = Column(INET)
    user_agent = Column(Text)
    at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class OtpSession(Base):
    __tablename__ = "otp_sessions"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    victim_contact = Column(String, nullable=False)
    otp_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    verified_at = Column(DateTime(timezone=True))
    session_token = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_type = Column(Enum(ActorType, name="actor_type", create_type=False), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    actor_victim_id = Column(UUID(as_uuid=True), ForeignKey("victim_accounts.id", ondelete="SET NULL"))
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    before = Column(JSONB)
    after = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

class CaseImport(Base):
    __tablename__ = "case_imports"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    file_name = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)
    status = Column(Enum(ImportStatus, name="import_status",create_type=False), nullable=False, default=ImportStatus.uploaded)
    total_rows = Column(Integer, nullable=False, default=0)
    success_rows = Column(Integer, nullable=False, default=0)
    failed_rows = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class CaseImportRow(Base):
    __tablename__ = "case_import_rows"
    # __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_id = Column(UUID(as_uuid=True), ForeignKey("case_imports.id", ondelete="CASCADE"), nullable=False, index=True)
    row_no = Column(Integer, nullable=False)
    raw_data = Column(JSONB, nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"))
    status = Column(Enum(ImportRowStatus, name="import_row_status", create_type=False), nullable=False)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class NoticeAttachment(Base):
    __tablename__ = "notice_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notice_id = Column(UUID(as_uuid=True), ForeignKey("notices.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    notice = relationship("Notice", back_populates="attachments")
    document = relationship("Document")
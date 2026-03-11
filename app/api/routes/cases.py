from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import pandas as pd
from io import BytesIO
import math
from datetime import datetime

from app.db.session import get_db
from app.db.models.all_models import Case, User, UserRole,NoticeAttachment,Notice
from app.schemas.schemas import CaseCreate, CaseResponse, CaseImportResponse
from app.api.deps.auth import get_current_user, require_roles

router = APIRouter(prefix="/cases", tags=["cases"])

from sqlalchemy.orm import selectinload

@router.get("/", response_model=List[CaseResponse])
async def list_cases(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(Case)
        .options(
            selectinload(Case.rules_state),
            selectinload(Case.parties),
            selectinload(Case.notices).options(
    selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
    selectinload(Notice.deliveries)
),
            selectinload(Case.milestones),
            selectinload(Case.arbitration),
            selectinload(Case.meetings),
            selectinload(Case.recordings),
            selectinload(Case.documents),
            selectinload(Case.victim_accounts)
        )
        .order_by(Case.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if current_user.role == UserRole.advocate:
        query = query.where(Case.assigned_advocate_id == current_user.id)

    result = await db.execute(query)
    cases = result.scalars().all()
    return cases


def extract_val(val, target_type=str):
    if pd.isna(val):
        return None
    try:
        if target_type == str:
            return str(val).strip()

        elif target_type == float:
            if isinstance(val, str):
                return float(val.replace(",", "").strip())
            return float(val)

        elif target_type == int:
            if isinstance(val, str):
                return int(val.replace(",", "").strip())
            return int(val)

        elif target_type == "date":
            if isinstance(val, str):
                return pd.to_datetime(val).date()

            if isinstance(val, (int, float)) and val > 10000:
                return pd.to_datetime(val, origin="1899-12-30", unit="D").date()

            return val.date() if hasattr(val, "date") else val

    except:
        return None

    return None


@router.post("/import", response_model=CaseImportResponse)
async def import_cases(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):

    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")

    try:
        content = await file.read()
        df = pd.read_excel(BytesIO(content))

        # Normalize headers
        df.columns = (
            df.columns
            .str.strip()
            .str.upper()
            .str.replace(r"\s+", " ", regex=True)
            .str.replace("\n", " ", regex=False)
            .str.replace("\r", "", regex=False)
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")

    success_count = 0
    failed_count = 0
    total_rows = len(df)

    for index, row in df.iterrows():

        try:

            agreement_no = extract_val(row.get("AGREEMENT NO"))

            if not agreement_no:
                failed_count += 1
                continue

            exists = await db.execute(select(Case).where(Case.agreement_no == agreement_no))
            if exists.scalar_one_or_none():
                failed_count += 1
                continue

            case_code = extract_val(row.get("REF. NO.")) or f"CASE-{int(datetime.now().timestamp()*1000)+index}"

            new_case = Case(
                case_code=case_code,
                ref_no=extract_val(row.get("REF. NO.")),
                mode=extract_val(row.get("MODE")),
                agreement_no=agreement_no,
                agreement_date=extract_val(row.get("AGREEMENT DATE"), "date"),
                status="NEW",
                created_by=current_user.id,
                claim_amount=extract_val(row.get("CLAIM AMOUNT"), float),
                claim_date=extract_val(row.get("CLAIM DATE"), "date"),
                amount_financed=extract_val(row.get("AMT FINANCE"), float),
                finance_charge=extract_val(row.get("FINANCE CHARGE"), float),
                agreement_value=extract_val(row.get("AGR VALUE"), float),
                award_amount=extract_val(row.get("AWARD AMOUNT"), float),
                award_amount_words=extract_val(row.get("AWARD AMOUNT IN WORDS")),
                make=extract_val(row.get("MAKE")),
                model=extract_val(row.get("MODEL")),
                engine_no=extract_val(row.get("ENGINE NO.")),
                chassis_no=extract_val(row.get("CHASIS NO.")),
                reg_no=extract_val(row.get("REG. NO")),
                first_emi_date=extract_val(row.get("FIRST EMI DATE"), "date"),
                last_emi_date=extract_val(row.get("LAST EMI DATE"), "date"),
                tenure=extract_val(row.get("TENURE"), int),
                sec_17_applied=extract_val(row.get("SEC 17 ORDER APPLIED(YES/NO)")),
                sec_17_applied_date=extract_val(row.get("SEC 17 ORDER APPLIED DATE"), "date"),
                sec_17_received_date=extract_val(row.get("SEC 17 ORDER RECEIVED DATE"), "date"),
                allocated_at=extract_val(row.get("ALLOCATION DATE"), "date"),
                zone=extract_val(row.get("ZONE")),
                region=extract_val(row.get("REGION")),
                branch_code=extract_val(row.get("BRANCH CODE")),
                branch_name=extract_val(row.get("BRANCH NAME")),
                product=extract_val(row.get("PRODUCT")),
                repossession_status=extract_val(row.get("REPOSSESSION STATUS (YES/NO)")),
                dpd=extract_val(row.get("D.P.D")),
                allocation_pos=extract_val(row.get("ALLOCATION POS")),
            )

            db.add(new_case)
            await db.flush()

            # =====================
            # PARTIES
            # =====================

            from app.db.models.all_models import CaseParty, PartyType

            applicant_name = extract_val(row.get("APPLICANT NAME"))

            if applicant_name:
                db.add(CaseParty(
                    case_id=new_case.id,
                    party_type=PartyType.applicant,
                    name=applicant_name,
                    father_name=extract_val(row.get("APPLICANT FATHER NAME")),
                    address=extract_val(row.get("RESIDENCE ADDRESS 1")),
                    residence_address_2=extract_val(row.get("RESIDENCE ADDRESS 2")),
                    residence_address_3=extract_val(row.get("RESIDENCE ADDRESS 3")),
                    office_address_1=extract_val(row.get("OFFICE ADDRESS 1")),
                    office_address_2=extract_val(row.get("OFFICE ADDRESS 2")),
                    office_address_3=extract_val(row.get("OFFICE ADDRESS 3")),
                    city=extract_val(row.get("CITY")),
                    state=extract_val(row.get("STATE")),
                    postal_code=extract_val(row.get("PIN CODE")),
                    age=extract_val(row.get("APPLICANT AGE"), int),
                    phone=extract_val(row.get("CUSTOMER PHONE 1")),
                    phone_2=extract_val(row.get("CUSTOMER PHONE 2 / EMAIL ID")),
                    email=extract_val(row.get("CUSTOMER PHONE 2 / EMAIL ID"))
                    if "@" in str(row.get("CUSTOMER PHONE 2 / EMAIL ID", "")) else None
                ))

            co_applicant_name = extract_val(row.get("CO-APPLICANT NAME"))

            if co_applicant_name:
                db.add(CaseParty(
                    case_id=new_case.id,
                    party_type=PartyType.co_applicant,
                    name=co_applicant_name,
                    father_name=extract_val(row.get("CO-APPLICANT FATHER NAME")),
                    address=extract_val(row.get("CO-APPLICANT ADDRESS")),
                ))

            guarantor_name = extract_val(row.get("GUARANTOR NAME"))

            if guarantor_name:
                db.add(CaseParty(
                    case_id=new_case.id,
                    party_type=PartyType.guarantor,
                    name=guarantor_name,
                    father_name=extract_val(row.get("GUARANTOR FATHERNAME")),
                    address=extract_val(row.get("GUARANTOR ADDRESS")),
                ))

            # =====================
            # ARBITRATION
            # =====================

            from app.db.models.all_models import CaseArbitration

            inst_name = extract_val(row.get("INSTUTION NAME"))
            arb_name = extract_val(row.get("ARBITRATOR NAME"))

            if inst_name or arb_name:
                db.add(CaseArbitration(
                    case_id=new_case.id,
                    institution_name=inst_name,
                    arbitrator_name=arb_name,
                    arbitrator_phone=extract_val(row.get("ARBITRATOR CONTACT NO.")),
                    arbitrator_email=extract_val(row.get("ARBITRATOR EMAIL ID")),
                    arbitrator_address=extract_val(row.get("ARBITRATOR ADDRESS")),
                    acceptance_date=extract_val(row.get("ACCEPTANCE BY ARBITRATOR (DATE)"), "date"),
                    arb_case_no=extract_val(row.get("ARB CASE NO.")),
                ))

            # =====================
            # MILESTONES
            # =====================

            from app.db.models.all_models import CaseMilestone, MilestoneType

            milestone_map = {
                MilestoneType.FIRST_MEETING: "FIRST MEETING / CLAIM STATEMENT (DATE) (30 DAYS FROM ACCEPTANCE)",
                MilestoneType.SECOND_MEETING: "SECOND MEETING (DATE) (20 DAYS FROM FIRST MEETING)",
                MilestoneType.THIRD_MEETING_EXPARTE: "THIRD MEETING/EX-PARTE NOTICE (DATE) (20 DAYS FROM SECOND MEETING)",
                MilestoneType.EVIDENCE_ARGUMENT: "EVIDENCE / ARGUMENT (DATE) (20 DAYS FROM THIRD MEETING)",
                MilestoneType.AWARD_DATE: "AWARD DATE (20 DAYS FROM EVIDENCE)",
                MilestoneType.STAMP_PURCHASE_DATE: "STAMP PURCHASE DATE (15 DAYS BEFORE AWARD DATE)"
            }

            for m_type, col in milestone_map.items():
                parsed_date = extract_val(row.get(col), "date")

                if parsed_date:
                    db.add(CaseMilestone(
                        case_id=new_case.id,
                        milestone_type=m_type,
                        planned_date=parsed_date,
                        actual_date=parsed_date,
                    ))

            # =====================
            # NOTICES
            # =====================

            from app.db.models.all_models import Notice, NoticeStatus
            from datetime import datetime as dt_module, time, timezone

            notices_to_add = [
                (1, "A", row.get("NOTICE A /DATE OF CN")),
                (2, "B", row.get("NOTICE B /DATE OF RN")),
                (3, "C", row.get("NOTICE - C")),
            ]

            for n_no, n_type, n_date in notices_to_add:

                parsed_date = extract_val(n_date, "date")

                if parsed_date:

                    dt = dt_module.combine(parsed_date, time.min).replace(tzinfo=timezone.utc)

                    db.add(Notice(
                        case_id=new_case.id,
                        notice_no=n_no,
                        notice_type=n_type,
                        status=NoticeStatus.sent,
                        created_at=dt
                    ))

            await db.commit()
            success_count += 1

        except Exception as e:

            await db.rollback()
            failed_count += 1
            print(f"Row {index} failed:", e)

    return CaseImportResponse(
        message="Import completed",
        total_rows=total_rows,
        success_rows=success_count,
        failed_rows=failed_count,
    )

@router.post("/", response_model=CaseResponse)
async def create_case(
    case_in: CaseCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    # Check duplicate case_code
    query = select(Case).where(Case.case_code == case_in.case_code)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Case code already exists")
        
    new_case = Case(**case_in.model_dump(), created_by=current_user.id)
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    
    stmt = (
        select(Case)
        .where(Case.id == new_case.id)
        .options(
            selectinload(Case.rules_state),
            selectinload(Case.parties),
            selectinload(Case.notices).options(
    selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
    selectinload(Notice.deliveries)
),
            selectinload(Case.milestones),
            selectinload(Case.arbitration),
            selectinload(Case.meetings),
            selectinload(Case.recordings),
            selectinload(Case.documents),
            selectinload(Case.victim_accounts)
        )
    )
    result = await db.execute(stmt)
    full_case = result.scalar_one()
    return full_case

from sqlalchemy.orm import selectinload

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: UUID, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.rules_state),
            selectinload(Case.parties),
            selectinload(Case.notices).options(
    selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
    selectinload(Notice.deliveries)
),
            selectinload(Case.milestones),
            selectinload(Case.arbitration),
            selectinload(Case.meetings),
            selectinload(Case.recordings),
            selectinload(Case.documents),
            selectinload(Case.victim_accounts)
        )
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if current_user.role == UserRole.advocate and case.assigned_advocate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this case")
        
    return case

@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: UUID, 
    case_in: CaseCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    query = select(Case).where(Case.id == case_id)
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    for key, value in case_in.model_dump(exclude_unset=True).items():
        setattr(case, key, value)
        
    await db.commit()
    await db.refresh(case)
    
    stmt = (
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.rules_state),
            selectinload(Case.parties),
            selectinload(Case.notices).options(
    selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
    selectinload(Notice.deliveries)
),
            selectinload(Case.milestones),
            selectinload(Case.arbitration),
            selectinload(Case.meetings),
            selectinload(Case.recordings),
            selectinload(Case.documents),
            selectinload(Case.victim_accounts)
        )
    )
    result = await db.execute(stmt)
    full_case = result.scalar_one()
    return full_case

from pydantic import BaseModel
class CaseAssign(BaseModel):
    advocate_id: UUID

@router.put("/{case_id}/assign", response_model=CaseResponse)
async def assign_advocate(
    case_id: UUID,
    payload: CaseAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    query = select(Case).where(Case.id == case_id)
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case.assigned_advocate_id = payload.advocate_id
    
    # Audit log
    from app.db.models.all_models import AuditLog, ActorType
    audit = AuditLog(
        actor_type=ActorType.internal,
        actor_user_id=current_user.id,
        action="ADVOCATE_ASSIGNED",
        entity_type="Case",
        entity_id=case.id,
        after={"assigned_advocate_id": str(payload.advocate_id)}
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(case)
    
    stmt = (
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.rules_state),
            selectinload(Case.parties),
            selectinload(Case.notices).options(
    selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
    selectinload(Notice.deliveries)
),
            selectinload(Case.milestones),
            selectinload(Case.arbitration),
            selectinload(Case.meetings),
            selectinload(Case.recordings),
            selectinload(Case.documents),
            selectinload(Case.victim_accounts)
        )
    )
    result = await db.execute(stmt)
    full_case = result.scalar_one()
    return full_case

@router.post("/{case_id}/close", response_model=CaseResponse)
async def close_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.super_admin, UserRole.case_manager]))
):
    query = select(Case).where(Case.id == case_id).options(
        selectinload(Case.rules_state),
        selectinload(Case.parties),
        selectinload(Case.notices).options(
    selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
    selectinload(Notice.deliveries)
),
        selectinload(Case.milestones),
        selectinload(Case.arbitration),
        selectinload(Case.meetings),
        selectinload(Case.recordings),
        selectinload(Case.documents),
        selectinload(Case.victim_accounts)
    )
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if not case.rules_state or not case.rules_state.closure_enabled:
        raise HTTPException(status_code=400, detail="Case closure is not enabled by rules (needs 3 notices)")
        
    case.status = "CLOSED"
    
    # Audit log
    from models import AuditLog, ActorType
    audit = AuditLog(
        actor_type=ActorType.internal,
        actor_user_id=current_user.id,
        action="CASE_CLOSED",
        entity_type="Case",
        entity_id=case.id,
        after={"status": "CLOSED"}
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(case)
    return case


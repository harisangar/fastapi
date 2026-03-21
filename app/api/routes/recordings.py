from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import uuid
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models.all_models import Recording, User, UserRole, Case, AuditLog, ActorType
from app.schemas.schemas import RecordingCreate, RecordingResponse
from app.api.deps.auth import get_current_user, require_roles
import os

UPLOAD_DIR = "uploads/recordings"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(
    prefix="/recordings",
    tags=["Recordings"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/", response_model=List[RecordingResponse])
async def list_recordings(
    skip: int = 0, limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Recording).options(selectinload(Recording.case)).offset(skip).limit(limit)
    result = await db.execute(query)
    recordings = result.scalars().all()
    
    for r in recordings:
        if r.case:
            setattr(r, 'case_code', r.case.case_code)
            
    return recordings

@router.post("/{case_id}/upload", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED)
async def upload_recording(
    case_id: str,
    file: UploadFile = File(...),
    meeting_id: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ✅ Verify case
    case_res = await db.execute(select(Case).filter(Case.id == case_id))
    if not case_res.scalars().first():
        raise HTTPException(status_code=404, detail="Case not found")

    # ✅ Generate ONE filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    # ✅ Build ONE path
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # ✅ Save file
    file_size = 0
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            buffer.write(chunk)

    # ✅ Store SAME path in DB
    file_path = file_path.replace("\\", "/")
    recording = Recording(
        case_id=case_id,
        meeting_id=meeting_id if meeting_id else None,
        storage_key=file_path,  # 🔥 FIXED (same as saved file)
        file_name=file.filename,
        mime_type=file.content_type,
        size_bytes=file_size,  # 🔥 FIXED (real size)
        uploaded_by=current_user.id
    )

    db.add(recording)
    await db.flush()

    # ✅ Audit log
    audit = AuditLog(
        actor_type=ActorType.internal,
        actor_user_id=current_user.id,
        action="RECORDING_UPLOADED",
        entity_type="Recording",
        entity_id=recording.id,
        after={"file_name": file.filename}
    )
    db.add(audit)

    await db.commit()
    await db.refresh(recording)

    return recording

@router.get("/{recording_id}/download")
async def download_recording(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["super_admin", "case_manager", "advocate"]))
):
    res = await db.execute(select(Recording).filter(Recording.id == recording_id))
    recording = res.scalars().first()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    file_path = f"{recording.storage_key}"  # ✅ actual path

    # ✅ Check file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    # ✅ Stream real file
    def iterfile():
        with open(file_path, "rb") as file:
            while chunk := file.read(1024 * 1024):  # 1MB chunks
                yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{recording.file_name}"'
    }

    return StreamingResponse(
        iterfile(),
        media_type=recording.mime_type or "application/octet-stream",
        headers=headers
    )

@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Recording).options(selectinload(Recording.case)).filter(Recording.id == recording_id))
    recording = result.scalars().first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
        
    if recording.case:
        setattr(recording, 'case_code', recording.case.case_code)
        
    return recording

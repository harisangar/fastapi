from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from app.db.session import get_db
from app.db.models.all_models import Document, User, UserRole
from app.schemas.schemas import DocumentCreate, DocumentResponse
from app.api.deps.auth import get_current_user, require_roles

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0, limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Document).options(selectinload(Document.case)).offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()
    
    for doc in documents:
        if doc.case:
            setattr(doc, 'case_code', doc.case.case_code)
            
    return documents

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_in: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = Document(**document_in.model_dump())
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Document).options(selectinload(Document.case)).filter(Document.id == document_id))
    document = result.scalars().first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.case:
        setattr(document, 'case_code', document.case.case_code)
        
    return document

from fastapi import UploadFile, File, Form
from fastapi.responses import StreamingResponse
import uuid

@router.post("/{case_id}/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_internal_document(
    case_id: str,
    file: UploadFile = File(...),
    category: str = Form("OTHER"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["super_admin", "case_manager", "advocate", "staff"]))
):
    from app.db.models.all_models import Case, DocSource, AuditLog, ActorType
    # Verify case
    case_res = await db.execute(select(Case).filter(Case.id == case_id))
    if not case_res.scalars().first():
        raise HTTPException(status_code=404, detail="Case not found")

    document = Document(
        case_id=case_id,
        uploaded_by_user_id=current_user.id,
        source="internal",
        category=category,
        file_name=file.filename,
        mime_type=file.content_type,
        size_bytes=file.size or 100000,
        storage_key=f"internal_docs/{uuid.uuid4()}_{file.filename}"
    )
    db.add(document)
    await db.flush()

    audit = AuditLog(
        actor_type="internal",
        actor_user_id=current_user.id,
        action="DOCUMENT_UPLOADED",
        entity_type="Document",
        entity_id=document.id,
        after={"file_name": file.filename, "source": "internal"}
    )
    db.add(audit)

    await db.commit()
    await db.refresh(document)
    return document

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["super_admin", "case_manager", "advocate", "staff"]))
):
    res = await db.execute(select(Document).filter(Document.id == document_id))
    document = res.scalars().first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Mock streaming the file
    def iterfile():
        yield b"mock document content for " + document.file_name.encode()

    headers = {
        "Content-Disposition": f'attachment; filename="{document.file_name}"'
    }
    return StreamingResponse(iterfile(), media_type=document.mime_type or "application/octet-stream", headers=headers)


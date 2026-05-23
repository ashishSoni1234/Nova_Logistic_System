from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import logging
import PyPDF2

from database import get_db
from models.document import Document, DocumentStatus
from models.user import User
from routers.auth import get_current_user
from agents.document_extractor import run_document_extractor
from agents.validator import run_validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".txt"}


async def process_document_bg(doc_id: int, file_path: str, db_url: str):
    """Background task: extract and validate document."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return

        doc.status = DocumentStatus.PROCESSING
        db.commit()

        raw_text = ""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            try:
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    raw_text = "\n".join(page.extract_text() or "" for page in reader.pages[:10])
            except Exception as e:
                logger.warning(f"PDF text extraction failed: {e}")

        doc.raw_text = raw_text[:10000]
        db.commit()

        extracted = await run_document_extractor(file_path, raw_text)
        doc.extracted_data = extracted
        doc.status = DocumentStatus.EXTRACTED
        db.commit()

        if extracted.get("status") != "failed":
            validation = await run_validator(extracted)
            doc.validation_result = validation
            doc.status = DocumentStatus.VALIDATED
            db.commit()

    except Exception as e:
        logger.error(f"Background processing failed for doc {doc_id}: {e}")
        if doc:
            doc.status = DocumentStatus.FAILED
            db.commit()
    finally:
        db.close()


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")

        safe_name = f"{current_user.id}_{os.urandom(4).hex()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)

        doc = Document(
            filename=file.filename,
            file_path=file_path,
            file_type=ext.lstrip("."),
            file_size=file_size,
            status=DocumentStatus.UPLOADED,
            tenant_id=current_user.tenant_id,
            uploaded_by=current_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        from config import settings
        background_tasks.add_task(process_document_bg, doc.id, file_path, settings.database_url)

        return {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "message": "Document uploaded and processing started",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@router.get("")
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(Document).filter(Document.tenant_id == current_user.tenant_id)
        if status:
            query = query.filter(Document.status == status)
        total = query.count()
        docs = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "items": [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "file_type": d.file_type,
                    "file_size": d.file_size,
                    "status": d.status,
                    "created_at": d.created_at,
                    "has_extracted_data": d.extracted_data is not None,
                }
                for d in docs
            ],
        }
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "extracted_data": doc.extracted_data,
        "validation_result": doc.validation_result,
        "raw_text": (doc.raw_text or "")[:500],
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


@router.post("/{doc_id}/reprocess")
async def reprocess_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = DocumentStatus.UPLOADED
    doc.extracted_data = None
    doc.validation_result = None
    db.commit()

    from config import settings
    background_tasks.add_task(process_document_bg, doc.id, doc.file_path, settings.database_url)
    return {"message": "Reprocessing started", "doc_id": doc_id}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception:
        pass

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}

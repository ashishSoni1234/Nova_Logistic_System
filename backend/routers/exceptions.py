from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from database import get_db
from models.exception_model import Exception as ExceptionModel, Severity
from models.user import User
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])


class ExceptionCreate(BaseModel):
    exception_type: str = "general"
    reason: str
    severity: str = "medium"
    details: Optional[str] = None
    workflow_run_id: Optional[int] = None
    document_id: Optional[int] = None


@router.get("")
async def list_exceptions(
    skip: int = 0,
    limit: int = 20,
    resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(ExceptionModel)
        if resolved is not None:
            query = query.filter(ExceptionModel.resolved == resolved)
        if severity:
            query = query.filter(ExceptionModel.severity == severity)

        total = query.count()
        exceptions = query.order_by(ExceptionModel.created_at.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "items": [
                {
                    "id": e.id,
                    "exception_type": e.exception_type,
                    "reason": e.reason,
                    "severity": e.severity,
                    "resolved": e.resolved,
                    "details": e.details,
                    "created_at": e.created_at,
                    "resolved_at": e.resolved_at,
                    "workflow_run_id": e.workflow_run_id,
                }
                for e in exceptions
            ],
        }
    except Exception as e:
        logger.error(f"List exceptions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list exceptions")


@router.get("/stats")
async def exception_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.query(ExceptionModel).count()
    unresolved = db.query(ExceptionModel).filter(ExceptionModel.resolved == False).count()
    critical = db.query(ExceptionModel).filter(
        ExceptionModel.severity == Severity.CRITICAL,
        ExceptionModel.resolved == False,
    ).count()
    high = db.query(ExceptionModel).filter(
        ExceptionModel.severity == Severity.HIGH,
        ExceptionModel.resolved == False,
    ).count()
    return {
        "total": total,
        "unresolved": unresolved,
        "critical": critical,
        "high": high,
    }


@router.post("")
async def create_exception(
    payload: ExceptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        exc = ExceptionModel(
            exception_type=payload.exception_type,
            reason=payload.reason,
            severity=Severity(payload.severity),
            details=payload.details,
            workflow_run_id=payload.workflow_run_id,
            document_id=payload.document_id,
        )
        db.add(exc)
        db.commit()
        db.refresh(exc)
        return {"id": exc.id, "status": "created"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{exc_id}/resolve")
async def resolve_exception(
    exc_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exc_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    exc.resolved = True
    exc.resolved_by = current_user.id
    exc.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Exception resolved", "exc_id": exc_id}


@router.get("/{exc_id}")
async def get_exception(
    exc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exc_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    return {
        "id": exc.id,
        "exception_type": exc.exception_type,
        "reason": exc.reason,
        "severity": exc.severity,
        "resolved": exc.resolved,
        "details": exc.details,
        "created_at": exc.created_at,
        "resolved_at": exc.resolved_at,
    }

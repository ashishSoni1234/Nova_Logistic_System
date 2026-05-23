from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from database import get_db
from models.approval import Approval, ApprovalStatus
from models.user import User, UserRole
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class ApprovalAction(BaseModel):
    action: str
    comment: Optional[str] = ""


@router.get("")
async def list_approvals(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(Approval)

        if current_user.role in [UserRole.ADMIN]:
            pass
        elif current_user.role == UserRole.MANAGER:
            query = query.filter(
                (Approval.assigned_to == current_user.id) |
                (Approval.assigned_role.in_(["Manager", "manager"]))
            )
        else:
            query = query.filter(Approval.assigned_to == current_user.id)

        if status:
            query = query.filter(Approval.status == status)

        total = query.count()
        approvals = query.order_by(Approval.created_at.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "items": [
                {
                    "id": a.id,
                    "title": a.title,
                    "description": a.description,
                    "assigned_role": a.assigned_role,
                    "status": a.status,
                    "amount": a.amount,
                    "comment": a.comment,
                    "created_at": a.created_at,
                    "resolved_at": a.resolved_at,
                    "workflow_run_id": a.workflow_run_id,
                }
                for a in approvals
            ],
        }
    except Exception as e:
        logger.error(f"List approvals error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list approvals")


@router.get("/pending-count")
async def pending_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(Approval).filter(Approval.status == ApprovalStatus.PENDING).count()
    return {"pending": count}


@router.get("/{approval_id}")
async def get_approval(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {
        "id": approval.id,
        "title": approval.title,
        "description": approval.description,
        "assigned_role": approval.assigned_role,
        "status": approval.status,
        "amount": approval.amount,
        "comment": approval.comment,
        "created_at": approval.created_at,
        "resolved_at": approval.resolved_at,
        "workflow_run_id": approval.workflow_run_id,
    }


@router.post("/{approval_id}/action")
async def process_approval(
    approval_id: int,
    payload: ApprovalAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")

    action = payload.action.lower()
    if action not in ["approve", "reject", "escalate"]:
        raise HTTPException(status_code=400, detail="Action must be approve, reject, or escalate")

    status_map = {
        "approve": ApprovalStatus.APPROVED,
        "reject": ApprovalStatus.REJECTED,
        "escalate": ApprovalStatus.ESCALATED,
    }

    approval.status = status_map[action]
    approval.comment = payload.comment
    approval.assigned_to = current_user.id
    approval.resolved_at = datetime.utcnow()
    db.commit()

    return {
        "message": f"Approval {action}d successfully",
        "approval_id": approval_id,
        "new_status": approval.status,
    }


@router.post("/create")
async def create_approval(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        approval = Approval(
            title=payload.get("title", "Manual Approval"),
            description=payload.get("description", ""),
            assigned_role=payload.get("assigned_role", "Manager"),
            amount=str(payload.get("amount", "")),
            workflow_run_id=payload.get("workflow_run_id"),
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        return {"id": approval.id, "status": approval.status}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

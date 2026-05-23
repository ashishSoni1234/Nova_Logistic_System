from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
import logging

from database import get_db
from models.user import User
from models.workflow import Workflow, WorkflowRun, RunStatus
from models.document import Document, DocumentStatus
from models.approval import Approval, ApprovalStatus
from models.exception_model import Exception as ExceptionModel, Severity
from models.supply_chain import SupplyChainData
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        total_workflows = db.query(Workflow).filter(
            Workflow.tenant_id == current_user.tenant_id
        ).count()

        total_documents = db.query(Document).filter(
            Document.tenant_id == current_user.tenant_id
        ).count()

        pending_approvals = db.query(Approval).filter(
            Approval.status == ApprovalStatus.PENDING
        ).count()

        open_exceptions = db.query(ExceptionModel).filter(
            ExceptionModel.resolved == False
        ).count()

        today = datetime.utcnow().date()
        exceptions_today = db.query(ExceptionModel).filter(
            func.date(ExceptionModel.created_at) == today
        ).count()

        active_runs = db.query(WorkflowRun).filter(
            WorkflowRun.status == RunStatus.RUNNING
        ).count()

        total_sc_records = db.query(SupplyChainData).count()

        return {
            "total_workflows": total_workflows,
            "total_documents": total_documents,
            "pending_approvals": pending_approvals,
            "open_exceptions": open_exceptions,
            "exceptions_today": exceptions_today,
            "active_runs": active_runs,
            "total_supply_chain_records": total_sc_records,
        }
    except Exception as e:
        logger.error(f"Dashboard summary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard summary")


@router.get("/shipments-over-time")
async def shipments_over_time(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rows = db.query(
            SupplyChainData.order_date,
            func.count(SupplyChainData.id).label("count"),
            func.sum(SupplyChainData.sales).label("total_sales"),
        ).group_by(
            SupplyChainData.order_date
        ).order_by(
            SupplyChainData.order_date
        ).limit(days).all()

        return {
            "data": [
                {
                    "date": r.order_date,
                    "shipments": r.count,
                    "sales": round(float(r.total_sales or 0), 2),
                }
                for r in rows
            ]
        }
    except Exception as e:
        logger.error(f"Shipments over time error: {e}")
        return {"data": []}


@router.get("/approval-status")
async def approval_status_chart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        statuses = [ApprovalStatus.PENDING, ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.ESCALATED]
        data = []
        for s in statuses:
            count = db.query(Approval).filter(Approval.status == s).count()
            data.append({"status": s.value, "count": count})
        return {"data": data}
    except Exception as e:
        logger.error(f"Approval status error: {e}")
        return {"data": []}


@router.get("/exception-trend")
async def exception_trend(
    days: int = 14,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        rows = db.query(
            func.date(ExceptionModel.created_at).label("date"),
            func.count(ExceptionModel.id).label("count"),
        ).filter(
            ExceptionModel.created_at >= start_date
        ).group_by(
            func.date(ExceptionModel.created_at)
        ).order_by(
            func.date(ExceptionModel.created_at)
        ).all()

        result = []
        for i in range(days):
            day = (start_date + timedelta(days=i)).date()
            count = next((r.count for r in rows if r.date == day), 0)
            result.append({"date": str(day), "exceptions": count})

        return {"data": result}
    except Exception as e:
        logger.error(f"Exception trend error: {e}")
        return {"data": []}


@router.get("/category-breakdown")
async def category_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rows = db.query(
            SupplyChainData.category,
            func.count(SupplyChainData.id).label("count"),
            func.sum(SupplyChainData.sales).label("sales"),
        ).filter(
            SupplyChainData.category != None,
            SupplyChainData.category != "",
        ).group_by(
            SupplyChainData.category
        ).order_by(
            func.count(SupplyChainData.id).desc()
        ).limit(10).all()

        return {
            "data": [
                {
                    "category": r.category or "Unknown",
                    "count": r.count,
                    "sales": round(float(r.sales or 0), 2),
                }
                for r in rows
            ]
        }
    except Exception as e:
        logger.error(f"Category breakdown error: {e}")
        return {"data": []}


@router.get("/recent-activity")
async def recent_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        recent_runs = db.query(WorkflowRun).order_by(
            WorkflowRun.started_at.desc()
        ).limit(5).all()

        recent_docs = db.query(Document).filter(
            Document.tenant_id == current_user.tenant_id
        ).order_by(Document.created_at.desc()).limit(5).all()

        recent_exceptions = db.query(ExceptionModel).order_by(
            ExceptionModel.created_at.desc()
        ).limit(5).all()

        return {
            "recent_runs": [
                {
                    "id": r.id,
                    "workflow_id": r.workflow_id,
                    "status": r.status,
                    "started_at": r.started_at,
                }
                for r in recent_runs
            ],
            "recent_documents": [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "status": d.status,
                    "created_at": d.created_at,
                }
                for d in recent_docs
            ],
            "recent_exceptions": [
                {
                    "id": e.id,
                    "exception_type": e.exception_type,
                    "severity": e.severity,
                    "reason": e.reason[:100],
                    "created_at": e.created_at,
                }
                for e in recent_exceptions
            ],
        }
    except Exception as e:
        logger.error(f"Recent activity error: {e}")
        return {"recent_runs": [], "recent_documents": [], "recent_exceptions": []}

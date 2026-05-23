from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging
import json

from database import get_db
from models.workflow import Workflow, WorkflowRun, WorkflowStatus, RunStatus
from models.user import User
from routers.auth import get_current_user
from workflow_engine.validator import validate_workflow
from workflow_engine.parser import parse_workflow_yaml
from workflow_engine.executor import execute_workflow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    yaml_config: str


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    yaml_config: Optional[str] = None
    status: Optional[str] = None


class WorkflowRunRequest(BaseModel):
    input_data: Optional[dict] = {}


@router.post("")
async def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        validation = validate_workflow(payload.yaml_config)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail={"errors": validation["errors"]})

        wf = Workflow(
            name=payload.name,
            description=payload.description,
            yaml_config=payload.yaml_config,
            tenant_id=current_user.tenant_id,
            created_by=current_user.id,
        )
        db.add(wf)
        db.commit()
        db.refresh(wf)
        return {
            "id": wf.id,
            "name": wf.name,
            "status": wf.status,
            "warnings": validation.get("warnings", []),
            "created_at": wf.created_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create workflow error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create workflow")


@router.get("")
async def list_workflows(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(Workflow).filter(Workflow.tenant_id == current_user.tenant_id)
        total = query.count()
        wfs = query.order_by(Workflow.created_at.desc()).offset(skip).limit(limit).all()
        return {
            "total": total,
            "items": [
                {
                    "id": w.id,
                    "name": w.name,
                    "description": w.description,
                    "status": w.status,
                    "created_at": w.created_at,
                    "run_count": len(w.runs),
                    "yaml_config": w.yaml_config,
                }
                for w in wfs
            ],
        }
    except Exception as e:
        logger.error(f"List workflows error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list workflows")


@router.get("/{wf_id}")
async def get_workflow(
    wf_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wf = db.query(Workflow).filter(
        Workflow.id == wf_id,
        Workflow.tenant_id == current_user.tenant_id,
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "yaml_config": wf.yaml_config,
        "status": wf.status,
        "created_at": wf.created_at,
        "updated_at": wf.updated_at,
    }


@router.put("/{wf_id}")
async def update_workflow(
    wf_id: int,
    payload: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wf = db.query(Workflow).filter(
        Workflow.id == wf_id,
        Workflow.tenant_id == current_user.tenant_id,
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if payload.yaml_config:
        validation = validate_workflow(payload.yaml_config)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail={"errors": validation["errors"]})
        wf.yaml_config = payload.yaml_config

    if payload.name:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description
    if payload.status:
        wf.status = payload.status

    db.commit()
    return {"message": "Workflow updated", "id": wf.id}


@router.delete("/{wf_id}")
async def delete_workflow(
    wf_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wf = db.query(Workflow).filter(
        Workflow.id == wf_id,
        Workflow.tenant_id == current_user.tenant_id,
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(wf)
    db.commit()
    return {"message": "Workflow deleted"}


@router.post("/{wf_id}/run")
async def run_workflow(
    wf_id: int,
    payload: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wf = db.query(Workflow).filter(
        Workflow.id == wf_id,
        Workflow.tenant_id == current_user.tenant_id,
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    run = WorkflowRun(
        workflow_id=wf.id,
        status=RunStatus.PENDING,
        input_data=json.dumps(payload.input_data),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    async def run_bg():
        from database import SessionLocal
        bg_db = SessionLocal()
        try:
            await execute_workflow(run.id, wf.yaml_config, payload.input_data or {}, bg_db)
        except Exception as e:
            logger.error(f"Workflow run {run.id} failed: {e}")
        finally:
            bg_db.close()

    background_tasks.add_task(run_bg)
    return {"run_id": run.id, "status": "started", "message": "Workflow execution started"}


@router.get("/{wf_id}/runs")
async def list_runs(
    wf_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wf = db.query(Workflow).filter(
        Workflow.id == wf_id,
        Workflow.tenant_id == current_user.tenant_id,
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    runs = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == wf_id).order_by(
        WorkflowRun.started_at.desc()
    ).limit(20).all()

    return {
        "items": [
            {
                "id": r.id,
                "status": r.status,
                "current_step": r.current_step,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "error_message": r.error_message,
            }
            for r in runs
        ]
    }


@router.post("/validate")
async def validate_yaml(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    yaml_content = payload.get("yaml_config", "")
    return validate_workflow(yaml_content)

"""Execute workflow step-by-step."""
import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session

from workflow_engine.parser import parse_workflow_yaml, get_start_step, get_step_by_id
from agents.document_extractor import run_document_extractor
from agents.validator import run_validator
from agents.exception_detector import run_exception_detector
from agents.workflow_router import run_workflow_router
from models.workflow import WorkflowRun, RunStatus
from models.approval import Approval, ApprovalStatus
from models.exception_model import Exception as ExceptionModel, Severity

logger = logging.getLogger(__name__)

MAX_STEPS = 20


async def execute_workflow(
    workflow_run_id: int,
    yaml_config: str,
    input_data: dict,
    db: Session,
) -> dict:
    """Execute a workflow from start to end, step by step."""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
    if not run:
        raise ValueError(f"WorkflowRun {workflow_run_id} not found")

    try:
        workflow = parse_workflow_yaml(yaml_config)
    except Exception as e:
        run.status = RunStatus.FAILED
        run.error_message = str(e)
        db.commit()
        return {"status": "failed", "error": str(e)}

    current_step_id = get_start_step(workflow)
    run.status = RunStatus.RUNNING
    run.current_step = current_step_id
    db.commit()

    context = dict(input_data)
    step_count = 0
    execution_log = []

    while current_step_id and step_count < MAX_STEPS:
        step = get_step_by_id(workflow, current_step_id)
        if not step:
            break

        step_count += 1
        step_type = step.get("type", "")
        logger.info(f"Executing step: {current_step_id} (type={step_type})")

        run.current_step = current_step_id
        db.commit()

        log_entry = {
            "step": current_step_id,
            "type": step_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if step_type == "start":
            next_step = step.get("next")
            log_entry["result"] = "started"
            current_step_id = next_step

        elif step_type == "end":
            log_entry["result"] = "completed"
            current_step_id = None

        elif step_type == "ai_agent":
            agent_name = step.get("agent", "")
            try:
                if agent_name == "document_extractor":
                    file_path = context.get("file_path", "")
                    agent_result = await run_document_extractor(file_path)
                    context.update(agent_result)
                    next_key = "on_success" if agent_result.get("status") == "success" else "on_failure"

                elif agent_name == "validator":
                    agent_result = await run_validator(context)
                    context["validation"] = agent_result
                    next_key = "on_success" if agent_result.get("validation_status") == "MATCH" else "on_failure"

                elif agent_name == "exception_detector":
                    agent_result = await run_exception_detector(context)
                    context["exception"] = agent_result
                    if agent_result.get("status") in ["SUSPICIOUS", "EXCEPTION"]:
                        exc = ExceptionModel(
                            workflow_run_id=workflow_run_id,
                            exception_type=agent_result.get("exception_type", "general"),
                            reason=agent_result.get("reason", "Detected by agent"),
                            severity=Severity(agent_result.get("severity", "medium")),
                            details=json.dumps(agent_result),
                        )
                        db.add(exc)
                        db.commit()
                    next_key = "on_success" if agent_result.get("status") == "NORMAL" else "on_failure"

                else:
                    agent_result = {"status": "success", "note": f"Unknown agent: {agent_name}"}
                    next_key = "on_success"

                log_entry["agent"] = agent_name
                log_entry["result"] = agent_result
                current_step_id = step.get(next_key, step.get("next"))

            except Exception as e:
                log_entry["error"] = str(e)
                current_step_id = step.get("on_failure", step.get("next"))
                logger.error(f"Agent {agent_name} failed: {e}")

        elif step_type == "condition":
            router_result = await run_workflow_router(context, workflow, current_step_id)
            next_step = router_result.get("next_step")
            log_entry["decision"] = router_result
            current_step_id = next_step

        elif step_type == "approval":
            assigned_role = step.get("assigned_role", "Manager")
            approval = Approval(
                workflow_run_id=workflow_run_id,
                title=f"Approval required: {step.get('id', 'step')}",
                description=f"Workflow approval step: {current_step_id}",
                assigned_role=assigned_role,
                status=ApprovalStatus.PENDING,
                amount=str(context.get("total_amount", context.get("amount", ""))),
            )
            db.add(approval)
            db.commit()

            run.status = RunStatus.PAUSED
            run.current_step = current_step_id
            db.commit()

            log_entry["result"] = "awaiting_approval"
            log_entry["assigned_role"] = assigned_role
            execution_log.append(log_entry)
            return {
                "status": "paused",
                "current_step": current_step_id,
                "reason": "awaiting_approval",
                "execution_log": execution_log,
            }

        else:
            current_step_id = step.get("next")
            log_entry["result"] = "passed"

        execution_log.append(log_entry)

    run.status = RunStatus.COMPLETED
    run.completed_at = datetime.utcnow()
    run.output_data = json.dumps(context)
    db.commit()

    return {
        "status": "completed",
        "steps_executed": step_count,
        "execution_log": execution_log,
        "output": context,
    }

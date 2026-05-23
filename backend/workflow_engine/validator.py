"""Validate YAML workflow structure before execution."""
import logging
from workflow_engine.parser import parse_workflow_yaml

logger = logging.getLogger(__name__)

REQUIRED_STEP_FIELDS = {"id", "type"}
VALID_STEP_TYPES = {"start", "end", "ai_agent", "approval", "condition", "notification"}


def validate_workflow(yaml_content: str) -> dict:
    """
    Validate a workflow YAML string.
    Returns {"valid": bool, "errors": list, "warnings": list}
    """
    errors = []
    warnings = []

    try:
        workflow = parse_workflow_yaml(yaml_content)
    except ValueError as e:
        return {"valid": False, "errors": [str(e)], "warnings": []}

    if not workflow.get("name"):
        errors.append("Workflow must have a 'name' field")

    steps = workflow.get("steps", [])
    if not steps:
        errors.append("Workflow must have at least one step")
        return {"valid": False, "errors": errors, "warnings": warnings}

    step_ids = set()
    has_start = False
    has_end = False

    for i, step in enumerate(steps):
        step_id = step.get("id", f"step_{i}")

        for field in REQUIRED_STEP_FIELDS:
            if field not in step:
                errors.append(f"Step '{step_id}': missing required field '{field}'")

        if step_id in step_ids:
            errors.append(f"Duplicate step ID: '{step_id}'")
        step_ids.add(step_id)

        step_type = step.get("type", "")
        if step_type not in VALID_STEP_TYPES:
            errors.append(f"Step '{step_id}': unknown type '{step_type}'. Valid: {VALID_STEP_TYPES}")

        if step_type == "start":
            has_start = True
            if not step.get("next"):
                warnings.append(f"Start step '{step_id}' has no 'next' defined")

        if step_type == "end":
            has_end = True

        if step_type == "ai_agent" and not step.get("agent"):
            errors.append(f"Step '{step_id}': ai_agent type requires 'agent' field")

        if step_type == "approval" and not step.get("assigned_role"):
            warnings.append(f"Step '{step_id}': approval step has no 'assigned_role'")

        if step_type == "condition":
            rules = step.get("rules", [])
            if not rules:
                warnings.append(f"Condition step '{step_id}' has no rules defined")

    if not has_start:
        warnings.append("No step with type 'start' found")
    if not has_end:
        warnings.append("No step with type 'end' found")

    next_refs = set()
    for step in steps:
        if step.get("next"):
            next_refs.add(step["next"])
        for rule in step.get("rules", []):
            if rule.get("next"):
                next_refs.add(rule["next"])
        for key in ["on_success", "on_failure"]:
            if step.get(key):
                next_refs.add(step[key])

    for ref in next_refs:
        if ref not in step_ids:
            warnings.append(f"Step reference '{ref}' not found in step IDs")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "step_count": len(steps),
    }

"""Parse YAML workflow definitions into Python dicts."""
import yaml
import json
import logging
from typing import Union

logger = logging.getLogger(__name__)

VALID_STEP_TYPES = {"start", "end", "ai_agent", "approval", "condition", "notification"}
VALID_AGENTS = {"document_extractor", "validator", "exception_detector", "workflow_router"}


def parse_workflow_yaml(yaml_content: str) -> dict:
    """Parse YAML string into validated workflow dict."""
    try:
        data = yaml.safe_load(yaml_content)
        if not data or "workflow" not in data:
            raise ValueError("YAML must have a top-level 'workflow' key")
        return data["workflow"]
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")


def workflow_to_yaml(workflow_dict: dict) -> str:
    """Convert workflow dict to YAML string."""
    return yaml.dump({"workflow": workflow_dict}, default_flow_style=False, allow_unicode=True)


def workflow_to_json(workflow_dict: dict) -> str:
    """Convert workflow dict to JSON string."""
    return json.dumps(workflow_dict, indent=2)


def extract_step_ids(workflow_dict: dict) -> list[str]:
    """Get all step IDs in order."""
    return [step["id"] for step in workflow_dict.get("steps", [])]


def get_start_step(workflow_dict: dict) -> str:
    """Find the start step ID."""
    for step in workflow_dict.get("steps", []):
        if step.get("type") == "start":
            return step.get("next") or step.get("id")
    steps = workflow_dict.get("steps", [])
    return steps[0]["id"] if steps else ""


def get_step_by_id(workflow_dict: dict, step_id: str) -> dict:
    """Find a step by its ID."""
    for step in workflow_dict.get("steps", []):
        if step.get("id") == step_id:
            return step
    return {}

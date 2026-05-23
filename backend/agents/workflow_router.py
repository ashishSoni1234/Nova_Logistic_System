"""Workflow Router Agent — evaluates conditions and routes workflow steps."""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Any
import logging
import json

from rag.pipeline import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class RouterState(TypedDict):
    task_type: str
    input_data: dict
    workflow_config: dict
    current_step: str
    retrieved_context: list
    schema: str
    llm_output: str
    final_result: dict
    error: Optional[str]


def resolve_scope(state: RouterState) -> RouterState:
    state["task_type"] = "workflow_routing"
    return state


def compile_context(state: RouterState) -> RouterState:
    return state


def route_schema(state: RouterState) -> RouterState:
    state["schema"] = "workflow_routing"
    return state


async def plan_and_execute(state: RouterState) -> RouterState:
    if state.get("error"):
        return state
    try:
        input_data = state["input_data"]
        workflow = state.get("workflow_config", {})
        current_step_id = state.get("current_step", "")

        steps = {s["id"]: s for s in workflow.get("steps", [])}
        current = steps.get(current_step_id, {})

        if current.get("type") == "condition":
            rules = current.get("rules", [])
            amount = float(input_data.get("amount", input_data.get("total_amount", 0)))

            next_step = None
            for rule in rules:
                condition = rule.get("if", "")
                try:
                    local_vars = {"amount": amount, **input_data}
                    if eval(condition, {"__builtins__": {}}, local_vars):
                        next_step = rule.get("next")
                        break
                except Exception:
                    continue

            state["final_result"] = {
                "decision": "route",
                "next_step": next_step or current.get("default", "complete"),
                "reason": f"Condition evaluation for amount={amount}",
                "current_step": current_step_id,
            }

        elif current.get("type") == "ai_agent":
            agent_name = current.get("agent", "")
            state["final_result"] = {
                "decision": "execute_agent",
                "agent": agent_name,
                "next_step_on_success": current.get("on_success", current.get("next")),
                "next_step_on_failure": current.get("on_failure", "flag_exception"),
                "current_step": current_step_id,
            }

        elif current.get("type") == "approval":
            state["final_result"] = {
                "decision": "await_approval",
                "assigned_role": current.get("assigned_role", "Manager"),
                "next_step": current.get("next", "complete"),
                "current_step": current_step_id,
            }

        elif current.get("type") == "end":
            state["final_result"] = {
                "decision": "complete",
                "next_step": None,
                "current_step": current_step_id,
            }

        else:
            next_step = current.get("next", "complete")
            state["final_result"] = {
                "decision": "advance",
                "next_step": next_step,
                "current_step": current_step_id,
            }

    except Exception as e:
        state["error"] = f"Routing failed: {str(e)}"
        logger.error(f"Workflow router error: {e}")
    return state


def deliver_evidence(state: RouterState) -> RouterState:
    if state.get("error"):
        state["final_result"] = {
            "decision": "error",
            "reason": state["error"],
            "next_step": None,
        }
    return state


def build_router_graph():
    graph = StateGraph(RouterState)
    graph.add_node("resolve_scope", resolve_scope)
    graph.add_node("compile_context", compile_context)
    graph.add_node("route_schema", route_schema)
    graph.add_node("plan_and_execute", plan_and_execute)
    graph.add_node("deliver_evidence", deliver_evidence)

    graph.set_entry_point("resolve_scope")
    graph.add_edge("resolve_scope", "compile_context")
    graph.add_edge("compile_context", "route_schema")
    graph.add_edge("route_schema", "plan_and_execute")
    graph.add_edge("plan_and_execute", "deliver_evidence")
    graph.add_edge("deliver_evidence", END)

    return graph.compile()


router_graph = build_router_graph()


async def run_workflow_router(
    input_data: dict,
    workflow_config: dict,
    current_step: str,
) -> dict:
    """Entry point for workflow routing agent."""
    initial_state: RouterState = {
        "task_type": "workflow_routing",
        "input_data": input_data,
        "workflow_config": workflow_config,
        "current_step": current_step,
        "retrieved_context": [],
        "schema": "workflow_routing",
        "llm_output": "",
        "final_result": {},
        "error": None,
    }
    try:
        result = await router_graph.ainvoke(initial_state)
        return result["final_result"]
    except Exception as e:
        logger.error(f"Router graph error: {e}")
        return {"decision": "error", "reason": str(e), "next_step": None}

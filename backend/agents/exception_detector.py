"""Exception Detection Agent — LangGraph + RAG + Groq."""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import logging
import json

from rag.retriever import retrieve_multi_collection, format_context_for_prompt
from rag.pipeline import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class DetectorState(TypedDict):
    task_type: str
    input_data: dict
    retrieved_context: list
    schema: str
    llm_output: str
    final_result: dict
    error: Optional[str]


def resolve_scope(state: DetectorState) -> DetectorState:
    input_data = state["input_data"]
    if "amount" in input_data or "transaction" in str(input_data):
        state["task_type"] = "fraud_detection"
    elif "late_delivery" in str(input_data) or "shipment" in str(input_data):
        state["task_type"] = "delivery_exception"
    else:
        state["task_type"] = "general_exception"
    return state


def compile_context(state: DetectorState) -> DetectorState:
    if state.get("error"):
        return state
    try:
        input_data = state["input_data"]
        amount = input_data.get("amount", input_data.get("total_amount", 0))
        query = f"transaction amount {amount} anomaly fraud pattern detection suspicious"

        contexts = retrieve_multi_collection(
            query,
            collection_keys=["fraud_patterns", "business_rules"],
            n_results=5,
        )
        state["retrieved_context"] = contexts
    except Exception as e:
        logger.warning(f"Exception detection context retrieval failed: {e}")
        state["retrieved_context"] = []
    return state


def route_schema(state: DetectorState) -> DetectorState:
    state["schema"] = "exception_detection"
    return state


async def plan_and_execute(state: DetectorState) -> DetectorState:
    if state.get("error"):
        return state
    try:
        input_data = state["input_data"]
        context_text = format_context_for_prompt(state.get("retrieved_context", []))
        task_type = state.get("task_type", "general_exception")

        prompt = f"""You are a logistics exception and fraud detection AI expert.
Task type: {task_type}

RETRIEVED FRAUD PATTERNS AND RULES:
{context_text}

TRANSACTION/DOCUMENT DATA TO ANALYZE:
{json.dumps(input_data, indent=2)}

Analyze this data for anomalies, fraud patterns, or exceptions. Consider:
1. Is the amount unusual compared to known patterns?
2. Are there timing anomalies?
3. Does it match any fraud patterns from the context?
4. Are there supply chain exceptions (late delivery, missing data)?

Respond ONLY with valid JSON:
{{
  "status": "NORMAL" | "SUSPICIOUS" | "EXCEPTION",
  "severity": "low" | "medium" | "high" | "critical",
  "confidence": 0.0-1.0,
  "exception_type": "fraud" | "delivery_delay" | "data_anomaly" | "policy_violation" | "none",
  "flags": ["list of specific issues found"],
  "reason": "detailed explanation",
  "recommended_action": "what should be done next"
}}"""

        llm = get_llm()
        messages = [
            SystemMessage(content="You are a fraud and exception detection AI. Respond with valid JSON only."),
            HumanMessage(content=prompt),
        ]
        response = llm.invoke(messages)
        content = response.content.strip()

        if "```" in content:
            parts = content.split("```")
            content = parts[1] if len(parts) > 1 else content
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content.strip())
        state["final_result"] = result
        state["llm_output"] = json.dumps(result)
    except json.JSONDecodeError:
        state["final_result"] = {
            "status": "EXCEPTION",
            "severity": "medium",
            "confidence": 0.0,
            "exception_type": "data_anomaly",
            "flags": ["Failed to parse detection response"],
            "reason": "Detection response could not be parsed",
            "recommended_action": "Manual review required",
        }
    except Exception as e:
        state["error"] = f"Detection failed: {str(e)}"
        logger.error(f"Exception detector error: {e}")
    return state


def deliver_evidence(state: DetectorState) -> DetectorState:
    if state.get("error"):
        state["final_result"] = {
            "status": "EXCEPTION",
            "severity": "medium",
            "confidence": 0.0,
            "exception_type": "data_anomaly",
            "flags": [state["error"]],
            "reason": state["error"],
            "recommended_action": "Manual review required",
        }
    return state


def build_detector_graph():
    graph = StateGraph(DetectorState)
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


detector_graph = build_detector_graph()


async def run_exception_detector(transaction_data: dict) -> dict:
    """Entry point for exception detection agent."""
    initial_state: DetectorState = {
        "task_type": "general_exception",
        "input_data": transaction_data,
        "retrieved_context": [],
        "schema": "exception_detection",
        "llm_output": "",
        "final_result": {},
        "error": None,
    }
    try:
        result = await detector_graph.ainvoke(initial_state)
        return result["final_result"]
    except Exception as e:
        logger.error(f"Detector graph error: {e}")
        return {
            "status": "EXCEPTION",
            "severity": "medium",
            "confidence": 0.0,
            "exception_type": "data_anomaly",
            "reason": str(e),
            "recommended_action": "Manual review required",
        }

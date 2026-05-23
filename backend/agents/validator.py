"""Validation Agent — LangGraph + RAG + Groq."""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import logging
import json

from rag.retriever import retrieve_multi_collection, format_context_for_prompt
from rag.pipeline import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class ValidatorState(TypedDict):
    task_type: str
    input_data: dict
    retrieved_context: list
    schema: str
    llm_output: str
    final_result: dict
    error: Optional[str]


def resolve_scope(state: ValidatorState) -> ValidatorState:
    state["task_type"] = "invoice_validation"
    return state


def compile_context(state: ValidatorState) -> ValidatorState:
    if state.get("error"):
        return state
    try:
        extracted = state["input_data"].get("extracted_data", {})
        vendor = extracted.get("vendor_name", "")
        amount = extracted.get("total_amount", 0)
        query = f"invoice validation vendor {vendor} amount {amount} purchase order matching rules"

        contexts = retrieve_multi_collection(
            query,
            collection_keys=["invoices", "business_rules"],
            n_results=4,
        )
        state["retrieved_context"] = contexts
    except Exception as e:
        logger.warning(f"Validation context retrieval failed: {e}")
        state["retrieved_context"] = []
    return state


def route_schema(state: ValidatorState) -> ValidatorState:
    state["schema"] = "invoice_validation"
    return state


async def plan_and_execute(state: ValidatorState) -> ValidatorState:
    if state.get("error"):
        return state
    try:
        extracted = state["input_data"].get("extracted_data", {})
        context_text = format_context_for_prompt(state.get("retrieved_context", []))

        prompt = f"""You are a logistics invoice validation expert.

RETRIEVED BUSINESS RULES AND CONTEXT:
{context_text}

EXTRACTED INVOICE DATA:
{json.dumps(extracted, indent=2)}

Validate this invoice against the business rules. Check:
1. Are all required fields present? (invoice_number, vendor_name, amount, date)
2. Does the amount seem reasonable based on context?
3. Are there any anomalies or missing data?
4. Does it match standard invoice format rules?

Respond ONLY with valid JSON:
{{
  "validation_status": "MATCH" | "MISMATCH" | "INCOMPLETE",
  "confidence": 0.0-1.0,
  "passed_checks": ["list of checks that passed"],
  "failed_checks": ["list of checks that failed"],
  "warnings": ["any warnings or concerns"],
  "reason": "brief overall assessment",
  "requires_manual_review": true | false
}}"""

        llm = get_llm()
        messages = [
            SystemMessage(content="You are an invoice validation AI. Always respond with valid JSON only."),
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
            "validation_status": "MISMATCH",
            "confidence": 0.0,
            "passed_checks": [],
            "failed_checks": ["Failed to parse validation response"],
            "warnings": [],
            "reason": "Validation response could not be parsed",
            "requires_manual_review": True,
        }
    except Exception as e:
        state["error"] = f"Validation failed: {str(e)}"
        logger.error(f"Validator error: {e}")
    return state


def deliver_evidence(state: ValidatorState) -> ValidatorState:
    if state.get("error"):
        state["final_result"] = {
            "validation_status": "MISMATCH",
            "confidence": 0.0,
            "passed_checks": [],
            "failed_checks": [state["error"]],
            "warnings": [],
            "reason": state["error"],
            "requires_manual_review": True,
        }
    return state


def build_validator_graph():
    graph = StateGraph(ValidatorState)
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


validator_graph = build_validator_graph()


async def run_validator(extracted_data: dict) -> dict:
    """Entry point for validation agent."""
    initial_state: ValidatorState = {
        "task_type": "invoice_validation",
        "input_data": {"extracted_data": extracted_data},
        "retrieved_context": [],
        "schema": "invoice_validation",
        "llm_output": "",
        "final_result": {},
        "error": None,
    }
    try:
        result = await validator_graph.ainvoke(initial_state)
        return result["final_result"]
    except Exception as e:
        logger.error(f"Validator graph error: {e}")
        return {
            "validation_status": "MISMATCH",
            "confidence": 0.0,
            "reason": str(e),
            "requires_manual_review": True,
        }

"""Document Extraction Agent — LangGraph + Groq Llama 3.1."""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import PyPDF2
import logging
import json
import os

from rag.pipeline import extract_structured_data, get_llm
from rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class ExtractorState(TypedDict):
    task_type: str
    input_data: dict
    raw_text: str
    retrieved_context: list
    schema: str
    llm_output: str
    final_result: dict
    error: Optional[str]


# ─── Stage 1: Scope Resolution ─────────────────────────────────────────────────

def resolve_scope(state: ExtractorState) -> ExtractorState:
    """Determine what type of document we're processing."""
    try:
        file_path = state["input_data"].get("file_path", "")
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            state["task_type"] = "pdf_extraction"
            state["schema"] = "invoice"
        elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
            state["task_type"] = "image_extraction"
            state["schema"] = "invoice"
        else:
            state["task_type"] = "text_extraction"
            state["schema"] = "generic"

        logger.info(f"Scope resolved: {state['task_type']}")
    except Exception as e:
        state["error"] = f"Scope resolution failed: {str(e)}"
    return state


# ─── Stage 2: Context Compilation ──────────────────────────────────────────────

def compile_context(state: ExtractorState) -> ExtractorState:
    """Retrieve similar invoice templates from ChromaDB."""
    if state.get("error"):
        return state
    try:
        sample_text = state.get("raw_text", "")[:500] or "invoice extraction"
        contexts = retrieve_context(
            query=f"invoice template {sample_text}",
            collection_key="invoices",
            n_results=3,
        )
        state["retrieved_context"] = contexts
        logger.info(f"Retrieved {len(contexts)} context chunks")
    except Exception as e:
        logger.warning(f"Context retrieval failed (non-fatal): {e}")
        state["retrieved_context"] = []
    return state


# ─── Stage 3: Schema Routing ────────────────────────────────────────────────────

def route_schema(state: ExtractorState) -> ExtractorState:
    """Select extraction schema based on document type."""
    if state.get("error"):
        return state

    schemas = {
        "invoice": {
            "invoice_number": "string — unique invoice identifier",
            "vendor_name": "string — name of the vendor/supplier",
            "vendor_address": "string — vendor address",
            "invoice_date": "string — date of invoice (YYYY-MM-DD format)",
            "due_date": "string — payment due date",
            "total_amount": "number — total invoice amount",
            "tax_amount": "number — tax/GST amount",
            "subtotal": "number — subtotal before tax",
            "currency": "string — currency code (USD, EUR, etc.)",
            "items": "array of {description, quantity, unit_price, total}",
            "payment_terms": "string — payment terms",
        },
        "generic": {
            "title": "string — document title",
            "date": "string — document date",
            "content_summary": "string — brief summary of content",
            "key_fields": "object — any key-value pairs found",
        },
    }

    state["schema"] = json.dumps(schemas.get(state["schema"], schemas["generic"]), indent=2)
    return state


# ─── Stage 4: Plan + Execute ────────────────────────────────────────────────────

def extract_text_from_file(file_path: str) -> str:
    """Extract raw text from PDF or return placeholder for images."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        try:
            text_parts = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages[:10]:
                    text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return ""
    elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
        return state_get_text_from_image(file_path)
    return ""


def state_get_text_from_image(file_path: str) -> str:
    """Placeholder for image text extraction (OCR not included, use text provided)."""
    return f"[Image file: {os.path.basename(file_path)} — text extraction requires OCR]"


async def plan_and_execute(state: ExtractorState) -> ExtractorState:
    """Use Groq Llama 3.1 to extract structured data from the document text."""
    if state.get("error"):
        return state
    try:
        raw_text = state.get("raw_text", "")
        if not raw_text:
            file_path = state["input_data"].get("file_path", "")
            if os.path.exists(file_path):
                raw_text = extract_text_from_file(file_path)
                state["raw_text"] = raw_text

        if not raw_text:
            state["error"] = "No text content found in document"
            return state

        context_snippets = "\n".join(
            ctx["text"][:200] for ctx in state.get("retrieved_context", [])[:2]
        )

        schema_desc = f"Extract these fields as JSON: {state['schema']}"
        example = json.dumps({
            "invoice_number": "INV-001",
            "vendor_name": "ABC Corp",
            "total_amount": 1500.00,
            "invoice_date": "2024-01-15",
            "items": [{"description": "Service A", "quantity": 1, "unit_price": 1500.00, "total": 1500.00}],
        }, indent=2)

        enhanced_text = raw_text
        if context_snippets:
            enhanced_text = f"Document text:\n{raw_text}\n\nSimilar invoice context:\n{context_snippets}"

        result = await extract_structured_data(enhanced_text, schema_desc, example)
        state["llm_output"] = json.dumps(result)
        state["final_result"] = result
        logger.info("Document extraction completed successfully")
    except Exception as e:
        state["error"] = f"Extraction failed: {str(e)}"
        logger.error(f"Extraction error: {e}")
    return state


# ─── Stage 5: Evidence Delivery ─────────────────────────────────────────────────

def deliver_evidence(state: ExtractorState) -> ExtractorState:
    """Package final result with metadata."""
    if state.get("error"):
        state["final_result"] = {
            "error": state["error"],
            "status": "failed",
            "extracted_fields": {},
        }
    else:
        result = state.get("final_result", {})
        if "error" not in result:
            result["status"] = "success"
            result["fields_extracted"] = len([k for k, v in result.items() if v and k not in ["status", "fields_extracted"]])
        state["final_result"] = result

    return state


# ─── Build LangGraph ────────────────────────────────────────────────────────────

def build_extractor_graph():
    graph = StateGraph(ExtractorState)

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


extractor_graph = build_extractor_graph()


async def run_document_extractor(file_path: str, raw_text: str = "") -> dict:
    """Entry point for document extraction agent."""
    initial_state: ExtractorState = {
        "task_type": "unknown",
        "input_data": {"file_path": file_path},
        "raw_text": raw_text,
        "retrieved_context": [],
        "schema": "invoice",
        "llm_output": "",
        "final_result": {},
        "error": None,
    }

    try:
        result = await extractor_graph.ainvoke(initial_state)
        return result["final_result"]
    except Exception as e:
        logger.error(f"Extractor graph error: {e}")
        return {"error": str(e), "status": "failed"}

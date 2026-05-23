from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from routers.auth import get_current_user
from models.user import User
from agents.document_extractor import run_document_extractor
from agents.validator import run_validator
from agents.exception_detector import run_exception_detector
from rag.pipeline import rag_query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])


class ExtractRequest(BaseModel):
    file_path: str
    raw_text: Optional[str] = ""


class ValidateRequest(BaseModel):
    extracted_data: dict


class DetectRequest(BaseModel):
    transaction_data: dict


class RAGQueryRequest(BaseModel):
    query: str
    collections: Optional[list] = ["supply_chain", "business_rules"]
    n_results: Optional[int] = 5


@router.post("/extract")
async def extract_document(
    payload: ExtractRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = await run_document_extractor(payload.file_path, payload.raw_text)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Extract agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_document(
    payload: ValidateRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = await run_validator(payload.extracted_data)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Validate agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-exception")
async def detect_exception(
    payload: DetectRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = await run_exception_detector(payload.transaction_data)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Exception detector error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag-query")
async def query_rag(
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = await rag_query(
            query=payload.query,
            collection_keys=payload.collections,
            n_results=payload.n_results,
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def agents_status(current_user: User = Depends(get_current_user)):
    from rag.vectorstore import get_collection_count, COLLECTIONS
    statuses = {}
    for key, col_name in COLLECTIONS.items():
        try:
            count = get_collection_count(col_name)
            statuses[key] = {"collection": col_name, "documents": count, "ready": count > 0}
        except Exception:
            statuses[key] = {"collection": col_name, "documents": 0, "ready": False}

    return {
        "agents": {
            "document_extractor": "ready",
            "validator": "ready",
            "exception_detector": "ready",
            "workflow_router": "ready",
        },
        "rag_collections": statuses,
    }

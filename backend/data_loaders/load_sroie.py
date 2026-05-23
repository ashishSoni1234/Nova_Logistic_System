"""Load SROIE receipt/invoice data into ChromaDB for RAG."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from pathlib import Path
from rag.embedder import embed_texts
from rag.vectorstore import upsert_documents, COLLECTIONS
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 10


def extract_text_from_sroie(json_path: Path) -> str:
    """Extract text content from a SROIE JSON annotation file."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            parts = []
            for key, value in data.items():
                if isinstance(value, str):
                    parts.append(f"{key}: {value}")
                elif isinstance(value, list):
                    parts.append(f"{key}: {', '.join(str(v) for v in value)}")
            return " | ".join(parts)

        return str(data)[:1000]
    except Exception as e:
        logger.warning(f"Could not parse {json_path}: {e}")
        return ""


def load_sroie_split(split_dir: Path, split_name: str) -> int:
    """Load one split (train/test) of SROIE into ChromaDB."""
    collection_name = COLLECTIONS["invoices"]
    texts, ids, metadatas = [], [], []
    doc_count = 0

    json_files = list(split_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files in {split_name}")

    for i in range(0, len(json_files), BATCH_SIZE):
        batch_files = json_files[i: i + BATCH_SIZE]

        for jf in batch_files:
            text = extract_text_from_sroie(jf)
            if not text:
                continue

            doc_id = f"sroie_{split_name}_{jf.stem}"
            texts.append(text[:1000])
            ids.append(doc_id)
            metadatas.append({
                "source": "sroie",
                "split": split_name,
                "filename": jf.stem,
                "type": "invoice",
            })
            doc_count += 1

        if texts:
            embeddings = embed_texts(texts)
            upsert_documents(collection_name, ids, texts, embeddings, metadatas)
            logger.info(f"  Embedded batch {i // BATCH_SIZE + 1}: {len(texts)} invoices")
            texts, ids, metadatas = [], [], []

    if texts:
        embeddings = embed_texts(texts)
        upsert_documents(collection_name, ids, texts, embeddings, metadatas)

    return doc_count


def embed_business_rules():
    """Embed standard business rules into ChromaDB for validation."""
    rules = [
        {
            "id": "rule_001",
            "text": "Invoice validation rule: Invoice amount must match purchase order amount within 5% tolerance. Vendor name must be on approved vendor list.",
            "type": "validation",
        },
        {
            "id": "rule_002",
            "text": "Approval routing rule: Invoices above $50,000 require CFO approval. Invoices between $10,000 and $50,000 require Manager approval. Below $10,000 requires Operator approval.",
            "type": "approval_routing",
        },
        {
            "id": "rule_003",
            "text": "Exception rule: Late delivery risk score above 0.7 triggers automatic exception. Discount rate above 30% requires manager review.",
            "type": "exception",
        },
        {
            "id": "rule_004",
            "text": "Fraud detection rule: Transactions with amount above $5,000 and unusual time patterns are flagged as suspicious. Duplicate invoice numbers within 30 days are rejected.",
            "type": "fraud",
        },
        {
            "id": "rule_005",
            "text": "Supply chain rule: Orders with late delivery risk > 0.5 should be escalated to logistics manager. Missing shipment dates within 48 hours trigger automated follow-up.",
            "type": "supply_chain",
        },
        {
            "id": "rule_006",
            "text": "Vendor policy: New vendors require 3-way match (PO, receipt, invoice). Existing approved vendors require 2-way match. All vendors must have valid tax ID.",
            "type": "vendor",
        },
        {
            "id": "rule_007",
            "text": "Payment terms: Net-30 is standard payment term. Early payment discount of 2% available for payment within 10 days. Late payment incurs 1.5% monthly interest.",
            "type": "payment",
        },
        {
            "id": "rule_008",
            "text": "Document requirements: All invoices must contain vendor name, invoice number, date, itemized charges, and total amount. Missing fields trigger extraction failure exception.",
            "type": "document",
        },
    ]

    collection_name = COLLECTIONS["business_rules"]
    texts = [r["text"] for r in rules]
    ids = [r["id"] for r in rules]
    metadatas = [{"source": "business_rules", "type": r["type"]} for r in rules]

    embeddings = embed_texts(texts)
    upsert_documents(collection_name, ids, texts, embeddings, metadatas)
    logger.info(f"Embedded {len(rules)} business rules into ChromaDB")


def main():
    sroie_base = Path(settings.dataset_path) / "sorie"
    total = 0

    for split in ["train", "test"]:
        split_dir = sroie_base / split
        if split_dir.exists():
            count = load_sroie_split(split_dir, split)
            total += count
            logger.info(f"  {split}: {count} invoices loaded")
        else:
            logger.warning(f"SROIE {split} directory not found: {split_dir}")

    embed_business_rules()
    logger.info(f"SROIE load complete: {total} invoice documents embedded")


if __name__ == "__main__":
    main()

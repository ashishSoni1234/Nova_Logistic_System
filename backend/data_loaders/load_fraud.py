"""Load fraud/anomaly patterns from creditcard.csv into ChromaDB."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import logging
from rag.embedder import embed_texts
from rag.vectorstore import upsert_documents, COLLECTIONS
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
MAX_FRAUD_FOR_CHROMA = 3000


def load_fraud_patterns(csv_path: str) -> int:
    """Load fraud pattern descriptions into ChromaDB."""
    logger.info(f"Loading fraud patterns from: {csv_path}")
    collection_name = COLLECTIONS["fraud_patterns"]

    texts, ids, metadatas = [], [], []
    fraud_count = 0
    normal_count = 0
    total_embedded = 0

    for chunk in pd.read_csv(csv_path, chunksize=CHUNK_SIZE):
        for idx, row in chunk.iterrows():
            is_fraud = int(row.get("Class", 0)) == 1
            amount = float(row.get("Amount", 0))
            time_val = float(row.get("Time", 0))

            if is_fraud and fraud_count >= MAX_FRAUD_FOR_CHROMA // 2:
                continue
            if not is_fraud and normal_count >= MAX_FRAUD_FOR_CHROMA // 2:
                continue

            v_features = [f"V{i}={row.get(f'V{i}', 0):.3f}" for i in range(1, 6)]
            feature_summary = ", ".join(v_features)

            label = "FRAUDULENT" if is_fraud else "NORMAL"
            text = (
                f"Transaction {label}: Amount=${amount:.2f} | "
                f"Time={time_val:.0f}s | "
                f"Key features: {feature_summary} | "
                f"Pattern type: {'suspicious high-value anomaly' if is_fraud and amount > 100 else 'normal transaction pattern'}"
            )

            doc_id = f"fraud_{idx}"
            texts.append(text)
            ids.append(doc_id)
            metadatas.append({
                "source": "creditcard",
                "label": label,
                "amount": str(amount),
                "is_fraud": str(is_fraud),
            })

            if is_fraud:
                fraud_count += 1
            else:
                normal_count += 1

            if len(texts) >= 200:
                embeddings = embed_texts(texts)
                upsert_documents(collection_name, ids, texts, embeddings, metadatas)
                total_embedded += len(texts)
                logger.info(f"  Embedded batch: fraud={fraud_count}, normal={normal_count}, total={total_embedded}")
                texts, ids, metadatas = [], [], []

            if fraud_count + normal_count >= MAX_FRAUD_FOR_CHROMA:
                break

        if fraud_count + normal_count >= MAX_FRAUD_FOR_CHROMA:
            break

    if texts:
        embeddings = embed_texts(texts)
        upsert_documents(collection_name, ids, texts, embeddings, metadatas)
        total_embedded += len(texts)

    logger.info(f"Fraud patterns loaded: {fraud_count} fraud + {normal_count} normal = {total_embedded} total")
    return total_embedded


def main():
    csv_path = os.path.join(settings.dataset_path, "Fraud", "creditcard.csv")
    if not os.path.exists(csv_path):
        logger.error(f"Fraud dataset not found: {csv_path}")
        return

    total = load_fraud_patterns(csv_path)
    logger.info(f"Fraud dataset load complete: {total} patterns in ChromaDB")


if __name__ == "__main__":
    main()

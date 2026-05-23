"""Load DataCo Supply Chain CSV into PostgreSQL + ChromaDB (chunked, RAM-safe)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import logging
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models.supply_chain import SupplyChainData
from rag.embedder import embed_texts
from rag.vectorstore import upsert_documents, COLLECTIONS
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
MAX_ROWS_FOR_CHROMA = 5000


def load_to_postgres(csv_path: str):
    """Load CSV into PostgreSQL using chunked reads."""
    logger.info(f"Loading DataCo CSV to PostgreSQL: {csv_path}")
    Base.metadata.create_all(bind=engine)

    total_loaded = 0
    for chunk_num, chunk in enumerate(pd.read_csv(csv_path, chunksize=CHUNK_SIZE, encoding="latin1", low_memory=False)):
        chunk.columns = [c.strip() for c in chunk.columns]

        records = []
        for _, row in chunk.iterrows():
            record = SupplyChainData(
                order_id=str(row.get("Order Id", row.get("Order ID", "")))[:100],
                order_date=str(row.get("order date (DateOrders)", row.get("Order Date", "")))[:50],
                ship_date=str(row.get("shipping date (DateOrders)", row.get("Ship Date", "")))[:50],
                customer_name=str(row.get("Customer Full Name", row.get("Customer Name", "")))[:255],
                customer_segment=str(row.get("Customer Segment", ""))[:100],
                product_name=str(row.get("Product Name", ""))[:500],
                category=str(row.get("Category Name", row.get("Category", "")))[:100],
                department=str(row.get("Department Name", row.get("Department", "")))[:100],
                market=str(row.get("Market", ""))[:100],
                region=str(row.get("Order Region", row.get("Region", "")))[:100],
                country=str(row.get("Order Country", row.get("Country", "")))[:100],
                order_status=str(row.get("Order Status", ""))[:50],
                shipping_mode=str(row.get("Shipping Mode", ""))[:100],
                sales=float(row["Sales"]) if pd.notna(row.get("Sales")) else None,
                order_quantity=int(row["Order Item Quantity"]) if pd.notna(row.get("Order Item Quantity")) else None,
                profit=float(row["Order Profit Per Order"]) if pd.notna(row.get("Order Profit Per Order")) else None,
                discount=float(row["Order Item Discount Rate"]) if pd.notna(row.get("Order Item Discount Rate")) else None,
                late_delivery_risk=int(row["Late_delivery_risk"]) if pd.notna(row.get("Late_delivery_risk")) else None,
            )
            records.append(record)

        db: Session = SessionLocal()
        try:
            db.bulk_save_objects(records)
            db.commit()
            total_loaded += len(records)
            logger.info(f"  Chunk {chunk_num + 1}: {len(records)} rows → PostgreSQL (total: {total_loaded})")
        except Exception as e:
            db.rollback()
            logger.error(f"  Chunk {chunk_num + 1} failed: {e}")
        finally:
            db.close()

    logger.info(f"PostgreSQL load complete: {total_loaded} rows")
    return total_loaded


def load_to_chromadb(csv_path: str):
    """Embed a sample of DataCo rows and store in ChromaDB."""
    logger.info(f"Embedding DataCo sample into ChromaDB...")
    collection_name = COLLECTIONS["supply_chain"]

    texts = []
    ids = []
    metadatas = []
    row_count = 0

    for chunk in pd.read_csv(csv_path, chunksize=500, encoding="latin1", low_memory=False):
        chunk.columns = [c.strip() for c in chunk.columns]

        for _, row in chunk.iterrows():
            if row_count >= MAX_ROWS_FOR_CHROMA:
                break

            text = (
                f"Order {row.get('Order Id', '')} | "
                f"Product: {row.get('Product Name', '')} | "
                f"Category: {row.get('Category Name', '')} | "
                f"Market: {row.get('Market', '')} | "
                f"Region: {row.get('Order Region', '')} | "
                f"Status: {row.get('Order Status', '')} | "
                f"Sales: ${row.get('Sales', 0):.2f} | "
                f"Profit: ${row.get('Order Profit Per Order', 0):.2f} | "
                f"Late Delivery Risk: {row.get('Late_delivery_risk', 0)}"
            )
            texts.append(text[:1000])
            ids.append(f"dataco_{row_count}")
            metadatas.append({
                "source": "dataco",
                "order_id": str(row.get("Order Id", ""))[:50],
                "category": str(row.get("Category Name", ""))[:50],
                "market": str(row.get("Market", ""))[:50],
            })
            row_count += 1

        if row_count >= MAX_ROWS_FOR_CHROMA:
            break

        if texts:
            embeddings = embed_texts(texts)
            upsert_documents(collection_name, ids, texts, embeddings, metadatas)
            logger.info(f"  Embedded batch of {len(texts)} (total: {row_count})")
            texts, ids, metadatas = [], [], []

    if texts:
        embeddings = embed_texts(texts)
        upsert_documents(collection_name, ids, texts, embeddings, metadatas)

    logger.info(f"ChromaDB load complete: {row_count} rows embedded")
    return row_count


def main():
    csv_path = os.path.join(settings.dataset_path, "Dataco", "DataCoSupplyChainDataset.csv")
    if not os.path.exists(csv_path):
        logger.error(f"Dataset not found: {csv_path}")
        return

    pg_rows = load_to_postgres(csv_path)
    chroma_rows = load_to_chromadb(csv_path)
    logger.info(f"DataCo load complete. PG: {pg_rows} rows, ChromaDB: {chroma_rows} rows")


if __name__ == "__main__":
    main()

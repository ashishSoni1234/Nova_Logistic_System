import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
import logging
import os

logger = logging.getLogger(__name__)

_client = None
_collections = {}


def get_chroma_client() -> chromadb.PersistentClient:
    """Singleton ChromaDB client — persists to disk."""
    global _client
    if _client is None:
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB client initialized at: {settings.chroma_persist_dir}")
    return _client


def get_collection(name: str):
    """Get or create a named ChromaDB collection."""
    global _collections
    if name not in _collections:
        client = get_chroma_client()
        _collections[name] = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB collection ready: {name}")
    return _collections[name]


def upsert_documents(
    collection_name: str,
    ids: list[str],
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict] = None,
):
    """Upsert documents into a ChromaDB collection."""
    if not texts:
        return
    collection = get_collection(collection_name)
    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas or [{} for _ in texts],
    )
    logger.info(f"Upserted {len(texts)} documents into '{collection_name}'")


def query_collection(
    collection_name: str,
    query_embedding: list[float],
    n_results: int = 5,
    where: dict = None,
) -> dict:
    """Query a collection by embedding vector."""
    collection = get_collection(collection_name)
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    results = collection.query(**kwargs)
    return results


def get_collection_count(collection_name: str) -> int:
    """Return number of documents in a collection."""
    try:
        collection = get_collection(collection_name)
        return collection.count()
    except Exception:
        return 0


COLLECTIONS = {
    "supply_chain": "nova_supply_chain",
    "invoices": "nova_invoices",
    "fraud_patterns": "nova_fraud_patterns",
    "business_rules": "nova_business_rules",
}

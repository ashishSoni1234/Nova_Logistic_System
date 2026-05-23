from sentence_transformers import SentenceTransformer
from config import settings
import logging
import threading

logger = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


def get_embedding_model() -> SentenceTransformer:
    """Singleton pattern — load model once, reuse across requests."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                logger.info(f"Loading embedding model: {settings.embedding_model}")
                _model = SentenceTransformer(settings.embedding_model)
                logger.info("Embedding model loaded successfully")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of text strings. Returns list of float vectors."""
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    return embeddings.tolist()


def embed_single(text: str) -> list[float]:
    """Embed a single text string."""
    model = get_embedding_model()
    embedding = model.encode([text], show_progress_bar=False)
    return embedding[0].tolist()

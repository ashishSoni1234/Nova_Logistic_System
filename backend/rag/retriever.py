from rag.embedder import embed_single
from rag.vectorstore import query_collection, COLLECTIONS
import logging

logger = logging.getLogger(__name__)


def retrieve_context(
    query: str,
    collection_key: str = "supply_chain",
    n_results: int = 5,
    where: dict = None,
) -> list[dict]:
    """
    Retrieve relevant context chunks from ChromaDB for a query.
    Returns list of {text, metadata, score} dicts.
    """
    try:
        collection_name = COLLECTIONS.get(collection_key, collection_key)
        query_embedding = embed_single(query)
        results = query_collection(
            collection_name=collection_name,
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )

        contexts = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            contexts.append({
                "text": doc,
                "metadata": meta,
                "score": round(1 - dist, 4),
            })

        return contexts
    except Exception as e:
        logger.error(f"Retrieval error for query '{query[:50]}': {e}")
        return []


def retrieve_multi_collection(
    query: str,
    collection_keys: list[str],
    n_results: int = 3,
) -> list[dict]:
    """Retrieve from multiple collections and merge results."""
    all_contexts = []
    for key in collection_keys:
        try:
            contexts = retrieve_context(query, collection_key=key, n_results=n_results)
            for ctx in contexts:
                ctx["source"] = key
            all_contexts.extend(contexts)
        except Exception as e:
            logger.warning(f"Failed to retrieve from collection '{key}': {e}")

    all_contexts.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_contexts[:n_results * 2]


def format_context_for_prompt(contexts: list[dict]) -> str:
    """Format retrieved contexts into a prompt-friendly string."""
    if not contexts:
        return "No relevant context found."

    lines = []
    for i, ctx in enumerate(contexts, 1):
        source = ctx.get("source", "database")
        score = ctx.get("score", 0)
        lines.append(f"[Context {i} | Source: {source} | Relevance: {score:.2f}]")
        lines.append(ctx["text"])
        lines.append("")

    return "\n".join(lines)

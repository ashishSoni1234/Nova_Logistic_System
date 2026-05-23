from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from rag.retriever import retrieve_context, retrieve_multi_collection, format_context_for_prompt
from config import settings
import logging
import json

logger = logging.getLogger(__name__)

_llm = None


def get_llm() -> ChatGroq:
    """Singleton Groq LLM instance."""
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.1,
            max_tokens=2048,
        )
        logger.info(f"Groq LLM initialized: {settings.groq_model}")
    return _llm


async def rag_query(
    query: str,
    collection_keys: list[str] = None,
    system_prompt: str = None,
    n_results: int = 5,
) -> dict:
    """
    Full RAG pipeline:
    1. Embed query
    2. Retrieve relevant context from ChromaDB
    3. Build prompt with context
    4. Send to Groq Llama 3.1
    5. Return structured response
    """
    try:
        if collection_keys is None:
            collection_keys = ["supply_chain"]

        contexts = retrieve_multi_collection(query, collection_keys, n_results=n_results)
        context_text = format_context_for_prompt(contexts)

        default_system = (
            "You are Nova, an expert AI assistant for logistics and supply chain management. "
            "Use the provided context to answer accurately. "
            "If the context doesn't contain enough information, say so clearly. "
            "Always provide structured, concise responses."
        )

        messages = [
            SystemMessage(content=system_prompt or default_system),
            HumanMessage(content=f"""CONTEXT:
{context_text}

QUESTION: {query}

Please provide a clear, structured answer based on the context above."""),
        ]

        llm = get_llm()
        response = llm.invoke(messages)
        answer = response.content

        return {
            "answer": answer,
            "contexts_used": len(contexts),
            "sources": [ctx.get("source", "unknown") for ctx in contexts],
            "query": query,
        }

    except Exception as e:
        logger.error(f"RAG pipeline error: {e}")
        return {
            "answer": f"RAG query failed: {str(e)}",
            "contexts_used": 0,
            "sources": [],
            "query": query,
        }


async def extract_structured_data(
    text: str,
    schema_description: str,
    example_output: str = "",
) -> dict:
    """Use Groq to extract structured JSON data from text."""
    try:
        system_prompt = (
            "You are an expert data extraction AI. "
            "Extract structured information from the provided text. "
            "Always respond with valid JSON only. No explanations, just JSON."
        )

        prompt = f"""Extract the following information from the text below.

SCHEMA: {schema_description}

{f'EXAMPLE OUTPUT FORMAT: {example_output}' if example_output else ''}

TEXT TO EXTRACT FROM:
{text[:3000]}

Respond with valid JSON only:"""

        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]
        response = llm.invoke(messages)
        content = response.content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return json.loads(content.strip())

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in extraction: {e}")
        return {"error": "Failed to parse LLM response as JSON", "raw": content if 'content' in dir() else ""}
    except Exception as e:
        logger.error(f"Structured extraction error: {e}")
        return {"error": str(e)}


async def classify_and_reason(
    input_text: str,
    task: str,
    options: list[str],
    context_keys: list[str] = None,
) -> dict:
    """Classify input into one of the options with reasoning."""
    try:
        contexts = []
        if context_keys:
            contexts = retrieve_multi_collection(input_text, context_keys, n_results=3)
        context_text = format_context_for_prompt(contexts)

        prompt = f"""Task: {task}

Options: {', '.join(options)}

Context:
{context_text}

Input to classify:
{input_text[:2000]}

Respond in this exact JSON format:
{{
  "classification": "<one of the options>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>",
  "flags": ["<any important observations>"]
}}"""

        llm = get_llm()
        messages = [
            SystemMessage(content="You are an expert classification AI. Always respond with valid JSON."),
            HumanMessage(content=prompt),
        ]
        response = llm.invoke(messages)
        content = response.content.strip()

        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        return json.loads(content.strip())

    except Exception as e:
        logger.error(f"Classification error: {e}")
        return {
            "classification": options[0] if options else "unknown",
            "confidence": 0.0,
            "reasoning": f"Classification failed: {str(e)}",
            "flags": [],
        }

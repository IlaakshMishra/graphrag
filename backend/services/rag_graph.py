"""LangGraph stateful conversational RAG pipeline.

Graph topology:

    START → retrieve → graph_retrieve → grade_documents → generate → END

State carries the question, rolling chat history (last N turns),
retrieved chunks, and the final answer + citations. We use LangGraph
rather than naive chains so the same graph can later host branches
(e.g. self-correction, query rewriting) without restructuring the code.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI

from backend.config import get_settings
from backend.services.graph_store import get_graph_store
from backend.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGState(TypedDict, total=False):
    question: str
    chat_history: List[Dict[str, str]]
    retrieved_docs: List[Dict[str, Any]]
    relevant_docs: List[Dict[str, Any]]
    graph_context: list  # entities from Neo4j knowledge graph
    answer: str
    sources: List[Dict[str, Any]]
    session_id: str
    namespace: str


_GRADER_SYSTEM = (
    "You are a strict relevance grader. Given a user question and a single "
    "document chunk, decide whether the chunk could help answer the question.\n"
    "Chunks may include OCR text from figures, diagrams, or screenshots — treat "
    "that text as real document content: if it could contain labels, queries, "
    "arrows, or terms relevant to the question, reply YES.\n"
    "Reply with only YES or NO."
)

_GENERATE_SYSTEM = (
    "You are a precise, helpful research assistant. Answer using ONLY the "
    "provided context. The context may mix normal PDF text with OCR lines "
    "from figures or diagrams — read those lines carefully and quote or "
    "summarize what they say when they answer the question.\n"
    "Do not claim that diagrams are 'only images' or 'not in the text' if "
    "the context includes OCR from that page or figure.\n"
    "If the user asks about 'Figure N' or text inside a diagram, quote any "
    "matching OCR lines from the cited page even if they partially overlap "
    "the body text.\n"
    "If the context is empty or truly contains no usable information, say "
    "exactly: \"I don't know based on the provided documents.\" "
    "Cite sources inline using the [filename] format. Be concise."
)


def _openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().OPENAI_API_KEY)


def _format_context(docs: List[Dict[str, Any]]) -> str:
    if not docs:
        return "(no context retrieved)"
    blocks = []
    for d in docs:
        src = d.get("source", "unknown")
        page = d.get("page")
        header = f"[{src}" + (f" p.{page}" if page else "") + "]"
        blocks.append(f"{header}\n{d.get('text', '').strip()}")
    return "\n\n---\n\n".join(blocks)


def _trim_history(
    history: List[Dict[str, str]],
    window: int,
) -> List[Dict[str, str]]:
    if not history:
        return []
    return history[-(window * 2) :]


async def _retrieve_node(state: RAGState) -> RAGState:
    cfg = get_settings()
    docs = await VectorStore.get().query(
        query_text=state["question"],
        namespace=state["namespace"],
        top_k=cfg.RETRIEVAL_TOP_K,
    )
    logger.info("retrieved %d docs for ns=%s", len(docs), state["namespace"])
    return {"retrieved_docs": docs}


async def _graph_retrieve_node(state: RAGState) -> RAGState:
    cfg = get_settings()
    client = _openai_client()

    entity_names: list[str] = []
    try:
        resp = await client.chat.completions.create(
            model=cfg.OPENAI_GRADER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract 3-5 key entity names from the question. "
                        'Return JSON: {"entities": ["name1", "name2"]}'
                    ),
                },
                {"role": "user", "content": state["question"]},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        entity_names = data.get("entities", [])
    except Exception:  # noqa: BLE001
        entity_names = []

    graph_context: list[dict] = []
    if entity_names and state.get("namespace"):
        try:
            graph_store = await get_graph_store()
            graph_context = await asyncio.to_thread(
                graph_store.query_related,
                entity_names,
                state["namespace"],
                cfg.GRAPH_RETRIEVAL_HOPS,
            )
            graph_context = graph_context[: cfg.GRAPH_MAX_ENTITIES]
        except Exception:  # noqa: BLE001
            graph_context = []

    logger.info("graph_retrieve found %d entities", len(graph_context))
    return {"graph_context": graph_context}


async def _grade_one(
    client: AsyncOpenAI, model: str, question: str, doc: Dict[str, Any]
) -> bool:
    text = doc.get("text", "").strip()
    if not text:
        return False
    user_msg = (
        f"Question:\n{question}\n\n"
        f"Document chunk:\n{text}\n\n"
        "Is this chunk relevant? Reply YES or NO."
    )
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _GRADER_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=4,
        )
        verdict = (resp.choices[0].message.content or "").strip().upper()
        return verdict.startswith("YES")
    except Exception as exc:  # noqa: BLE001
        logger.warning("grader error, defaulting to keep doc: %s", exc)
        return True


async def _grade_node(state: RAGState) -> RAGState:
    cfg = get_settings()
    docs = state.get("retrieved_docs", []) or []
    if not docs:
        return {"relevant_docs": []}

    client = _openai_client()
    verdicts = await asyncio.gather(
        *[_grade_one(client, cfg.OPENAI_GRADER_MODEL, state["question"], d) for d in docs]
    )
    kept = [d for d, ok in zip(docs, verdicts) if ok]
    if not kept and docs:
        n = min(cfg.GRADER_FALLBACK_TOP_N, len(docs))
        kept = docs[:n]
        logger.warning(
            "grader kept 0/%d — using top %d retrieved chunks as fallback (noisy OCR/diagram queries)",
            len(docs),
            n,
        )
    logger.info("grader kept %d / %d (after fallback if needed)", len(kept), len(docs))
    return {"relevant_docs": kept}


async def _generate_node(state: RAGState) -> RAGState:
    cfg = get_settings()
    docs = state.get("relevant_docs") or state.get("retrieved_docs") or []
    history = _trim_history(state.get("chat_history", []) or [], cfg.HISTORY_WINDOW)

    if not docs:
        return {
            "answer": "I don't know based on the provided documents.",
            "sources": [],
        }

    context = _format_context(docs)

    graph_context = state.get("graph_context", [])
    if graph_context:
        graph_lines = [
            f"- {e['name']} ({e.get('type', 'Unknown')}): {e.get('description', '')}"
            for e in graph_context
            if e.get("name")
        ]
        if graph_lines:
            context += "\n\nKNOWLEDGE GRAPH CONTEXT (entities related to this query):\n"
            context += "\n".join(graph_lines)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": _GENERATE_SYSTEM},
        {
            "role": "system",
            "content": f"Context retrieved from the user's documents:\n\n{context}",
        },
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": state["question"]})

    client = _openai_client()
    resp = await client.chat.completions.create(
        model=cfg.OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    answer = (resp.choices[0].message.content or "").strip()

    seen: set[str] = set()
    sources: List[Dict[str, Any]] = []
    for d in docs:
        key = f"{d.get('source')}::{d.get('chunk_index')}"
        if key in seen:
            continue
        seen.add(key)
        snippet = (d.get("text") or "").strip().replace("\n", " ")
        sources.append(
            {
                "source": d.get("source", "unknown"),
                "page": d.get("page"),
                "chunk_index": d.get("chunk_index"),
                "score": d.get("score"),
                "snippet": snippet[:280],
            }
        )

    return {"answer": answer, "sources": sources}


def _build_graph():
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", _retrieve_node)
    graph.add_node("graph_retrieve", _graph_retrieve_node)
    graph.add_node("grade_documents", _grade_node)
    graph.add_node("generate", _generate_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "graph_retrieve")
    graph.add_edge("graph_retrieve", "grade_documents")
    graph.add_edge("grade_documents", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


_compiled_graph = None


def _graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


async def run_rag(
    question: str,
    chat_history: List[Dict[str, str]],
    namespace: str,
    session_id: str,
) -> Dict[str, Any]:
    trace = await run_rag_trace(
        question=question,
        chat_history=chat_history,
        namespace=namespace,
        session_id=session_id,
    )
    return {
        "answer": trace["answer"],
        "sources": trace["sources"],
        "session_id": session_id,
        "namespace": namespace,
        "used_documents": trace["used_documents"],
    }


async def run_rag_trace(
    question: str,
    chat_history: List[Dict[str, str]],
    namespace: str,
    session_id: str,
) -> Dict[str, Any]:
    """Full graph invoke with fields needed for RAGAS / evaluation (contexts, counts)."""
    initial: RAGState = {
        "question": question,
        "chat_history": chat_history or [],
        "namespace": namespace,
        "session_id": session_id,
        "graph_context": [],
    }
    final = await _graph().ainvoke(initial)
    retrieved = final.get("retrieved_docs") or []
    relevant = final.get("relevant_docs") or []
    contexts = [
        (d.get("text") or "").strip()
        for d in relevant
        if (d.get("text") or "").strip()
    ]
    used_for_gen = relevant or retrieved
    return {
        "answer": final.get("answer", ""),
        "sources": final.get("sources", []),
        "session_id": session_id,
        "namespace": namespace,
        "used_documents": len(used_for_gen),
        "contexts": contexts,
        "retrieved_count": len(retrieved),
        "relevant_count": len(relevant),
    }

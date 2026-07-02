import requests

from . import config
from .ingest import load_vectorstore


def _call_llm(prompt: str) -> str:
    """Call a local Ollama server (no API key, no internet needed)."""
    url = f"{config.OLLAMA_URL}/api/chat"
    payload = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Could not reach Ollama at "
            f"{config.OLLAMA_URL}. Is it running? Start it with 'ollama serve' "
            f"(and make sure you've pulled the model: 'ollama pull {config.LLM_MODEL}')."
        )

    data = resp.json()
    return data["message"]["content"]


def answer_question(repo_id: str, question: str, top_k: int = None):
    vectorstore = load_vectorstore(repo_id)

    if vectorstore is None:
        raise ValueError(
            f"No index found for repo_id='{repo_id}'. Process the repository first."
        )

    top_k = top_k or config.TOP_K

    docs = vectorstore.similarity_search(question, k=top_k)

    results = []
    for doc in docs:
        results.append(
            {
                "source": doc.metadata.get("source", "Unknown"),
                "type": doc.metadata.get("type", "text"),
                "content": doc.page_content,
            }
        )

    context = "\n\n".join(
        f"[Source: {r['source']}]\n{r['content']}" for r in results
    )

    prompt = (
        "You are a helpful assistant answering questions about a GitHub "
        "repository, using only the context below. If the answer isn't "
        "in the context, say so.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

    answer = _call_llm(prompt)

    return {
        "answer": answer,
        "results": results,
        "sources": list(dict.fromkeys([r["source"] for r in results])),
    }

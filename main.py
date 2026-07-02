from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

from .ingest import ingest_repository, load_vectorstore
from .rag import answer_question
from . import config, rag
import inspect

app = FastAPI(title="GitHub Repository Explorer API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    github_url: str


class AskRequest(BaseModel):
    repo_id: str
    question: str


@app.get("/debug")
def debug():
    """
    Shows the ACTUAL config and code this running server is using — use this to
    confirm your .env and file edits really took effect, instead of guessing.
    """
    source = inspect.getsource(rag._call_llm)

    ollama_reachable = None
    try:
        r = requests.get(config.OLLAMA_URL, timeout=3)
        ollama_reachable = r.status_code == 200
    except Exception:
        ollama_reachable = False

    return {
        "ollama_url": config.OLLAMA_URL,
        "ollama_reachable": ollama_reachable,
        "llm_model": config.LLM_MODEL,
        "using_ollama": "ollama" in source.lower() or config.OLLAMA_URL in source,
        "using_old_dead_endpoint": "api-inference.huggingface.co" in source,
        "rag_module_file": rag.__file__,
        "config_module_file": config.__file__,
    }


@app.get("/")
def root():
    return {"status": "ok", "message": "GitHub Repository Explorer API"}


@app.post("/ingest")
def ingest(req: IngestRequest):
    """Clone a public repo, extract README/code/issues, embed, and store in FAISS."""
    try:
        result = ingest_repository(req.github_url)
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/status/{repo_id}")
def status(repo_id: str):
    vs = load_vectorstore(repo_id)
    return {"repo_id": repo_id, "indexed": vs is not None}


@app.post("/ask")
def ask(req: AskRequest):
    """Answer a natural-language question grounded in the indexed repository."""
    try:
        result = answer_question(req.repo_id, req.question)
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
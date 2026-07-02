# 🔍 GitHub Repository Explorer (RAG-powered)

Ask any public GitHub repo questions like *"What does this project do?"* or *"Where is
the authentication code?"* and get answers grounded in the repo's actual README, code,
and issues — not made up.

---

## 1. How it works (plain language)

Think of it as 3 stages:

**Stage 1 — Read the repository (once, when you "process" a repo)**
1. You paste a GitHub URL.
2. The backend downloads (`git clone`) that repo to disk.
3. It reads the README, every code file, and pulls the repo's issues from GitHub's API.
4. Long files are cut into small "chunks" (a few hundred words each) — because an AI
   model can only look at small pieces of text at a time, not a whole codebase.
5. Each chunk is converted into a list of numbers (an "embedding") that captures its
   *meaning*, not just its words.
6. All those number-lists are stored in **FAISS**, a fast similarity-search index —
   like a search engine, but for meaning instead of keywords.

**Stage 2 — Ask a question**
1. You type a question ("Where is the login logic?").
2. That question is also converted into an embedding.
3. FAISS finds the 5 chunks whose meaning is closest to your question.
4. Those chunks (plus your question) are handed to an LLM with strict instructions:
   *"Only answer from this context. If it's not here, say you don't know."*
5. The LLM writes a concise answer and the app shows you which files it used.

**Stage 3 — Display**
Streamlit shows a chat-style UI with your question, the answer, and clickable-looking
source tags (e.g. `src/auth.py`) so you can verify where the answer came from.

```
User → GitHub URL → clone repo → extract README/code/issues → chunk → embed → FAISS
User → question → FastAPI → FAISS retrieves chunks → LLM explains → answer + sources → Streamlit
```

### Why the answers stay accurate (not "inappropriate"/hallucinated)
- The LLM is **only** given the retrieved chunks — it has no access to the internet or
  its own training data about the repo, so it can't make things up about *this* project.
- The system prompt forces it to reply `"I couldn't find this in the repository."`
  when the answer genuinely isn't in the retrieved context, instead of guessing.
- Every answer is shown with its **source files**, so you can always double-check.
- The prompt explicitly restricts the assistant to repository-related, technical answers.

### A note on "Databricks"
Databricks is a paid, cluster-based platform mainly useful when you need to clone and
process **thousands** of repos in parallel at scale. For a single-repo explorer like
this, that's overkill — so `backend/ingest.py` and `backend/github_utils.py` implement
the *same* clone → extract → chunk logic as plain Python functions. If you later want
to scale this to many repositories, you can import these exact functions into a
Databricks notebook and run them across a cluster — no rewrite needed.

---

## 2. Project structure

```
github-rag-explorer/
├── backend/
│   ├── main.py            # FastAPI app: /ingest, /ask, /status endpoints
│   ├── ingest.py           # Clone → extract → chunk → embed → store in FAISS
│   ├── rag.py              # Retrieval + grounded LLM answer generation
│   ├── github_utils.py     # URL parsing, git clone, GitHub issues API
│   ├── config.py           # All settings (models, chunk sizes, paths)
│   └── requirements.txt
├── frontend/
│   ├── app.py               # Streamlit chat UI
│   └── requirements.txt
├── data/
│   ├── repos/                # Cloned repositories land here
│   └── indexes/               # Saved FAISS indexes land here
├── .env.example
└── README.md
```

---

## 3. Setup (step by step)

### Prerequisites
- Python 3.10+
- `git` installed and on your PATH
- A free [Hugging Face](https://huggingface.co/join) account (for LLM answers)

### Step 1 — Get the code onto your machine
Unzip the project folder you downloaded, then open a terminal inside it.

### Step 2 — Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### Step 3 — Install backend dependencies
```bash
pip install -r backend/requirements.txt
```

### Step 4 — Configure your environment
```bash
cp .env.example .env
```
Open `.env` and fill in:
- `HF_TOKEN` — from https://huggingface.co/settings/tokens (needed for real LLM
  answers; without it, the app still runs and shows you the retrieved context, just
  without an AI-generated explanation).
- `GITHUB_TOKEN` — optional, raises the GitHub API rate limit for fetching issues.

> **Note on the LLM model:** Hugging Face retired its old free `api-inference.huggingface.co`
> endpoint — this app now calls their current `router.huggingface.co` chat API instead.
> That API needs a **chat/instruct** model (not a plain text-generation model like
> `flan-t5-large`, which won't work here). The default, `Qwen/Qwen2.5-1.5B-Instruct`,
> is free and ungated. Another good option: `meta-llama/Llama-3.2-3B-Instruct` (may
> require accepting Meta's license once on the model's Hugging Face page).
>
> **After editing `.env`, restart the backend** (`Ctrl+C` then re-run `uvicorn ...`) —
> it's only read once at startup, so changes won't apply to an already-running server.

### Step 5 — Start the backend (FastAPI)
```bash
uvicorn backend.main:app --reload --port 8000
```
Leave this running. Visit http://localhost:8000/docs to see interactive API docs.

### Step 6 — Install & start the frontend (Streamlit), in a new terminal
```bash
source venv/bin/activate
pip install -r frontend/requirements.txt
streamlit run frontend/app.py
```
Your browser will open at http://localhost:8501.

### Step 7 — Use it
1. In the sidebar, paste a public GitHub URL, e.g. `https://github.com/psf/requests`.
2. Click **Process Repository** (first run downloads the embedding model, ~1-2 min).
3. Ask questions in the chat box, or click one of the suggested questions.

---

## 4. Example questions to try
- "What does this project do?"
- "How do I install it?"
- "Where is the authentication code?"
- "Explain the database connection."
- "Which file handles user login?"
- "List the open issues about bugs."
- "What license does this project use?"

---

## 5. Extending this project
- **Swap the LLM**: `backend/rag.py` → `_call_llm()` is the only place that calls an
  LLM. Point it at OpenAI, Anthropic's Claude API, or a local model instead of the
  free Hugging Face endpoint if you want faster/better answers.
- **Swap FAISS for ChromaDB**: `backend/ingest.py` uses LangChain's `FAISS` wrapper;
  swapping in `Chroma` from `langchain_community.vectorstores` is a near drop-in change.
- **Persist multiple repos**: indexes are already saved per-repo under
  `data/indexes/<owner>__<repo>/`, so the app already supports switching between
  previously-processed repos via `repo_id` without re-cloning.
- **Private repos**: pass an authenticated clone URL
  (`https://<token>@github.com/owner/repo.git`) in `github_utils.clone_repository`.

---

## 6. Troubleshooting
| Problem | Fix |
|---|---|
| `git clone failed` | Check the URL is a real **public** repo and `git` is installed |
| Ingest is slow | First run downloads the ~90MB embedding model — later runs are fast |
| LLM errors / 503 | Free HF models can be "cold" — wait 20s and retry, or pick a smaller model |
| Empty/odd answers | Try more specific questions; check the `sources` shown are relevant |
| CORS / connection errors in Streamlit | Confirm the backend is running and the Backend URL in the sidebar matches (`http://localhost:8000`) |

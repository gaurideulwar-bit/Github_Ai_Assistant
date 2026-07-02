import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language
from langchain.schema import Document

from . import config
from .github_utils import clone_repository, fetch_issues, parse_github_url

_embeddings = None


def get_embeddings():
    """Lazy-load the local embedding model (downloaded once, cached after)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)
    return _embeddings


def _iter_repo_files(repo_path: str):
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in config.SKIP_DIRS]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                if os.path.getsize(fpath) > config.MAX_FILE_SIZE_BYTES:
                    continue
            except OSError:
                continue
            yield fpath


def _read_text(fpath: str):
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def build_documents(repo_path: str, owner: str, repo: str):
    """Turn README/docs, code, and issues into LangChain Documents with metadata."""
    docs = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.TEXT_CHUNK_SIZE, chunk_overlap=config.TEXT_CHUNK_OVERLAP
    )

    for fpath in _iter_repo_files(repo_path):
        rel_path = os.path.relpath(fpath, repo_path)
        fname_lower = os.path.basename(fpath).lower()
        ext = os.path.splitext(fpath)[1].lower()

        # ---- README / markdown / plain docs ----
        if fname_lower.startswith("readme") or ext in {".md", ".rst", ".txt"}:
            content = _read_text(fpath)
            if not content or not content.strip():
                continue
            for i, chunk in enumerate(text_splitter.split_text(content)):
                docs.append(Document(
                    page_content=chunk,
                    metadata={"source": rel_path, "type": "doc", "chunk": i},
                ))

        # ---- Source code (comments live naturally inside these chunks) ----
        elif ext in config.CODE_EXTENSIONS:
            content = _read_text(fpath)
            if not content or not content.strip():
                continue
            lang_name = config.CODE_EXTENSIONS[ext]
            splitter = text_splitter
            lc_lang = getattr(Language, lang_name.upper(), None)
            if lc_lang:
                try:
                    splitter = RecursiveCharacterTextSplitter.from_language(
                        language=lc_lang,
                        chunk_size=config.CODE_CHUNK_SIZE,
                        chunk_overlap=config.CODE_CHUNK_OVERLAP,
                    )
                except Exception:
                    splitter = text_splitter

            for i, chunk in enumerate(splitter.split_text(content)):
                docs.append(Document(
                    page_content=chunk,
                    metadata={"source": rel_path, "type": "code", "language": lang_name, "chunk": i},
                ))

    # ---- GitHub issues ----
    for issue in fetch_issues(owner, repo):
        content = f"Issue #{issue['number']}: {issue['title']}\n\n{issue['body']}"
        for i, chunk in enumerate(text_splitter.split_text(content)):
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "source": f"issue #{issue['number']}", "type": "issue",
                    "state": issue["state"], "url": issue["url"], "chunk": i,
                },
            ))

    return docs


def ingest_repository(github_url: str) -> dict:
    """Full pipeline: clone -> extract -> chunk -> embed -> store in FAISS."""
    owner, repo = parse_github_url(github_url)
    repo_id, repo_path = clone_repository(github_url)

    docs = build_documents(repo_path, owner, repo)
    if not docs:
        raise ValueError("No README, code, or issue content found to index in this repository.")

    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(docs, embeddings)

    index_path = os.path.join(config.INDEX_DIR, repo_id)
    vectorstore.save_local(index_path)

    return {
        "repo_id": repo_id,
        "owner": owner,
        "repo": repo,
        "num_chunks": len(docs),
        "index_path": index_path,
    }


def load_vectorstore(repo_id: str):
    index_path = os.path.join(config.INDEX_DIR, repo_id)
    if not os.path.exists(index_path):
        return None
    embeddings = get_embeddings()
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)

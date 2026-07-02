import os
from dotenv import load_dotenv

# ---------------- Paths ----------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(BASE_DIR, ".env"))
REPO_CLONE_DIR = os.path.join(BASE_DIR, "data", "repos")
INDEX_DIR = os.path.join(BASE_DIR, "data", "indexes")

os.makedirs(REPO_CLONE_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# ---------------- GitHub ----------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# ---------------- Embeddings ----------------
# Runs 100% locally and free, no API key needed.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# ---------------- LLM (local via Ollama) ----------------
# No API key, no internet needed after you've pulled a model.
# Install: https://ollama.com/download
# Then run:  ollama pull llama3.2   (or phi3, mistral, qwen2.5, etc.)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")

# ---------------- Chunking ----------------
CODE_CHUNK_SIZE = 800
CODE_CHUNK_OVERLAP = 100
TEXT_CHUNK_SIZE = 1000
TEXT_CHUNK_OVERLAP = 150

# ---------------- Retrieval ----------------
TOP_K = 5

# ---------------- File filters ----------------
CODE_EXTENSIONS = {
    ".py": "python", ".js": "js", ".ts": "ts", ".java": "java",
    ".go": "go", ".rb": "ruby", ".cpp": "cpp", ".c": "c",
    ".cs": "csharp", ".php": "php", ".rs": "rust", ".kt": "kotlin",
}
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".idea", ".vscode"}
MAX_FILE_SIZE_BYTES = 300_000

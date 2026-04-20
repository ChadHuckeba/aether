import os
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# 1. Environment and Path Setup
BASE_DIR = Path(__file__).parent.resolve()
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# 2. Key Constants
# Use AETHER_SAFE_ROOT from env, fallback to parent of current directory
SAFE_ROOT = Path(os.getenv("AETHER_SAFE_ROOT", str(BASE_DIR.parent))).resolve()
STORAGE_DIR = BASE_DIR / "storage"
PROJECTS_FILE = BASE_DIR / "projects.json"
REQUIRED_EXTS = [".py", ".md", ".ps1", ".txt", ".json", ".toml", ".yaml", ".yml"]

# 3. Global LlamaIndex Settings
def init_settings():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found in environment variables.")

    # LLM Configuration
    Settings.llm = GoogleGenAI(
        model="gemini-3-flash-preview", 
        api_key=api_key
    )

    # Embedding Configuration
    Settings.embed_model = GoogleGenAIEmbedding(
        model_name="models/gemini-embedding-001", 
        api_key=api_key
    )

    # Performance Settings
    Settings.embed_batch_size = 100
    Settings.chunk_size = 1024

# Automatically initialize settings on import
init_settings()

def get_storage_path(project_name: str) -> Path:
    """Helper to resolve storage directory for a specific project."""
    folder = project_name.lower().replace(" ", "_")
    path = STORAGE_DIR / folder
    path.mkdir(parents=True, exist_ok=True)
    return path

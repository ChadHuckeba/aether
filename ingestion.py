import os
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Settings, SimpleDirectoryReader
from llama_index.readers.github import GithubRepositoryReader, GithubClient
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter

# Environment Setup
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Global Settings Configuration
Settings.llm = GoogleGenAI(
    model="gemini-3-flash-preview", 
    api_key=os.getenv("GEMINI_API_KEY")
)

Settings.embed_model = GoogleGenAIEmbedding(
    model_name="models/gemini-embedding-001", 
    api_key=os.getenv("GEMINI_API_KEY")
)

Settings.embed_batch_size = 100
token = os.getenv("GITHUB_TOKEN")

from llama_index.core import VectorStoreIndex, Settings, SimpleDirectoryReader, StorageContext, load_index_from_storage

# ... (Environment and Settings unchanged)

def sync_local_dir_custom(dir_path: str, storage_dir: str):
    """
    Orchestrates the retrieval and indexing of a local directory into a specific storage folder.
    Uses incremental indexing (refresh) for efficiency.
    """
    print(f"Syncing {dir_path} -> {storage_dir}...")
    
    storage_path = Path(storage_dir)
    docstore_exists = (storage_path / "docstore.json").exists()

    reader = SimpleDirectoryReader(
        input_dir=dir_path,
        recursive=True,
        exclude=["node_modules", ".git", "__pycache__", "venv", ".venv", "storage"],
        required_exts=[".py", ".md", ".ps1", ".txt", ".json", ".toml", ".yaml", ".yml"]
    )
    
    documents = reader.load_data()

    if docstore_exists:
        print("Existing index found. Refreshing changed documents...")
        storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
        index = load_index_from_storage(storage_context)
        refreshed_docs = index.refresh_ref_docs(documents)
        
        # refreshed_docs is a list of booleans indicating if the document was updated/added
        updated_count = sum(refreshed_docs)
        if updated_count > 0:
            print(f"Updated {updated_count} documents.")
            index.storage_context.persist(persist_dir=storage_dir)
        else:
            print("No changes detected. Index is up to date.")
    else:
        print(f"No index found. Performing initial indexing of {len(documents)} documents...")
        # Parsing and Node Hygiene (SentenceSplitter is handled automatically by VectorStoreIndex)
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=storage_dir)
    
    print("Sync complete.")

def sync_local_dir(dir_path: str):
    """Legacy wrapper for default storage."""
    sync_local_dir_custom(dir_path, "./storage")

def sync_github_repo(owner: str, repo: str, branch: str = "main"):
    """
    Orchestrates the retrieval and indexing of a specific GitHub repository.
    """
    print(f"Starting sync for {owner}/{repo}...")
    
    github_client = GithubClient(github_token=token)
    
    reader = GithubRepositoryReader(
        github_client=github_client,
        owner=owner,
        repo=repo,
        use_parser=False,
        verbose=True,
        filter_directories=(
            ["node_modules", ".git", "__pycache__", "venv", ".venv", "docs"], 
            GithubRepositoryReader.FilterType.EXCLUDE
        ),
        filter_file_extensions=(
            [".py", ".md", ".ps1", ".txt"], 
            GithubRepositoryReader.FilterType.INCLUDE
        )
    )
    
    # --- LOGIC MUST BE INDENTED WITHIN THE FUNCTION ---
    print("Fetching documents from GitHub...")
    raw_documents = reader.load_data(branch=branch)
    
    # Parsing and Node Hygiene
    parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
    nodes = parser.get_nodes_from_documents(raw_documents)
    
    # Filter empty content to prevent embedding API KeyErrors
    clean_nodes = [node for node in nodes if node.get_content().strip()]
    print(f"Indexing {len(clean_nodes)} valid nodes...")

    # Build and Persist Index
    index = VectorStoreIndex(clean_nodes)
    index.storage_context.persist(persist_dir="./storage")
    
    print(f"Sync complete. Aether is ready on the Stable Tier.")

if __name__ == "__main__":
    project_path = os.getenv("PROJECT_PATH")
    if not project_path:
        print("Error: PROJECT_PATH not found in .env")
    else:
        sync_local_dir(project_path)
import os
from pathlib import Path
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.readers.github import GithubRepositoryReader, GithubClient
from llama_index.core.node_parser import SentenceSplitter
from config import REQUIRED_EXTS

# No need to manually load_dotenv or init Settings, config.py does it on import

token = os.getenv("GITHUB_TOKEN")

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
        required_exts=REQUIRED_EXTS
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

def sync_local_dir(dir_path: str, project_name: str = None):
    """Orchestrates retrieval and indexing with project-specific storage."""
    if not project_name:
        project_name = os.getenv("PROJECT_NAME", "default")
    
    folder = project_name.lower().replace(" ", "_")
    storage_dir = Path("./storage") / folder
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    sync_local_dir_custom(dir_path, str(storage_dir))

def sync_github_repo(owner: str, repo: str, branch: str = "main"):
    """
    Orchestrates the retrieval and indexing of a specific GitHub repository.
    Uses incremental indexing (refresh) for efficiency if possible.
    """
    project_name = f"{owner}_{repo}"
    storage_dir = get_storage_path(project_name)
    docstore_exists = (storage_dir / "docstore.json").exists()
    
    print(f"Starting sync for {owner}/{repo} (Branch: {branch})...")
    
    github_client = GithubClient(github_token=token)
    
    reader = GithubRepositoryReader(
        github_client=github_client,
        owner=owner,
        repo=repo,
        use_parser=False,
        verbose=True,
        filter_directories=(
            ["node_modules", ".git", "__pycache__", "venv", ".venv", "docs", "storage"], 
            GithubRepositoryReader.FilterType.EXCLUDE
        ),
        filter_file_extensions=(
            REQUIRED_EXTS, 
            GithubRepositoryReader.FilterType.INCLUDE
        )
    )
    
    print("Fetching documents from GitHub...")
    documents = reader.load_data(branch=branch)
    
    if docstore_exists:
        print("Existing index found. Refreshing changed documents...")
        storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
        index = load_index_from_storage(storage_context)
        refreshed_docs = index.refresh_ref_docs(documents)
        
        updated_count = sum(refreshed_docs)
        if updated_count > 0:
            print(f"Updated {updated_count} documents.")
            index.storage_context.persist(persist_dir=str(storage_dir))
        else:
            print("No changes detected. GitHub index is up to date.")
    else:
        print(f"No index found. Performing initial indexing of {len(documents)} documents...")
        # Build and Persist Index
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=str(storage_dir))
    
    print(f"Sync complete. Storage: {storage_dir}")

if __name__ == "__main__":
    project_path = os.getenv("PROJECT_PATH")
    project_name = os.getenv("PROJECT_NAME")
    if not project_path:
        print("Error: PROJECT_PATH not found in .env")
    else:
        sync_local_dir(project_path, project_name)
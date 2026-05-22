import os
import time
import logging
from pathlib import Path
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.readers.github import GithubRepositoryReader, GithubClient
from aether.core.config import REQUIRED_EXTS, get_storage_path

logger = logging.getLogger("aether.ingest")
token = os.getenv("GITHUB_TOKEN")

def sync_local_dir_custom(dir_path: str, storage_dir: str):
    """
    Orchestrates the retrieval and indexing of a local directory into a specific storage folder.
    Uses incremental indexing (refresh) for efficiency.
    """
    logger.info(f"Syncing {dir_path} -> {storage_dir}...")
    
    storage_path = Path(storage_dir)
    docstore_exists = (storage_path / "docstore.json").exists()

    reader = SimpleDirectoryReader(
        input_dir=dir_path,
        recursive=True,
        exclude=["node_modules", ".git", "__pycache__", "venv", ".venv", "storage"],
        required_exts=REQUIRED_EXTS
    )
    
    documents = reader.load_data()
    for doc in documents:
        if doc.metadata and "file_path" in doc.metadata:
            doc.doc_id = doc.metadata["file_path"]

    if docstore_exists:
        logger.info("Existing index found. Refreshing changed documents...")
        storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
        index = load_index_from_storage(storage_context)
        batch_size = 5
        refreshed_docs = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Refreshing batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1} ({len(batch)} docs)...")
            
            retries = 5
            for attempt in range(retries):
                try:
                    batch_refreshed = index.refresh_ref_docs(batch)
                    refreshed_docs.extend(batch_refreshed)
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e):
                        wait_time = 15 * (attempt + 1)
                        logger.warning(f"Rate limited or server unavailable. Waiting {wait_time}s before retry (Attempt {attempt+1}/{retries})...")
                        time.sleep(wait_time)
                    else:
                        raise e
            else:
                raise RuntimeError("Failed to refresh documents after max retries due to rate limiting.")
            
            # Sleep between batches to respect rate limits
            time.sleep(2)

        updated_count = sum(refreshed_docs)

        # Remove docs for files that no longer exist on disk
        existing_doc_ids = {doc.doc_id for doc in documents}
        ref_doc_info = index.docstore.get_all_ref_doc_info()
        all_stored_ids = set(ref_doc_info.keys()) if ref_doc_info else set()
        stale_ids = all_stored_ids - existing_doc_ids
        for doc_id in stale_ids:
            index.delete_ref_doc(doc_id, delete_from_docstore=True)
        if stale_ids:
            logger.info(f"Purged {len(stale_ids)} stale documents.")

        # Persist if anything changed
        if updated_count > 0 or stale_ids:
            logger.info(f"Updated {updated_count} documents, purged {len(stale_ids)} stale documents.")
            index.storage_context.persist(persist_dir=storage_dir)
        else:
            logger.info("No changes detected. Index is up to date.")
    else:
        logger.info(f"No index found. Performing initial indexing of {len(documents)} documents...")
        index = VectorStoreIndex([])
        batch_size = 5
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Indexing batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1} ({len(batch)} docs)...")
            
            retries = 5
            for attempt in range(retries):
                try:
                    for doc in batch:
                        # Prevent duplicate insertion on retry attempts
                        ref_doc_info = index.docstore.get_all_ref_doc_info()
                        if ref_doc_info and doc.doc_id in ref_doc_info:
                            continue
                        index.insert(doc)
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e):
                        wait_time = 15 * (attempt + 1)
                        logger.warning(f"Rate limited or server unavailable. Waiting {wait_time}s before retry (Attempt {attempt+1}/{retries})...")
                        time.sleep(wait_time)
                    else:
                        raise e
            else:
                raise RuntimeError("Failed to index documents after max retries due to rate limiting.")
            
            # Persist after each successful batch so progress is not lost on failure
            index.storage_context.persist(persist_dir=storage_dir)
            
            # Sleep between batches to respect rate limits
            if i + batch_size < len(documents):
                time.sleep(2)
    
    logger.info("Sync complete.")

def sync_local_dir(dir_path: str, project_name: str = None):
    """Orchestrates retrieval and indexing with project-specific storage."""
    if not project_name:
        project_name = os.getenv("PROJECT_NAME", "default")
    
    storage_dir = get_storage_path(project_name)
    sync_local_dir_custom(dir_path, str(storage_dir))

def sync_github_repo(owner: str, repo: str, branch: str = "main"):
    """
    Orchestrates the retrieval and indexing of a specific GitHub repository.
    Uses incremental indexing (refresh) for efficiency if possible.
    """
    project_name = f"{owner}_{repo}"
    storage_dir = get_storage_path(project_name)
    docstore_exists = (storage_dir / "docstore.json").exists()
    
    logger.info(f"Starting sync for {owner}/{repo} (Branch: {branch})...")
    
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
    
    logger.info("Fetching documents from GitHub...")
    documents = reader.load_data(branch=branch)
    
    if docstore_exists:
        logger.info("Existing index found. Refreshing changed documents...")
        storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
        index = load_index_from_storage(storage_context)
        refreshed_docs = index.refresh_ref_docs(documents)
        
        updated_count = sum(refreshed_docs)
        if updated_count > 0:
            logger.info(f"Updated {updated_count} documents.")
            index.storage_context.persist(persist_dir=str(storage_dir))
        else:
            logger.info("No changes detected. GitHub index is up to date.")
    else:
        logger.info(f"No index found. Performing initial indexing of {len(documents)} documents...")
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=str(storage_dir))
    
    logger.info(f"Sync complete. Storage: {storage_dir}")

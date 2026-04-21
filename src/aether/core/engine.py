import asyncio
import os
import gc
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from llama_index.core import StorageContext, load_index_from_storage
from aether.core.ingest import sync_local_dir_custom
from aether.core.config import get_storage_path

async def get_index(active_project: str) -> Any:
    """Helper to load a LlamaIndex from storage."""
    storage_dir = str(get_storage_path(active_project))
    docstore_path = os.path.join(storage_dir, "docstore.json")
    
    if not os.path.exists(docstore_path):
        raise FileNotFoundError(f"No index found for {active_project}. Please Synchronize.")
    
    def _load():
        sc = StorageContext.from_defaults(persist_dir=storage_dir)
        return load_index_from_storage(sc)
    
    # Load in a thread to keep async loops clear
    return await asyncio.to_thread(_load)

async def run_ingestion(active_project: str, project_path: str) -> Dict[str, str]:
    """Orchestrates the ingestion process for a specific project."""
    if not os.path.exists(project_path):
        raise FileNotFoundError(f"Project source path not found: {project_path}")
        
    storage_dir = str(get_storage_path(active_project))
    
    # Run in a thread for CPU-intensive embedding
    await asyncio.to_thread(sync_local_dir_custom, project_path, storage_dir)
    
    return {
        "last_sync": datetime.now().strftime("%H:%M:%S"),
        "status": "idle"
    }

def query_aether(prompt: str, project_name: str = None):
    """Synchronous core query engine helper."""
    if not project_name:
        project_name = os.getenv("PROJECT_NAME", "default")
        
    storage_dir = get_storage_path(project_name)
    
    if not (storage_dir / "docstore.json").exists():
        raise FileNotFoundError(f"Storage directory {storage_dir} not found. Run ingestion.py first.")

    storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
    index = load_index_from_storage(storage_context)
    query_engine = index.as_query_engine(streaming=False)
    
    return query_engine.query(prompt)

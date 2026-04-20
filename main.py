import os
from pathlib import Path
from llama_index.core import StorageContext, load_index_from_storage
from config import get_storage_path

def query_aether(prompt: str):
    project_name = os.getenv("PROJECT_NAME", "default")
    storage_dir = get_storage_path(project_name)
    
    if not (storage_dir / "docstore.json").exists():
        raise FileNotFoundError(f"Storage directory {storage_dir} not found. Run ingestion.py first.")

    # 3. Load the index from the local JSON files
    storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
    index = load_index_from_storage(storage_context)

    # 4. Create the Query Engine
    # streaming=True allows for faster perceived response times
    query_engine = index.as_query_engine(streaming=False)
    
    response = query_engine.query(prompt)
    return response

if __name__ == "__main__":
    # Test Query: Replace this with any question about Vanguard
    test_query = "What is the relationship between base_scout.py and scout_core.py?"
    
    print(f"Querying Aether: {test_query}\n")
    result = query_aether(test_query)
    print(f"RESULT:\n{result}")
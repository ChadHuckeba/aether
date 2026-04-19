import os
import json
from pathlib import Path

from dotenv import load_dotenv

# Load environment to get PROJECT_NAME
load_dotenv()

def get_index_stats(storage_dir=None):
    if not storage_dir:
        project_name = os.getenv("PROJECT_NAME", "default")
        folder = project_name.lower().replace(" ", "_")
        storage_dir = Path("./storage") / folder
    
    storage_path = Path(storage_dir)
    if not storage_path.exists():
        print(f"Error: {storage_dir} not found.")
        return

    # 1. Physical File Stats
    print(f"--- Physical Storage ---")
    total_size = 0
    for f in storage_path.glob("*.json"):
        size_kb = f.stat().st_size / 1024
        total_size += size_kb
        print(f"{f.name}: {size_kb:.2f} KB")
    print(f"Total Index Size: {total_size:.2f} KB\n")

    # 2. Logic/Data Stats (Parsing docstore.json)
    docstore_path = storage_path / "docstore.json"
    with open(docstore_path, "r") as f:
        data = json.load(f)

    # Extracting internal counts
    # docstore_data -> doc_hash_map contains the ref_doc_ids
    doc_dict = data.get("docstore/data", {})
    ref_doc_info = data.get("docstore/ref_doc_info", {})
    
    nodes = list(doc_dict.keys())
    source_files = list(ref_doc_info.keys())

    print(f"--- Logical Index Stats ---")
    print(f"Total Source Files: {len(source_files)}")
    print(f"Total Vector Nodes (Chunks): {len(nodes)}")
    
    # 3. List unique filenames from metadata
    print(f"\n--- Files Indexed ---")
    indexed_files = set()
    for node_id, node_data in doc_dict.items():
        # LlamaIndex stores metadata in the __data__ or extra_info field
        metadata = node_data.get("__data__", {}).get("metadata", {})
        file_name = metadata.get("file_path") or metadata.get("file_name")
        if file_name:
            indexed_files.add(file_name)
    
    for f in sorted(indexed_files):
        print(f" - {f}")

if __name__ == "__main__":
    get_index_stats()
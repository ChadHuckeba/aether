import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import psutil
from config import get_storage_path

def get_index_metrics(project_name: str, project_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculates comprehensive metrics for a project's index.
    Combines physical storage stats with logical index data from docstore.json.
    """
    storage_dir = get_storage_path(project_name)
    docstore_path = storage_dir / "docstore.json"
    
    # Default empty structure
    metrics = {
        "project_name": project_name,
        "project_path_name": Path(project_path).name if project_path else "None",
        "node_count": 0,
        "file_count": 0,
        "total_size_kb": 0,
        "files": [],
        "exists": False,
        "ram_usage_mb": round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    }

    if not docstore_path.exists():
        return metrics

    try:
        # 1. Physical Storage Stats
        total_size_kb = sum(f.stat().st_size for f in storage_dir.glob("*.json")) / 1024
        metrics["total_size_kb"] = round(total_size_kb, 2)
        metrics["exists"] = True

        # 2. Logical Index Stats
        with open(docstore_path, "r") as f:
            data = json.load(f)
        
        # LlamaIndex stores data in different structures depending on version/persistence
        doc_data = data.get("docstore/data", data.get("docstore", {}).get("data", {}))
        ref_info = data.get("docstore/ref_doc_info", data.get("docstore", {}).get("ref_doc_info", {}))
        
        metrics["node_count"] = len(doc_data)
        metrics["file_count"] = len(ref_info)
        
        # 3. Resolve File Paths (Relative to project root if possible)
        file_list = []
        for info in ref_info.values():
            full_path_str = info.get("metadata", {}).get("file_path")
            if not full_path_str:
                continue
                
            full_path = Path(full_path_str).resolve()
            
            if project_path:
                try:
                    clean_proj = Path(project_path).resolve()
                    rel = os.path.relpath(str(full_path), str(clean_proj))
                    if rel.startswith(".."):
                        file_list.append(full_path.name)
                    else:
                        file_list.append(rel)
                except (ValueError, Exception):
                    file_list.append(full_path.name)
            else:
                file_list.append(full_path.name)
        
        metrics["files"] = sorted(list(set(file_list)))
        
    except Exception as e:
        print(f"Error calculating metrics for {project_name}: {e}")
        metrics["error"] = str(e)

    return metrics

def print_index_report(project_name: str):
    """CLI helper to print a pretty report, similar to the old stats.py."""
    metrics = get_index_metrics(project_name)
    
    if not metrics["exists"]:
        print(f"Error: No index found for project '{project_name}'.")
        return

    print(f"\n{'='*40}")
    print(f" AETHER INDEX REPORT: {project_name}")
    print(f"{'='*40}")
    print(f" Physical Size:  {metrics['total_size_kb']:.2f} KB")
    print(f" Total Files:    {metrics['file_count']}")
    print(f" Total Nodes:    {metrics['node_count']}")
    print(f" RAM Usage:      {metrics['ram_usage_mb']} MB")
    print(f"\n Indexed Files:")
    for f in metrics['files']:
        print(f"  - {f}")
    print(f"{'='*40}\n")

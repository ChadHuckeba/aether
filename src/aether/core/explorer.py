import os
from pathlib import Path
from typing import Dict, Any, List, Optional

def browse_directory(path: Optional[str], safe_root: Path) -> Dict[str, Any]:
    """
    Safely browses a directory, providing traversal protection.
    Returns a dict with directory info or error message.
    """
    current_safe_root = safe_root.resolve()

    if not path or path == "undefined":
        path = str(current_safe_root)
    
    try:
        requested_path = Path(path).resolve()
    except Exception as e:
        return {"error": f"Invalid path: {str(e)}", "current": str(current_safe_root)}
    
    # Path Traversal Protection
    if not str(requested_path).startswith(str(current_safe_root)):
        return {"error": "Access denied: Path outside safe root", "current": str(current_safe_root)}

    if not requested_path.exists():
        return {"error": "Path does not exist", "current": str(requested_path)}
    
    dirs = []
    try:
        for item in requested_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                dirs.append(item.name)
    except Exception as e:
        return {"error": str(e)}

    return {
        "current": str(requested_path).replace("\\", "/"),
        "parent": str(requested_path.parent).replace("\\", "/") if requested_path != current_safe_root else None,
        "directories": sorted(dirs)
    }

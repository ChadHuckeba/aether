import json
import os
from pathlib import Path
from typing import Dict, List
from aether.core.config import PROJECTS_FILE

def load_projects() -> Dict[str, str]:
    """Load projects from the project registry file."""
    # Path logic: aether/src/aether/core/projects.py -> parent(core) -> parent(aether) -> parent(src) = Root
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
    
    vanguard_path = os.getenv("PROJECT_PATH")
    if not vanguard_path:
        # Fallback for local development structure
        potential_vanguard = PROJECT_ROOT.parent / "vanguard"
        vanguard_path = str(potential_vanguard.resolve()) if potential_vanguard.exists() else "Unknown"

    default = {
        "Vanguard": vanguard_path.replace("\\", "/"),
        "Aether": str(PROJECT_ROOT).replace("\\", "/")
    }

    if not PROJECTS_FILE.exists():
        save_projects(default)
        return default
    try:
        with open(PROJECTS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default

def save_projects(data: Dict[str, str]):
    """Save projects to the project registry file."""
    with open(PROJECTS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Global Registry State (will be managed by the server but powered by these functions)
def get_project_list(projects: Dict[str, str]) -> List[Dict[str, str]]:
    """Format projects for API responses."""
    return [{"name": k, "path": v} for k, v in projects.items()]

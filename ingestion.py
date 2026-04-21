import os
import sys
from pathlib import Path

# Add src to path for discoverability
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from aether.core.ingest import sync_local_dir

if __name__ == "__main__":
    project_path = os.getenv("PROJECT_PATH")
    project_name = os.getenv("PROJECT_NAME")
    if not project_path:
        print("Error: PROJECT_PATH not found in .env")
    else:
        sync_local_dir(project_path, project_name)

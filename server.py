import sys
from pathlib import Path

# Add src to path for discoverability
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

if __name__ == "__main__":
    import uvicorn
    # The app is now located in aether.api.app
    uvicorn.run("aether.api.app:app", host="127.0.0.1", port=8000, reload=True)

import os
import json
import asyncio
import gc
import psutil
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from llama_index.core import StorageContext, load_index_from_storage
from ingestion import sync_local_dir_custom
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 1. Configuration Centralization
from config import SAFE_ROOT, PROJECTS_FILE, REQUIRED_EXTS, get_storage_path
from stats_engine import get_index_metrics
from ui_templates import get_dashboard_html, get_manage_html

from contextlib import asynccontextmanager

# --- Lifespan Management ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    if not os.getenv("GEMINI_API_KEY"):
        print("\n" + "!"*60)
        print(" CRITICAL ERROR: GEMINI_API_KEY is not set in .env")
        print(" The server will start, but queries and ingestion will fail.")
        print("!"*60 + "\n")
    
    restart_watcher()
    yield
    # Shutdown logic
    if observer:
        observer.stop()
        observer.join()

app = FastAPI(title="Aether Context API", lifespan=lifespan)

# --- Global State & Persistence ---

def load_projects():
    vanguard_path = os.getenv("PROJECT_PATH")
    if not vanguard_path:
        # Fallback for local development structure
        potential_vanguard = Path(__file__).parent.parent / "vanguard"
        vanguard_path = str(potential_vanguard.resolve()) if potential_vanguard.exists() else "Unknown"

    default = {
        "Vanguard": vanguard_path.replace("\\", "/"),
        "Aether": str(Path(__file__).parent.absolute()).replace("\\", "/")
    }
    if not os.path.exists(PROJECTS_FILE):
        save_projects(default)
        return default
    try:
        with open(PROJECTS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default

def save_projects(data):
    with open(PROJECTS_FILE, "w") as f:
        json.dump(data, f, indent=4)

PROJECTS = load_projects()
active_project = "Vanguard"
sync_status = {"status": "idle", "last_sync": "Never", "auto_sync": True}
_cached_index = None
_stats_cache = {} 

# --- Helpers ---

def get_storage_dir(project_name):
    return str(get_storage_path(project_name))

async def get_index():
    global _cached_index
    if _cached_index is not None:
        return _cached_index

    storage_dir = get_storage_dir(active_project)
    docstore_path = os.path.join(storage_dir, "docstore.json")
    
    if not os.path.exists(docstore_path):
        raise HTTPException(status_code=404, detail=f"No index found for {active_project}. Please click Synchronize.")
    
    try:
        def _load():
            sc = StorageContext.from_defaults(persist_dir=storage_dir)
            return load_index_from_storage(sc)
        
        _cached_index = await asyncio.to_thread(_load)
        return _cached_index
    except Exception as e:
        print(f"Error loading index: {e}")
        raise HTTPException(status_code=500, detail="Failed to load index storage. It might be corrupted.")

async def run_ingestion():
    global sync_status, _cached_index
    if sync_status["status"] == "syncing":
        return
    sync_status["status"] = "syncing"
    try:
        path = PROJECTS[active_project]
        storage_dir = get_storage_dir(active_project)
        await asyncio.to_thread(sync_local_dir_custom, path, storage_dir)
        _cached_index = None 
        from datetime import datetime
        sync_status["last_sync"] = datetime.now().strftime("%H:%M:%S")
        sync_status["status"] = "idle"
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        sync_status["status"] = f"error: {str(e)}"


# --- Watcher Logic ---
class ProjectWatcher(FileSystemEventHandler):
    def __init__(self, loop):
        self.loop = loop
        self.last_triggered = 0
        self.debounce_seconds = 5

    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Extension Filter
        ext = Path(event.src_path).suffix.lower()
        if ext not in REQUIRED_EXTS:
            return

        if any(x in event.src_path for x in [".git", "__pycache__", "storage", ".venv"]):
            return
        
        current_time = time.time()
        if current_time - self.last_triggered > self.debounce_seconds:
            self.last_triggered = current_time
            print(f"Auto-sync triggered by: {event.src_path}")
            asyncio.run_coroutine_threadsafe(run_ingestion(), self.loop)

observer = None

def restart_watcher():
    global observer
    if observer:
        try:
            observer.stop()
            observer.join()
        except:
            pass
    
    project_path = PROJECTS.get(active_project)
    if project_path and os.path.exists(project_path) and sync_status["auto_sync"]:
        observer = Observer()
        handler = ProjectWatcher(asyncio.get_event_loop())
        observer.schedule(handler, project_path, recursive=True)
        observer.start()
        print(f"Watching {active_project} at {project_path}")

@app.on_event("startup")
async def startup_event():
    restart_watcher()

@app.on_event("shutdown")
async def shutdown_event():
    if observer:
        observer.stop()
        observer.join()

# --- API ENDPOINTS ---

class QueryRequest(BaseModel):
    prompt: str

class QueryResponse(BaseModel):
    response: str

class SwitchRequest(BaseModel):
    name: str

class ProjectConfig(BaseModel):
    name: str
    path: str

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    try:
        index = get_index()
        query_engine = index.as_query_engine(streaming=False)
        response = await query_engine.aquery(request.prompt)
        return QueryResponse(response=str(response))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/switch")
async def switch_project(request: SwitchRequest):
    global active_project, _cached_index
    if request.name not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")
    active_project = request.name
    _cached_index = None 
    gc.collect()
    restart_watcher()
    return {"active": active_project}

@app.get("/projects")
async def get_projects():
    return [{"name": k, "path": v} for k, v in PROJECTS.items()]

@app.post("/projects")
async def add_project_endpoint(request: ProjectConfig):
    global PROJECTS
    PROJECTS[request.name] = request.path
    save_projects(PROJECTS)
    return {"status": "added"}

@app.delete("/projects/{name}")
async def delete_project(name: str):
    global PROJECTS, active_project, _cached_index
    if name not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")
    
    del PROJECTS[name]
    save_projects(PROJECTS)
    
    if active_project == name:
        active_project = list(PROJECTS.keys())[0] if PROJECTS else "None"
        _cached_index = None
        restart_watcher()
    
    return {"status": "deleted"}

@app.get("/browse")
async def browse_fs(path: str = None):
    # Use environment or relative path if SAFE_ROOT isn't configured
    safe_root_str = os.getenv("AETHER_SAFE_ROOT", str(SAFE_ROOT))
    current_safe_root = Path(safe_root_str).resolve()

    if not path or path == "undefined":
        path = str(current_safe_root)
    
    requested_path = Path(path).resolve()
    
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

@app.post("/release")
async def release_memory():
    global _cached_index
    _cached_index = None
    gc.collect()
    return {"status": "released"}

@app.get("/stats")
async def get_stats():
    global _stats_cache
    try:
        if active_project not in PROJECTS:
            return {
                "error": f"Active project {active_project} not found in registry",
                "available_projects": list(PROJECTS.keys())
            }

        project_path = PROJECTS.get(active_project)
        storage_dir = Path(get_storage_dir(active_project))
        docstore_path = storage_dir / "docstore.json"
        
        # --- Optimized Cache Check ---
        current_mtime = docstore_path.stat().st_mtime if docstore_path.exists() else 0
        cache = _stats_cache.get(active_project, {"mtime": -1, "data": None})
        
        if cache["mtime"] == current_mtime and cache["data"] is not None:
            stats_data = cache["data"]
        else:
            # Rebuild Cache using shared engine
            stats_data = get_index_metrics(active_project, project_path)
            _stats_cache[active_project] = {"mtime": current_mtime, "data": stats_data}
        
        # Prepare Response (Dynamic fields that change frequently)
        final_data = stats_data.copy()
        final_data["ram_usage_mb"] = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
        final_data["is_loaded"] = _cached_index is not None
        final_data["sync_status"] = sync_status
        final_data["available_projects"] = list(PROJECTS.keys())
        return final_data

    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in get_stats: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def trigger_ingest(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_ingestion)
    return {"status": "started"}

# --- PAGES ---

@app.get("/", response_class=HTMLResponse)
async def dashboard_page():
    return get_dashboard_html(active_project)

@app.get("/manage", response_class=HTMLResponse)
async def manage_page():
    return get_manage_html()

if __name__ == "__main__":
    import uvicorn
    # Security: Bind to 127.0.0.1 to prevent external network access
    uvicorn.run(app, host="127.0.0.1", port=8000)

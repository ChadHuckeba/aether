import aether.core.config
import os
import gc
import psutil
import asyncio
import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# 1. Configuration & Core Modules
from aether.core.config import SAFE_ROOT, PROJECTS_FILE, REQUIRED_EXTS, get_storage_path
from aether.core.projects import load_projects, save_projects, get_project_list
from aether.core.stats import get_index_metrics
from aether.core.engine import get_index, run_ingestion
from aether.core.watcher import setup_watcher
from aether.core.explorer import browse_directory
from aether.ui.templates import get_dashboard_html, get_manage_html

# --- Global State ---
logger = logging.getLogger("aether.api")
PROJECTS = load_projects()
active_project = list(PROJECTS.keys())[0] if PROJECTS else "None"
sync_status = {
    "status": "idle",
    "last_sync": "Never",
    "auto_sync": False,
    "pending_changes": False,
    "last_ingested": None
}
_cached_index = None
_stats_cache = {}
observer = None

def get_project_path(name: str) -> Optional[str]:
    entry = PROJECTS.get(name)
    if isinstance(entry, dict):
        return entry.get("path")
    return entry

def mark_pending_changes():
    global sync_status
    sync_status["pending_changes"] = True
    logger.info(f"Pending changes flagged by watcher callback for project: {active_project}")

# --- Lifespan Management ---

def restart_watcher():
    global observer
    if observer:
        try:
            observer.stop()
            observer.join()
        except:
            pass
    
    project_path = get_project_path(active_project)
    if project_path and os.path.exists(project_path):
        observer = setup_watcher(
            path=project_path,
            loop=asyncio.get_event_loop(),
            on_modified_callback=trigger_auto_sync,
            required_exts=REQUIRED_EXTS,
            auto_sync=sync_status["auto_sync"],
            on_change_detected_callback=mark_pending_changes
        )
        if observer:
            logger.info(f"Watching {active_project} at {project_path} (auto_sync={sync_status['auto_sync']})")

async def trigger_auto_sync():
    """Callback for watcher."""
    await run_ingestion_task()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global PROJECTS, sync_status
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("CRITICAL ERROR: GEMINI_API_KEY is not set.")
    
    # Read last_ingested on startup
    active_entry = PROJECTS.get(active_project)
    if isinstance(active_entry, dict):
        sync_status["last_ingested"] = active_entry.get("last_ingested")
    
    restart_watcher()
    yield
    if observer:
        observer.stop()
        observer.join()

app = FastAPI(title="Aether Context Engine", lifespan=lifespan)

# --- Core Task Runners ---

async def run_ingestion_task():
    global sync_status, _cached_index
    if sync_status["status"] == "syncing":
        return
        
    sync_status["status"] = "syncing"
    try:
        path = get_project_path(active_project)
        exclude_dirs = []
        if active_project in PROJECTS:
            entry = PROJECTS[active_project]
            if isinstance(entry, dict):
                exclude_dirs = entry.get("exclude_dirs", [])
        result = await run_ingestion(active_project, path, exclude_dirs)
        sync_status.update(result)
        _cached_index = None # Invalidate cache
        
        # Reset pending changes
        sync_status["pending_changes"] = False
        
        # Get UTC ISO 8601 timestamp
        from datetime import datetime
        utc_ts = datetime.utcnow().isoformat() + "Z"
        sync_status["last_ingested"] = utc_ts
        
        # Update projects.json entry
        if active_project in PROJECTS:
            entry = PROJECTS[active_project]
            if isinstance(entry, dict):
                entry["last_ingested"] = utc_ts
            else:
                PROJECTS[active_project] = {"path": entry, "last_ingested": utc_ts}
            save_projects(PROJECTS)
            
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        sync_status["status"] = f"error: {str(e)}"

# --- API Endpoints ---

class QueryRequest(BaseModel):
    prompt: str

class SwitchRequest(BaseModel):
    name: str

class ProjectConfig(BaseModel):
    name: str
    path: str

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    global _cached_index
    try:
        if _cached_index is None:
            _cached_index = await get_index(active_project)
            
        query_engine = _cached_index.as_query_engine(streaming=False)
        response = await query_engine.aquery(request.prompt)
        return {"response": str(response)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/switch")
async def switch_project(request: SwitchRequest):
    global active_project, _cached_index, sync_status
    if request.name not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")
    
    active_project = request.name
    _cached_index = None 
    gc.collect()
    
    # Read last_ingested for the new active project
    active_entry = PROJECTS.get(active_project)
    if isinstance(active_entry, dict):
        sync_status["last_ingested"] = active_entry.get("last_ingested")
    else:
        sync_status["last_ingested"] = None
    sync_status["pending_changes"] = False
    
    restart_watcher()
    return {"active": active_project}

@app.get("/projects")
async def get_projects_endpoint():
    return [{"name": k, "path": (v.get("path") if isinstance(v, dict) else v)} for k, v in PROJECTS.items()]

@app.post("/projects")
async def add_project_endpoint(request: ProjectConfig):
    global PROJECTS
    PROJECTS[request.name] = {"path": request.path, "last_ingested": None, "exclude_dirs": []}
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
async def browse_fs(path: Optional[str] = None):
    return browse_directory(path, SAFE_ROOT)

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
            return {"error": "No active project", "available_projects": list(PROJECTS.keys())}

        project_path = get_project_path(active_project)
        storage_dir = get_storage_path(active_project)
        docstore_path = storage_dir / "docstore.json"
        
        current_mtime = docstore_path.stat().st_mtime if docstore_path.exists() else 0
        cache = _stats_cache.get(active_project, {"mtime": -1, "data": None})
        
        if cache["mtime"] == current_mtime and cache["data"] is not None:
            stats_data = cache["data"]
        else:
            stats_data = get_index_metrics(active_project, project_path)
            _stats_cache[active_project] = {"mtime": current_mtime, "data": stats_data}
        
        final_data = stats_data.copy()
        final_data["ram_usage_mb"] = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
        final_data["is_loaded"] = _cached_index is not None
        final_data["sync_status"] = sync_status
        final_data["available_projects"] = list(PROJECTS.keys())
        final_data["project_path"] = project_path
        return final_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def trigger_ingest(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_ingestion_task)
    return {"status": "started"}

@app.get("/", response_class=HTMLResponse)
async def dashboard_page():
    return get_dashboard_html(active_project)

@app.get("/manage", response_class=HTMLResponse)
async def manage_page():
    return get_manage_html()

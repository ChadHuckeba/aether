import os
import json
import asyncio
import gc
import psutil
import time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from ingestion import sync_local_dir_custom
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 1. Environment and Path Setup
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# 2. Global Settings
SAFE_ROOT = Path("G:/code/SurvivalStack").resolve()

Settings.llm = GoogleGenAI(
    model="gemini-3-flash-preview", 
    api_key=os.getenv("GEMINI_API_KEY")
)
Settings.embed_model = GoogleGenAIEmbedding(
    model_name="models/gemini-embedding-001", 
    api_key=os.getenv("GEMINI_API_KEY")
)

app = FastAPI(title="Aether Context API")

# --- Global State & Persistence ---
PROJECTS_FILE = "projects.json"

def load_projects():
    default = {
        "Vanguard": os.getenv("PROJECT_PATH", "Unknown"),
        "Aether": str(Path(__file__).parent.absolute()).replace("\\", "/")
    }
    if not os.path.exists(PROJECTS_FILE):
        save_projects(default)
        return default
    with open(PROJECTS_FILE, "r") as f:
        return json.load(f)

def save_projects(data):
    with open(PROJECTS_FILE, "w") as f:
        json.dump(data, f, indent=4)

PROJECTS = load_projects()
active_project = "Vanguard"
sync_status = {"status": "idle", "last_sync": "Never", "auto_sync": True}
_cached_index = None
REQUIRED_EXTS = [".py", ".md", ".ps1", ".txt", ".json", ".toml", ".yaml", ".yml"]

# --- Helpers ---

def get_storage_dir(project_name):
    folder = project_name.lower().replace(" ", "_")
    path = Path("./storage") / folder
    path.mkdir(parents=True, exist_ok=True)
    return str(path)

def get_index():
    global _cached_index
    if _cached_index is not None:
        return _cached_index

    storage_dir = get_storage_dir(active_project)
    if not os.path.exists(os.path.join(storage_dir, "docstore.json")):
        raise HTTPException(status_code=500, detail=f"No index found for {active_project}. Please click Synchronize.")
    
    storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
    _cached_index = load_index_from_storage(storage_context)
    return _cached_index

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
    try:
        if active_project not in PROJECTS:
            return {
                "error": f"Active project {active_project} not found in registry",
                "available_projects": list(PROJECTS.keys())
            }

        project_path = PROJECTS.get(active_project)
        storage_dir = Path(get_storage_dir(active_project))
        ram_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        
        file_list = []
        node_count = 0
        total_size_kb = 0
        file_count = 0
        
        if storage_dir.exists() and (storage_dir / "docstore.json").exists():
            try:
                with open(storage_dir / "docstore.json", "r") as f:
                    data = json.load(f)
                
                # Handling both nested and flat docstore structures
                doc_data = data.get("docstore/data", data.get("docstore", {}).get("data", {}))
                ref_info = data.get("docstore/ref_doc_info", data.get("docstore", {}).get("ref_doc_info", {}))
                
                node_count = len(doc_data)
                file_count = len(ref_info)
                total_size_kb = round(sum(f.stat().st_size for f in storage_dir.glob("*.json")) / 1024, 2)
                
                for info in ref_info.values():
                    full_path = info.get("metadata", {}).get("file_path")
                    if full_path:
                        try:
                            # Sanitize paths for relpath
                            clean_full = Path(full_path).resolve()
                            clean_proj = Path(project_path).resolve()
                            file_list.append(os.path.relpath(str(clean_full), str(clean_proj)))
                        except:
                            file_list.append(full_path)
            except Exception as e:
                print(f"Error reading docstore: {e}")

        return {
            "node_count": node_count,
            "file_count": file_count,
            "total_size_kb": total_size_kb,
            "files": sorted(list(set(file_list))),
            "sync_status": sync_status,
            "project_name": active_project,
            "project_path": Path(project_path).name if project_path else "None",
            "is_loaded": _cached_index is not None,
            "ram_usage_mb": round(ram_mb, 2),
            "available_projects": list(PROJECTS.keys())
        }
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

COMMON_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono&display=swap');
body { font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f8fafc; overflow-x: hidden; }
.glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.1); }
.syncing { animation: pulse 2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
.mono { font-family: 'JetBrains Mono', monospace; }
.btn-primary { background: white; color: #0f172a; font-weight: 700; transition: all 0.2s; border-radius: 1rem; }
.btn-primary:hover { background: #60a5fa; color: white; transform: translateY(-1px); }
.nav-link { color: #64748b; transition: all 0.2s; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; }
.nav-link:hover { color: #f8fafc; }
.nav-link.active { color: #60a5fa; border-bottom: 2px solid #60a5fa; }
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard_page():
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Aether Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>{COMMON_STYLE}</style>
    </head>
    <body class="p-8 min-h-screen relative text-slate-300">
        <div class="max-w-6xl mx-auto">
            <nav class="flex gap-8 mb-12 border-b border-white/5 pb-4">
                <a href="/" class="nav-link active">Status</a>
                <a href="/manage" class="nav-link">Project Registry</a>
            </nav>

            <header class="flex justify-between items-end mb-12">
                <div>
                    <h1 class="text-6xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-white to-slate-500">Aether</h1>
                    <p class="text-slate-500 text-sm mt-2 ml-1 italic tracking-widest uppercase">Universal Context Engine</p>
                </div>
                
                <div class="flex flex-col items-end gap-3">
                    <div class="text-[10px] uppercase tracking-widest text-slate-500 font-bold mr-2">Active Context</div>
                    <div class="group relative">
                        <button class="glass pl-4 pr-10 py-2 rounded-full text-sm font-semibold flex items-center gap-2 hover:border-blue-500/50 transition-all">
                            <span class="w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]"></span>
                            <span id="project-label" class="text-blue-100 font-bold text-sm">{active_project}</span>
                            <svg class="w-4 h-4 absolute right-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </button>
                        <div class="absolute right-0 top-full w-56 pt-2 opacity-0 group-hover:opacity-100 transition-all pointer-events-none group-hover:pointer-events-auto z-50">
                            <div class="glass rounded-2xl p-2 shadow-2xl border border-white/5 bg-slate-900/95">
                                <div class="px-3 py-2 text-[10px] text-slate-500 font-bold uppercase tracking-widest">Switch Project</div>
                                <div id="project-list"></div>
                                <div class="h-px bg-white/5 my-2 mx-2"></div>
                                <a href="/manage" class="w-full text-left px-3 py-2 text-xs text-blue-400 hover:text-white transition-colors italic block">Manage Projects</a>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div class="glass p-6 rounded-3xl">
                    <h3 class="text-slate-500 text-[10px] uppercase tracking-widest font-bold mb-2">System</h3>
                    <div id="status-badge" class="flex items-center gap-2">
                        <span id="status-dot" class="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span id="status-text" class="text-sm font-medium text-emerald-400 uppercase tracking-tighter">Ready</span>
                    </div>
                </div>
                <div class="glass p-6 rounded-3xl relative overflow-hidden">
                    <h3 class="text-slate-500 text-[10px] uppercase tracking-widest font-bold mb-2">Memory Use</h3>
                    <div class="flex items-center justify-between">
                        <p id="ram-status" class="text-2xl font-bold italic mono">--</p>
                        <button onclick="releaseRAM()" class="text-[10px] text-slate-500 hover:text-white underline">Purge</button>
                    </div>
                    <div id="ram-pulse" class="absolute bottom-0 left-0 h-1 bg-blue-500 transition-all duration-1000" style="width: 0%"></div>
                </div>
                <div class="glass p-6 rounded-3xl text-center">
                    <h3 class="text-slate-500 text-[10px] uppercase tracking-widest font-bold mb-2 text-left">Source Files</h3>
                    <p id="stat-files" class="text-3xl font-bold italic mono">--</p>
                </div>
                <div class="glass p-6 rounded-3xl text-center">
                    <h3 class="text-slate-500 text-[10px] uppercase tracking-widest font-bold mb-2 text-left">Nodes</h3>
                    <p id="stat-nodes" class="text-3xl font-bold italic mono text-blue-400">--</p>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-20">
                <div class="lg:col-span-2 glass rounded-[2rem] overflow-hidden">
                    <div class="p-8 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                        <div>
                            <h2 class="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                                Knowledge Base 
                                <span class="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full font-mono">./<span id="project-path-display">--</span></span>
                            </h2>
                        </div>
                        <button id="sync-btn" onclick="triggerSync()" class="bg-white text-slate-900 hover:bg-blue-400 hover:text-white transition-all px-8 py-3 rounded-2xl font-bold text-sm shadow-xl">
                            Synchronize
                        </button>
                    </div>
                    <div id="file-list" class="p-6 max-h-[500px] overflow-y-auto space-y-1"></div>
                </div>

                <div class="space-y-6">
                    <div class="glass rounded-[2rem] p-8">
                        <h2 class="text-lg font-bold mb-6 flex items-center gap-2 text-white">
                            <span class="w-1 h-4 bg-blue-500 rounded-full"></span>
                            Operations
                        </h2>
                        <div class="space-y-6">
                            <div>
                                <p class="text-[10px] text-slate-500 uppercase font-black mb-2">Last Update</p>
                                <p id="last-sync" class="text-sm mono text-slate-300">--</p>
                            </div>
                            <button onclick="testQuery()" class="w-full py-3 rounded-2xl bg-blue-500/10 text-blue-400 text-xs font-bold hover:bg-blue-500/20 transition-all border border-blue-500/20">
                                Ping Engine
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <footer class="absolute bottom-8 right-8 text-right">
                <p class="text-[10px] text-slate-600 font-bold uppercase tracking-widest mb-1 text-[8px]">Developed By</p>
                <p class="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-200 to-slate-500 tracking-tight italic">SurvivalStack</p>
            </footer>
        </div>

        <script>
            async function switchProject(name) {{
                await fetch('/switch', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name: name }})
                }});
                updateStats();
            }}

            async function releaseRAM() {{
                await fetch('/release', {{ method: 'POST' }});
                updateStats();
            }}

            async function testQuery() {{
                await fetch('/query', {{ 
                    method: 'POST', 
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ prompt: 'ping' }})
                }});
                updateStats();
            }}

            async function updateStats() {{
                try {{
                    const res = await fetch('/stats');
                    const data = await res.json();
                    
                    document.getElementById('stat-nodes').innerText = data.node_count;
                    document.getElementById('stat-files').innerText = data.file_count;
                    document.getElementById('last-sync').innerText = data.sync_status.last_sync;
                    document.getElementById('project-label').innerText = data.project_name;
                    document.getElementById('project-path-display').innerText = data.project_path;

                    const rs = document.getElementById('ram-status');
                    rs.innerText = data.ram_usage_mb + ' MB';
                    rs.className = data.is_loaded ? 'text-3xl font-bold italic mono text-blue-400' : 'text-3xl font-bold italic mono text-slate-700';
                    document.getElementById('ram-pulse').style.width = data.is_loaded ? '100%' : '0%';

                    const pList = document.getElementById('project-list');
                    pList.innerHTML = data.available_projects.map(p => `
                        <button onclick="switchProject('${{p}}')" class="w-full text-left px-3 py-2 text-sm rounded-xl transition-colors ${{p === data.project_name ? 'text-blue-400 bg-blue-500/10 font-bold' : 'text-slate-400 hover:text-white hover:bg-white/5'}}">
                            ${{p}}
                        </button>
                    `).join('');

                    const list = document.getElementById('file-list');
                    list.innerHTML = data.files.map(f => `
                        <div class="flex items-center gap-4 p-3 rounded-2xl group border border-transparent hover:border-white/5 transition-all">
                            <div class="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-[8px] font-black mono text-slate-500 group-hover:text-blue-400">
                                ${{f.split('.').pop().toUpperCase()}}
                            </div>
                            <span class="text-sm font-medium text-slate-400 group-hover:text-white truncate italic tracking-tight">${{f}}</span>
                        </div>
                    `).join('');
                }} catch(e) {{ console.error(e); }}
            }}

            async function triggerSync() {{
                await fetch('/ingest', {{ method: 'POST' }});
                updateStats();
            }}

            setInterval(updateStats, 3000);
            updateStats();
        </script>
    </body>
    </html>
    """

@app.get("/manage", response_class=HTMLResponse)
async def manage_page():
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Aether | Project Registry</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            {COMMON_STYLE}
            .modal-overlay {{ background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); }}
            .explorer-item {{ transition: all 0.2s; }}
            .explorer-item:hover {{ background: rgba(255,255,255,0.05); color: #60a5fa; }}
        </style>
    </head>
    <body class="p-8 min-h-screen text-slate-300">
        <div class="max-w-6xl mx-auto">
            <nav class="flex gap-8 mb-12 border-b border-white/5 pb-4">
                <a href="/" class="nav-link">Status</a>
                <a href="/manage" class="nav-link active">Project Registry</a>
            </nav>

            <header class="mb-12">
                <h1 class="text-4xl font-bold text-white tracking-tight">Project Registry</h1>
                <p class="text-slate-500 mt-2 text-sm italic">Configure and manage Aether project contexts.</p>
            </header>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-12">
                <div class="lg:col-span-2 space-y-4" id="project-cards"></div>

                <div class="glass rounded-[2rem] p-8 h-fit sticky top-8">
                    <h2 class="text-xl font-bold text-white mb-6 tracking-tight">Register New Engine</h2>
                    <div class="space-y-4">
                        <div>
                            <label class="text-[10px] uppercase font-bold text-slate-500 ml-1">Context Name</label>
                            <input id="new-name" type="text" placeholder="Example Project Name" class="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition-all mt-1">
                        </div>
                        <div>
                            <label class="text-[10px] uppercase font-bold text-slate-500 ml-1">Path</label>
                            <div class="flex gap-2 mt-1">
                                <input id="new-path" type="text" placeholder="/path/to/source" class="flex-1 bg-slate-900/50 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition-all">
                                <button onclick="openExplorer()" class="glass px-4 rounded-xl text-blue-400 hover:text-white transition-all text-xs font-bold">Browse</button>
                            </div>
                        </div>
                        <button onclick="handleAdd()" class="w-full btn-primary py-4 rounded-2xl text-sm shadow-xl mt-4">
                            Activate Context
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Explorer Modal -->
        <div id="explorer-modal" class="fixed inset-0 modal-overlay z-[100] hidden flex items-center justify-center p-8">
            <div class="glass w-full max-w-2xl rounded-[2rem] flex flex-col max-h-[80vh] border border-white/10 shadow-2xl">
                <div class="p-8 border-b border-white/5 flex justify-between items-center">
                    <div>
                        <h2 class="text-xl font-bold text-white">System Explorer</h2>
                        <p id="current-browse-path" class="text-xs text-slate-500 mono mt-1 truncate max-w-md">/Loading...</p>
                    </div>
                    <button onclick="closeExplorer()" class="text-slate-500 hover:text-white">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
                <div id="explorer-list" class="flex-1 overflow-y-auto p-4 space-y-1">
                    <!-- Folders here -->
                </div>
                <div class="p-6 border-t border-white/5 bg-white/[0.02] flex justify-between items-center">
                    <button onclick="navigateUp()" class="text-xs font-bold text-blue-400 hover:underline">↑ Up One Level</button>
                    <button onclick="selectCurrentFolder()" class="btn-primary px-8 py-3 rounded-xl text-xs">Select Folder</button>
                </div>
            </div>
        </div>

        <script>
            let currentPath = "";

            async function openExplorer() {{
                document.getElementById('explorer-modal').classList.remove('hidden');
                loadPath(currentPath || "G:/code/SurvivalStack");
            }}

            function closeExplorer() {{
                document.getElementById('explorer-modal').classList.add('hidden');
            }}

            async function loadPath(path) {{
                const res = await fetch(`/browse?path=${{encodeURIComponent(path)}}`);
                const data = await res.json();
                if(data.error) return alert(data.error);

                currentPath = data.current;
                document.getElementById('current-browse-path').innerText = currentPath;
                
                const container = document.getElementById('explorer-list');
                container.innerHTML = data.directories.map(d => `
                    <div onclick="loadPath('${{currentPath}}/${{d}}')" class="explorer-item flex items-center gap-3 p-3 rounded-xl cursor-pointer">
                        <svg class="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path></svg>
                        <span class="text-sm font-medium tracking-tight">${{d}}</span>
                    </div>
                `).join('');
            }}

            function navigateUp() {{
                const parts = currentPath.split('/');
                parts.pop();
                loadPath(parts.join('/') || 'C:/');
            }}

            function selectCurrentFolder() {{
                document.getElementById('new-path').value = currentPath;
                closeExplorer();
            }}

            async function handleAdd() {{
                const name = document.getElementById('new-name').value;
                const path = document.getElementById('new-path').value;
                if(!name || !path) return alert("All fields required");
                
                await fetch('/projects', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name, path }})
                }});
                location.reload();
            }}

            async function deleteProject(name) {{
                if(!confirm(`Delete ${{name}} Context?`)) return;
                await fetch(`/projects/${{name}}`, {{ method: 'DELETE' }});
                loadRegistry();
            }}

            async function updateProject(oldName) {{
                const newPath = prompt("New Source Path:", "G:/...");
                if(!newPath) return;
                await fetch('/projects', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name: oldName, path: newPath }})
                }});
                loadRegistry();
            }}

            async function loadRegistry() {{
                try {{
                    const res = await fetch('/projects');
                    const data = await res.json();
                    const container = document.getElementById('project-cards');
                    
                    container.innerHTML = data.map(p => `
                        <div class="glass p-8 rounded-[2rem] flex justify-between items-center group hover:border-white/20 transition-all">
                            <div>
                                <h3 class="text-xl font-bold text-white mb-1 tracking-tight">${{p.name}}</h3>
                                <p class="text-[10px] text-slate-500 mono bg-slate-900/50 px-2 py-0.5 rounded-full inline-block mt-2">${{p.path}}</p>
                            </div>
                            <div class="flex gap-6 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onclick="updateProject('${{p.name}}')" class="text-[10px] font-bold uppercase tracking-widest text-blue-400 hover:text-white transition-colors">Modify Path</button>
                                <button onclick="deleteProject('${{p.name}}')" class="text-[10px] font-bold uppercase tracking-widest text-red-400 hover:text-white transition-colors">Discard</button>
                            </div>
                        </div>
                    `).join('');
                }} catch (e) {{ console.error(e); }}
            }}

            loadRegistry();
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    # Security: Bind to 127.0.0.1 to prevent external network access
    uvicorn.run(app, host="127.0.0.1", port=8000)

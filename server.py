import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from ingestion import sync_local_dir

# 1. Environment and Path Setup
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# 2. Global Settings
Settings.llm = GoogleGenAI(
    model="gemini-3-flash-preview", 
    api_key=os.getenv("GEMINI_API_KEY")
)
Settings.embed_model = GoogleGenAIEmbedding(
    model_name="models/gemini-embedding-001", 
    api_key=os.getenv("GEMINI_API_KEY")
)

app = FastAPI(title="Aether Context API")

class QueryRequest(BaseModel):
    prompt: str

class QueryResponse(BaseModel):
    response: str

# Track sync status
sync_status = {"status": "idle", "last_sync": "Never"}
PROJECT_NAME = os.getenv("PROJECT_NAME", "Project")
PROJECT_PATH = os.getenv("PROJECT_PATH", "Unknown")
# Short display path (just the folder name)
DISPLAY_PATH = Path(PROJECT_PATH).name if PROJECT_PATH != "Unknown" else "Unknown"

def get_index():
    storage_dir = "./storage"
    if not os.path.exists(storage_dir):
        raise HTTPException(status_code=500, detail="Storage directory not found. Run ingestion.py first.")
    
    storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
    return load_index_from_storage(storage_context)

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    try:
        index = get_index()
        query_engine = index.as_query_engine(streaming=False)
        response = await query_engine.aquery(request.prompt)
        return QueryResponse(response=str(response))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    storage_path = Path("./storage")
    if not storage_path.exists():
        return {"error": "No storage found"}
    
    docstore_path = storage_path / "docstore.json"
    with open(docstore_path, "r") as f:
        data = json.load(f)
    
    doc_dict = data.get("docstore/data", {})
    ref_doc_info = data.get("docstore/ref_doc_info", {})
    
    # Calculate sizes
    total_size_kb = sum(f.stat().st_size for f in storage_path.glob("*.json")) / 1024
    
    files = []
    project_path = os.getenv("PROJECT_PATH", "")
    
    for doc_id, info in ref_doc_info.items():
        metadata = info.get("metadata", {})
        full_path = metadata.get("file_path") or metadata.get("file_name") or doc_id
        
        # Convert to relative path if possible
        try:
            if project_path and os.path.isabs(full_path):
                rel_path = os.path.relpath(full_path, project_path)
                files.append(rel_path)
            else:
                files.append(full_path)
        except ValueError:
            files.append(full_path)

    return {
        "node_count": len(doc_dict),
        "file_count": len(ref_doc_info),
        "total_size_kb": round(total_size_kb, 2),
        "files": sorted(list(set(files))),
        "sync_status": sync_status,
        "project_name": PROJECT_NAME,
        "project_path": DISPLAY_PATH
    }

async def run_ingestion():
    global sync_status
    sync_status["status"] = "syncing"
    try:
        project_path = os.getenv("PROJECT_PATH")
        if not project_path:
            raise ValueError("PROJECT_PATH not set in .env")
        # Run in a thread to not block the event loop if it's heavy
        await asyncio.to_thread(sync_local_dir, project_path)
        from datetime import datetime
        sync_status["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sync_status["status"] = "idle"
    except Exception as e:
        sync_status["status"] = f"error: {str(e)}"

@app.post("/ingest")
async def trigger_ingest(background_tasks: BackgroundTasks):
    if sync_status["status"] == "syncing":
        return {"message": "Already syncing"}
    background_tasks.add_task(run_ingestion)
    return {"message": "Ingestion started"}

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Aether Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono&display=swap');
            body {{ font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f8fafc; overflow-x: hidden; }}
            .glass {{ background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.1); }}
            .syncing {{ animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }}
            @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .5; }} }}
            .mono {{ font-family: 'JetBrains Mono', monospace; }}
        </style>
    </head>
    <body class="p-8 min-h-screen relative">
        <div class="max-w-6xl mx-auto">
            <header class="flex justify-between items-end mb-12">
                <div>
                    <h1 class="text-6xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-white to-slate-500">Aether</h1>
                    <p class="text-slate-500 text-sm mt-2 ml-1">Universal Context Engine</p>
                </div>
                
                <div class="flex flex-col items-end gap-3">
                    <div class="text-[10px] uppercase tracking-widest text-slate-500 font-bold mr-2">Active Context</div>
                    <div class="group relative">
                        <button class="glass pl-4 pr-10 py-2 rounded-full text-sm font-semibold flex items-center gap-2 hover:border-blue-500/50 transition-all">
                            <span class="w-2 h-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]"></span>
                            <span id="project-label" class="text-blue-100">{PROJECT_NAME}</span>
                            <svg class="w-4 h-4 absolute right-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </button>
                        <!-- Dropdown Placeholder -->
                        <div class="absolute right-0 mt-2 w-48 glass rounded-2xl p-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none group-hover:pointer-events-auto z-50">
                            <div class="px-3 py-2 text-[10px] text-slate-500 font-bold uppercase">Switch Project</div>
                            <div class="px-3 py-2 text-sm text-blue-400 font-medium bg-blue-500/10 rounded-xl mb-1">{PROJECT_NAME}</div>
                            <div class="px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 rounded-xl cursor-not-allowed">Add Project +</div>
                        </div>
                    </div>
                </div>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div class="glass p-6 rounded-3xl">
                    <h3 class="text-slate-500 text-[10px] uppercase tracking-widest font-bold mb-2">Status</h3>
                    <div id="status-badge" class="flex items-center gap-2">
                        <span id="status-dot" class="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span id="status-text" class="text-sm font-medium">Ready</span>
                    </div>
                </div>
                <div class="glass p-6 rounded-3xl">
                    <h3 class="text-slate-500 text-[10px] uppercase tracking-widest font-bold mb-2">Vector Nodes</h3>
                    <p id="stat-nodes" class="text-3xl font-bold italic mono">--</p>
                </div>
                <div class="glass p-6 rounded-3xl">
                    <h3 class="text-slate-500 text-[10px] uppercase tracking-widest font-bold mb-2">Source Files</h3>
                    <p id="stat-files" class="text-3xl font-bold italic mono">--</p>
                </div>
                <div class="glass p-6 rounded-3xl">
                    <h3 class="text-slate-500 text-[10px] uppercase tracking-widest font-bold mb-2">Index Size</h3>
                    <p id="stat-size" class="text-3xl font-bold italic mono text-blue-400">--</p>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-20">
                <div class="lg:col-span-2 glass rounded-[2rem] overflow-hidden">
                    <div class="p-8 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                        <div>
                            <h2 class="text-xl font-bold">Knowledge Base</h2>
                            <p class="text-xs text-slate-500 mt-1 mono truncate max-w-xs" id="project-path-display">./{DISPLAY_PATH}</p>
                        </div>
                        <button id="sync-btn" onclick="triggerSync()" class="bg-white text-slate-900 hover:bg-blue-400 hover:text-white transition-all px-8 py-3 rounded-2xl font-bold text-sm shadow-xl">
                            Synchronize
                        </button>
                    </div>
                    <div id="file-list" class="p-6 max-h-[500px] overflow-y-auto space-y-1">
                        <!-- Files populated here -->
                    </div>
                </div>

                <div class="space-y-6">
                    <div class="glass rounded-[2rem] p-8">
                        <h2 class="text-lg font-bold mb-6 flex items-center gap-2">
                            <span class="w-1 h-4 bg-blue-500 rounded-full"></span>
                            Operations
                        </h2>
                        <div class="space-y-6">
                            <div>
                                <p class="text-[10px] text-slate-500 uppercase font-black tracking-tighter mb-2">Last Update</p>
                                <p id="last-sync" class="text-sm mono text-slate-300">--</p>
                            </div>
                            <div>
                                <p class="text-[10px] text-slate-500 uppercase font-black tracking-tighter mb-2">Query Gateway</p>
                                <div class="flex items-center gap-2">
                                    <span class="px-2 py-1 rounded bg-blue-500/10 text-blue-400 text-[10px] mono">POST</span>
                                    <p class="text-sm mono text-slate-300">/query</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="p-8 rounded-[2rem] border border-blue-500/20 bg-blue-500/[0.02]">
                        <h3 class="text-blue-400 text-xs font-bold uppercase mb-2">Integration Pro-Tip</h3>
                        <p class="text-slate-400 text-xs leading-relaxed">
                            Aether works best when paired with Gemini CLI. Use the query endpoint to inject real-time code context into your prompts.
                        </p>
                    </div>
                </div>
            </div>

            <footer class="absolute bottom-8 right-8 text-right">
                <p class="text-[10px] text-slate-600 font-bold uppercase tracking-widest mb-1">Developed By</p>
                <p class="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-200 to-slate-500 tracking-tight italic">SurvivalStack</p>
            </footer>
        </div>

        <script>
            async function updateStats() {{
                const res = await fetch('/stats');
                const data = await res.json();
                
                document.getElementById('stat-nodes').innerText = data.node_count;
                document.getElementById('stat-files').innerText = data.file_count;
                document.getElementById('stat-size').innerText = data.total_size_kb + ' KB';
                document.getElementById('last-sync').innerText = data.sync_status.last_sync;
                document.getElementById('project-label').innerText = data.project_name;
                document.getElementById('project-path-display').innerText = './' + data.project_path;

                const statusText = document.getElementById('status-text');
                const statusDot = document.getElementById('status-dot');
                const btn = document.getElementById('sync-btn');

                if (data.sync_status.status === 'syncing') {{
                    statusText.innerText = 'Syncing...';
                    statusDot.className = 'w-2 h-2 rounded-full bg-blue-500 syncing';
                    btn.disabled = true;
                    btn.innerText = 'Wait...';
                    btn.className = 'bg-slate-800 text-slate-500 cursor-not-allowed px-8 py-3 rounded-2xl font-bold text-sm shadow-none';
                }} else {{
                    statusText.innerText = 'Ready';
                    statusDot.className = 'w-2 h-2 rounded-full bg-emerald-500';
                    btn.disabled = false;
                    btn.innerText = 'Synchronize';
                    btn.className = 'bg-white text-slate-900 hover:bg-blue-400 hover:text-white transition-all px-8 py-3 rounded-2xl font-bold text-sm shadow-xl';
                }}

                const list = document.getElementById('file-list');
                list.innerHTML = data.files.map(f => `
                    <div class="flex items-center gap-4 p-3 rounded-2xl hover:bg-white/[0.03] transition-colors group border border-transparent hover:border-white/5">
                        <div class="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-[10px] font-black mono text-slate-500 group-hover:text-blue-400 transition-colors">
                            ${{f.split('.').pop().toUpperCase()}}
                        </div>
                        <div class="flex flex-col">
                            <span class="text-sm font-medium text-slate-300 group-hover:text-white transition-colors truncate">
                                ${{f.split(/[\\\\/]/).pop()}}
                            </span>
                            <span class="text-[10px] text-slate-600 mono truncate max-w-[200px] md:max-w-md italic">
                                ${{f}}
                            </span>
                        </div>
                    </div>
                `).join('');
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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "storage_exists": os.path.exists("./storage")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "storage_exists": os.path.exists("./storage")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

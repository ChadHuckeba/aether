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
    for doc_id, info in ref_doc_info.items():
        metadata = info.get("metadata", {})
        files.append(metadata.get("file_name") or metadata.get("file_path") or doc_id)

    return {
        "node_count": len(doc_dict),
        "file_count": len(ref_doc_info),
        "total_size_kb": round(total_size_kb, 2),
        "files": sorted(list(set(files))),
        "sync_status": sync_status
    }

async def run_ingestion():
    global sync_status
    sync_status["status"] = "syncing"
    try:
        vanguard_path = os.getenv("VANGUARD_PATH")
        if not vanguard_path:
            raise ValueError("VANGUARD_PATH not set in .env")
        # Run in a thread to not block the event loop if it's heavy
        await asyncio.to_thread(sync_local_dir, vanguard_path)
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
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Aether Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
            body { font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f8fafc; }
            .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.1); }
            .syncing { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-5xl mx-auto">
            <header class="flex justify-between items-center mb-8">
                <div>
                    <h2 class="text-xs font-bold tracking-widest text-blue-500 uppercase mb-1">SurvivalStack</h2>
                    <h1 class="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">Aether</h1>
                    <p class="text-slate-400">Context Engine</p>
                </div>
                <div id="status-badge" class="px-4 py-2 rounded-full glass text-sm font-medium flex items-center gap-2">
                    <span id="status-dot" class="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span id="status-text">System Ready</span>
                </div>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="glass p-6 rounded-2xl">
                    <h3 class="text-slate-400 text-sm mb-1">Vector Nodes</h3>
                    <p id="stat-nodes" class="text-3xl font-bold">--</p>
                </div>
                <div class="glass p-6 rounded-2xl">
                    <h3 class="text-slate-400 text-sm mb-1">Source Files</h3>
                    <p id="stat-files" class="text-3xl font-bold">--</p>
                </div>
                <div class="glass p-6 rounded-2xl">
                    <h3 class="text-slate-400 text-sm mb-1">Index Size</h3>
                    <p id="stat-size" class="text-3xl font-bold">-- KB</p>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div class="lg:col-span-2 glass rounded-2xl overflow-hidden">
                    <div class="p-6 border-b border-white/10 flex justify-between items-center">
                        <h2 class="text-xl font-semibold">Indexed Knowledge</h2>
                        <button id="sync-btn" onclick="triggerSync()" class="bg-blue-600 hover:bg-blue-500 transition-colors px-6 py-2 rounded-xl font-medium shadow-lg shadow-blue-900/20">
                            Sync Vanguard
                        </button>
                    </div>
                    <div id="file-list" class="p-6 max-h-[400px] overflow-y-auto space-y-2">
                        <!-- Files populated here -->
                    </div>
                </div>

                <div class="glass rounded-2xl p-6">
                    <h2 class="text-xl font-semibold mb-4">Operations</h2>
                    <div class="space-y-4">
                        <div class="p-4 rounded-xl bg-white/5 border border-white/5">
                            <p class="text-xs text-slate-500 uppercase font-bold mb-1">Last Sync</p>
                            <p id="last-sync" class="text-sm">--</p>
                        </div>
                        <div class="p-4 rounded-xl bg-white/5 border border-white/5">
                            <p class="text-xs text-slate-500 uppercase font-bold mb-1">Endpoint</p>
                            <p class="text-sm font-mono text-blue-400">/query</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function updateStats() {
                const res = await fetch('/stats');
                const data = await res.json();
                
                document.getElementById('stat-nodes').innerText = data.node_count;
                document.getElementById('stat-files').innerText = data.file_count;
                document.getElementById('stat-size').innerText = data.total_size_kb;
                document.getElementById('last-sync').innerText = data.sync_status.last_sync;

                const statusText = document.getElementById('status-text');
                const statusDot = document.getElementById('status-dot');
                const btn = document.getElementById('sync-btn');

                if (data.sync_status.status === 'syncing') {
                    statusText.innerText = 'Syncing Knowledge...';
                    statusDot.className = 'w-2 h-2 rounded-full bg-blue-500 syncing';
                    btn.disabled = true;
                    btn.innerText = 'Syncing...';
                    btn.className = 'bg-slate-700 cursor-not-allowed px-6 py-2 rounded-xl font-medium';
                } else {
                    statusText.innerText = 'System Ready';
                    statusDot.className = 'w-2 h-2 rounded-full bg-emerald-500';
                    btn.disabled = false;
                    btn.innerText = 'Sync Vanguard';
                    btn.className = 'bg-blue-600 hover:bg-blue-500 transition-colors px-6 py-2 rounded-xl font-medium shadow-lg shadow-blue-900/20';
                }

                const list = document.getElementById('file-list');
                list.innerHTML = data.files.map(f => `
                    <div class="flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors group">
                        <div class="w-8 h-8 rounded bg-blue-500/10 flex items-center justify-center text-blue-400 text-xs font-bold">
                            ${f.split('.').pop().toUpperCase()}
                        </div>
                        <div class="text-sm text-slate-300 group-hover:text-white transition-colors truncate">
                            ${f}
                        </div>
                    </div>
                `).join('');
            }

            async function triggerSync() {
                await fetch('/ingest', { method: 'POST' });
                updateStats();
            }

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

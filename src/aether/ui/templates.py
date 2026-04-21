# ui_templates.py
from aether.core.config import SAFE_ROOT

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

def get_dashboard_html(active_project: str):
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
                            <span class="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full font-mono"><span id="project-path-display">--</span></span>
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
                            <span class="text-sm font-medium text-slate-400 group-hover:text-white truncate italic tracking-tight pr-1">${{f}}</span>
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

def get_manage_html():
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
                loadPath(currentPath);
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
                loadPath(parts.join('/') || '/');
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
                const newPath = prompt("New Source Path:", "{SAFE_ROOT}/...");
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

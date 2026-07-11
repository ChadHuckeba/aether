# SurvivalStack Session Onboarding Brief: Aether Context Engine
**Date:** May 23, 2026

This onboarding brief outlines the environment structure, current governance rules, system architecture, open backlog items, and directives for the Aether Context Engine following the session of May 23, 2026.

---

## 1. Environment Overview

Aether is integrated within the multi-repository SurvivalStack product line. Below is the mapping of active repositories sourced from `registry.json`:

| Product Line | Repository Name | Local Path | GitHub Repository | State |
| :--- | :--- | :--- | :--- | :--- |
| **Core** | `dotfiles` | `core/dotfiles` | `ChadHuckeba/Core-dotfiles` | Active |
| **Core** | `huckos` | `core/HuckOS.C-137` | `ChadHuckeba/Core-HuckOS.C-137` | Active |
| **SurvivalStack** | `vanguard` | `survivalstack/Vanguard` | `ChadHuckeba/SurvivalStack-Vanguard` | Active |
| **SurvivalStack** | `cairn` | `survivalstack/cairn` | `ChadHuckeba/SurvivalStack-Cairn` | Active |
| **SurvivalTools** | `aether` | `survivaltools/Aether` | `ChadHuckeba/SurvivalTools-Aether` | Active |
| **HoundStack** | `wallboard` | `houndstack/Wallboard` | `ChadHuckeba/HoundStack-Wallboard` | Active |

---

## 2. Active Governance Framework

Project governance is declared in `GEMINI.md` and coordinates local agent behavior with the Global Governance Architecture:

*   **Precedence Mandate**: Global Policy (`~/.gemini/GEMINI.md`) supersedes Local Policy (`GEMINI.md`). Local policies add project-specific mandates but cannot override global mandates.
*   **RAG-First Mandate**: AI agents MUST prioritize semantic codebase intelligence. Agents must use the `query_codebase` MCP tool before resorting to manual file-reading (`view_file` or `grep_search`).
*   **Documentation Impact Assessment (DIA)**: Any code modifications affecting `src/aether/core/watcher.py` or `src/aether/core/ingest.py` require a synchronized sibling update to `docs/ENGINE.md`.
*   **Telemetry Discipline**: All modules must initialize and use a hierarchical logger via `logging.getLogger("aether.<module>")`. Direct print statements for telemetry are strictly prohibited.
*   **Audit Notice**: Governance is currently under audit and hardening (Work Items 9 and 10 are pending).

---

## 3. Aether System — Current State

### 3.1 Architecture
Aether is an asynchronous codebase context and query engine constructed using FastAPI and LlamaIndex. It uses the Google Gemini API (`gemini-embedding-001`) to generate embeddings and represent codebase repositories semantically as vector indices.

### 3.2 API Endpoints
Aether exposes the following HTTP endpoints:
*   `GET /`: Serving the dashboard UI.
*   `GET /manage`: Serving the project management UI.
*   `GET /projects`: List all configured projects.
*   `POST /projects`: Add a new project config (`name`, `path`).
*   `DELETE /projects/{name}`: Delete a project configuration.
*   `POST /switch`: Switch the active project context (`name`).
*   `POST /query`: Query the active index via RAG (`prompt`).
*   `POST /ingest`: Trigger an asynchronous background ingestion/sync task.
*   `GET /stats`: Retrieve index size, file count, node list, memory metrics, and sync status.
*   `POST /release`: Release the vector index from RAM.
*   `GET /browse`: Interactive directory browser.

### 3.3 Ingestion Pipeline
The ingestion engine in `src/aether/core/ingest.py` orchestrates the local-to-storage synchronization:
*   **Document ID Mapping**: Structured to use `filename_as_id=True` on the `SimpleDirectoryReader` for stable document tracking.
*   **Targeted Exclusions**: Respects per-project directories listed under `exclude_dirs` in `projects.json`.
*   **Batch Quotas**: Counted and tracked via `embed_calls_used` to feed the daily limit counter.
*   **Incremental Recovery**: Employs incremental batch-level persistence (`index.storage_context.persist()`) inside both the full/initial indexing and refresh loop paths. This ensures that completed batches are saved immediately, preventing progress loss on rate-limit errors or timeouts.

### 3.4 sync_status Structure
The `/stats` response contains the following status metadata block:
*   `status`: Status of the current ingestion context (`idle`, `syncing`, `quota_exceeded`, or `error: <msg>`).
*   `last_sync`: ISO 8601 UTC timestamp of the last completed synchronization loop.
*   `auto_sync`: Boolean representing whether file changes trigger auto-ingestion (default: `False`).
*   `pending_changes`: Flagged `True` when file watch notifications occur but have not yet been synchronized.
*   `last_ingested`: ISO 8601 UTC timestamp of last ingestion completed.
*   `embed_calls_today`: Accumulation of embedding batches processed today.
*   `embed_limit`: Configured ceiling for daily embedding batches (default: `900`).
*   `embed_calls_used`: Count of embedding batches used in the most recent ingest run.

### 3.5 MCP Integration
Exposes FastMCP tools to client runtimes (e.g. `agy`):
*   `query_codebase(prompt)`: Ask questions against the active project index.
*   `refresh_index()`: Remote command triggering a background ingestion cycle.
*   *Note:* The MCP configuration resolves `AETHER_BASE_URL` to `http://127.0.0.1:8000` to resolve local network routing issues.

### 3.6 Current Index State
As of May 23, 2026, all four active projects have had their indices successfully built/refreshed, and `last_ingested` timestamps are fully populated in `data/projects.json`:
1.  **Vanguard** (Active, `/home/chadh/survivalstack/Vanguard`)
2.  **Aether** (Active, `/home/chadh/survivaltools/Aether`)
3.  **Wallboard** (Active, `/home/chadh/houndstack/Wallboard`)
4.  **HuckOS.C-137** (Active, `/home/chadh/core/HuckOS.C-137`)

### 3.7 Configuration Locations
*   **Config Registry**: `data/projects.json` (fallback defaults in `src/aether/core/projects.py`).
*   **Environment**: `.env` (contains API keys, port settings, and directories).
*   **Quota Ledger**: `data/quota.json` (tracks daily API batch usage).

---

## 4. Open Work Items

*   **Item 8: Write Aether documentation (ENGINE.md)** *(Next Active Item)*
    *   Draft authoritative documentation covering Aether's internal logic, folder hierarchies, architecture, and module integrations.
*   **Item 9: agy governance audit**
    *   Conduct a compatibility review to ensure the agy agent strictly complies with local/global governance protocols, MEMORY.md boundaries, registry.json network definitions, and standardized VCS wrappers.
*   **Item 10: Harden agy governance**
    *   Implement robust behavior guards to prevent agy from autonomously initiating commands (like starting background servers) without manual authorization.
*   **Backlog Issues (Backlog Status on Project Board #6):**
    *   **Issue #58** (`chore`): Reconcile `load_projects()` fallback default to include newer schema fields (`last_ingested`, `exclude_dirs`).
    *   **Issue #61** (`chore`, `governance`): Audit and prevent agy from starting Aether server autonomously without approval.
    *   **Issue #62** (`chore`, `governance`): Reconcile `registry.json` keys, ports, and labels against Aether's actual state.
    *   **Issue #63** (`chore`): Investigate adding build artifact directories (`.egg-info`, `dist`, etc.) to the default index exclusions.
    *   **Issue #64** (`chore`): Investigate and reconcile `embed_calls_today` discrepancies resulting from model validation requests.

---

## 5. Pull Requests Merged This Session

*   **PR #53** (`feat`): Added support for per-project directory exclusions (`exclude_dirs`) in the ingestion engine.
*   **PR #55** (`feat`): Implemented a daily embedding quota guard and counter tracked in `data/quota.json`.
*   **PR #57** (`fix`): Converted `restart_watcher()` to async and moved watchdog joins to threads, resolving Uvicorn server deadlock during project switches.
*   **PR #60** (`refactor`): Added batch-level incremental persistence to the document refresh loop inside `sync_local_dir_custom` to prevent embedding loss.

---

## 6. Instructions for Next Session

1.  **Immediate Focus**: Begin execution on **Item 8** by compiling the functional documentation for Aether in `docs/ENGINE.md`.
2.  **Safety Directive**: Do NOT trigger any directory ingestion cycles without explicit operator confirmation.
3.  **Service Control**: Do NOT start the Aether server process autonomously. Wait for manual operator startup and instruction.

---

## 7. Session Tracker State

### Complete
- Disable auto_sync, add pending_changes flag and exclude_dirs (PR #53)
- Add daily embed quota guard (PR #55)
- Uvicorn observer deadlock fix (PR #57)
- Investigate automatic registry — no automatic registry confirmed
- Fix Issue #46 — for/else RuntimeError partial progress recovery (PR #60)
- Rebuild all indexes — Wallboard, HuckOS.C-137, Aether, Vanguard — all last_ingested populated

### Active Next Session
- Item 8: Write Aether documentation (ENGINE.md)

### Governance (Pending Audit First)
- Item 9: agy governance audit — GEMINI.md compatibility, MEMORY.md, registry.json, skill invocation syntax
- Item 10: Harden agy governance — based on audit findings

### Backlog
- Issue #58: Update load_projects() fallback default schema
- Issue #61: agy autonomously started Aether server without approval
- Issue #62: Review and reconcile registry.json against current Aether state
- Issue #63: Investigate egg-info and build artifacts in Aether index
- Issue #64: Investigate embed_calls_today vs Google RPD dashboard discrepancy


# SurvivalStack | Aether
### Dynamic Code Context Engine

Aether is a specialized context provider built on LlamaIndex and Google Gemini. It serves as a real-time "Code Oracle," indexing local source code to provide high-fidelity Retrieval-Augmented Generation (RAG) for development, architectural analysis, and project discovery.

## Key Features

- **Efficiency Mode (Lazy Loading)**: Aether stays in a "Sleep" state with a minimal memory footprint until you perform your first query.
- **Modular Architecture**: Built as a standard Python package (`aether`) with clear separation between core engine logic and API delivery.
- **Project Agnostic**: Easily switch context by updating `PROJECT_NAME` and `PROJECT_PATH` in your `.env` or using the built-in Project Registry.
- **Local-First Indexing**: Syncs directly with your local filesystem to capture uncommitted code changes instantly.
- **Interactive Dashboard**: A glassmorphic web interface for monitoring RAM usage, viewing indexed nodes, and managing project contexts.
- **Clean Station Workflow**: Use the included session manager to start and stop the engine with zero leftover background processes.

## Architecture

Aether is organized as a modular package in `src/aether/`:

1.  **Core (`aether.core`)**: Contains the primary engine logic, including ingestion (`ingest.py`), index orchestration (`engine.py`), and file system watching (`watcher.py`).
2.  **API (`aether.api`)**: A thin FastAPI wrapper that serves the engine via REST endpoints.
3.  **UI (`aether.ui`)**: Contains the templates for the web-based dashboard and registry.
4.  **Data Isolation (`/data`)**: All variable state, including the project registry (`projects.json`) and vector indices (`storage/`), is isolated from the application code.

## Getting Started

### Prerequisites
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Google Gemini API Key

### Configuration
1. Create a `.env` file in the root directory:
```env
# API Keys
GEMINI_API_KEY=your_key_here

# Active Project Configuration
PROJECT_NAME=Vanguard
PROJECT_PATH=/path/to/your/project
```

2. Initialize the project registry:
```bash
cp data/projects.json.example data/projects.json
```
Edit `data/projects.json` to map your project names to their local absolute paths.

## Session Management

Aether includes a session manager to keep your workstation clean.

```bash
# Start Aether in the background
./session.sh start

# Check real-time RAM usage and PID
./session.sh status

# Stop Aether and free all resources
./session.sh stop
```

## Dashboard Usage

Access the dashboard at **[http://localhost:8000](http://localhost:8000)**.

- **Status**: Monitor memory usage and view the current Knowledge Base state.
- **Project Registry**: Manage multiple project contexts and safely browse your filesystem to add new directories.
- **Synchronize**: Re-scans the local project path for code changes and updates the vector index.

---
© 2026 SurvivalStack

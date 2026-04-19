# SurvivalStack | Aether
### Dynamic Code Context Engine

Aether is a specialized context provider built on LlamaIndex and Google Gemini. It serves as a real-time "Code Oracle," indexing local source code to provide high-fidelity Retrieval-Augmented Generation (RAG) for development, architectural analysis, and project discovery.

## Key Features

- **Efficiency Mode (Lazy Loading)**: Aether stays in a "Sleep" state with a minimal memory footprint until you perform your first query.
- **Project Agnostic**: Easily switch context by updating `PROJECT_NAME` and `PROJECT_PATH` in your `.env`.
- **Local-First Indexing**: Syncs directly with your local filesystem to capture uncommitted code changes instantly.
- **Interactive Dashboard**: A glassmorphic web interface for monitoring RAM usage, viewing indexed nodes, and triggering manual purges/syncs.
- **Clean Station Workflow**: Use the included session manager to start and stop the engine with zero leftover background processes.

## Architecture

1.  **Ingestion (`ingestion.py`)**: Handles recursive parsing and vectorization of project source code.
2.  **Context Server (`server.py`)**: A FastAPI backend that manages the lazy loading singleton and serves the dashboard.
3.  **Storage (`/storage`)**: Local persistence for the vector index (Git-ignored for security).

## Getting Started

### Prerequisites
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Google Gemini API Key

### Configuration
Create a `.env` file:
```env
# API Keys
GEMINI_API_KEY=your_key_here

# Active Project Configuration
PROJECT_NAME=Vanguard
PROJECT_PATH=G:/path/to/vanguard
```

## Session Management

Aether includes a PowerShell session manager to keep your workstation clean.

```powershell
# Start Aether in the background
./session.ps1 start

# Check real-time RAM usage and PID
./session.ps1 status

# Stop Aether and free all resources
./session.ps1 stop
```

## Dashboard Usage

Access the dashboard at **[http://localhost:8000](http://localhost:8000)**.

- **Ping Aether**: Pre-warms the engine by loading the project index into RAM.
- **Purge**: Clears the index from memory while keeping the service alive (Efficiency Mode).
- **Synchronize**: Re-scans the local project path for code changes.

---
© 2026 SurvivalStack

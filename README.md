# SurvivalStack | Aether
### Vanguard Context Engine

Aether is a specialized context provider for the Vanguard project, built on LlamaIndex and Google Gemini. It serves as a real-time "Code Oracle," indexing local source code to provide high-fidelity Retrieval-Augmented Generation (RAG) for development and architectural analysis.

## Features

- **Local-First Indexing**: Automatically synchronizes with your local `vanguard` repository to maintain tight context on uncommitted changes.
- **FastAPI Backend**: Provides a `/query` endpoint for semantic search and code analysis.
- **Interactive Dashboard**: A modern web interface for monitoring index health, viewing vector node statistics, and triggering manual synchronizations.
- **Gemini Powered**: Utilizes `gemini-1.5-flash` for high-speed reasoning and `gemini-embedding-001` for deep semantic understanding of code relationships.

## Architecture

1.  **Ingestion (`ingestion.py`)**: Uses `SimpleDirectoryReader` to parse Python, Markdown, and configuration files from the local Vanguard directory.
2.  **Context Server (`server.py`)**: An asynchronous FastAPI server that manages the LlamaIndex state and serves the web dashboard.
3.  **Storage (`/storage`)**: Local persistence for vector stores and document metadata (ignored by Git for security).

## Getting Started

### Prerequisites
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Google Gemini API Key

### Configuration
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here
VANGUARD_PATH=C:/path/to/vanguard
```

### Running the Engine
1. **Sync Dependencies**:
   ```bash
   uv sync
   ```
2. **Start the Context Server**:
   ```bash
   uv run python server.py
   ```
3. **Access the Dashboard**:
   Open [http://localhost:8000](http://localhost:8000) in your browser.

## API Usage

### Query Context
```bash
Invoke-RestMethod -Uri "http://localhost:8000/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"prompt": "How does scout_core.py interact with individual scouts?"}'
```

---
© 2026 SurvivalStack

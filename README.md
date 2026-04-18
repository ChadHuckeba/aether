# SurvivalStack | Aether
### Dynamic Code Context Engine

Aether is a specialized context provider built on LlamaIndex and Google Gemini. It serves as a real-time "Code Oracle," indexing local source code to provide high-fidelity Retrieval-Augmented Generation (RAG) for development, architectural analysis, and project discovery.

## Features

- **Project Agnostic**: Easily switch between different projects by updating the `.env` configuration.
- **Local-First Indexing**: Automatically synchronizes with any local repository to maintain tight context on real-time changes.
- **FastAPI Backend**: Provides a `/query` endpoint for semantic search and code analysis across your project.
- **Interactive Dashboard**: A modern web interface for monitoring index health, viewing vector node statistics, and triggering synchronizations for the active project.
- **Gemini Powered**: Utilizes `gemini-1.5-flash` for high-speed reasoning and `gemini-embedding-001` for deep semantic understanding.

## Architecture

1.  **Ingestion (`ingestion.py`)**: Uses `SimpleDirectoryReader` to parse codebases from a path defined in your environment.
2.  **Context Server (`server.py`)**: An asynchronous FastAPI server that dynamically adapts its branding and sync logic based on your active project.
3.  **Storage (`/storage`)**: Local persistence for vector stores and document metadata (ignored by Git for security).

## Getting Started

### Prerequisites
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Google Gemini API Key

### Configuration
Create a `.env` file in the root directory:
```env
# API Keys
GEMINI_API_KEY=your_key_here

# Active Project Configuration
PROJECT_NAME=MyProject
PROJECT_PATH=C:/path/to/your/code
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
  -Body '{"prompt": "Explain the core architecture of this project."}'
```

---
© 2026 SurvivalStack

# Aether | Integrations & Connectivity

## Overview
Aether is built for connectivity. It can be accessed via a modern REST API or as a standardized **Model Context Protocol (MCP)** server.

## 1. Model Context Protocol (MCP)
Aether includes an MCP server implementation in `mcp_server.py`. This allows AI agents (like Google Gemini) to query the Code Oracle directly.

### Configuration
To add Aether as a tool in your agent's configuration:
```json
"mcpServers": {
  "aether": {
    "command": "/path/to/aether/.venv/bin/python",
    "args": ["/path/to/aether/mcp_server.py"],
    "env": {
      "AETHER_BASE_URL": "http://127.0.0.1:8000"
    }
  }
}
```

### Provided Tools
*   `query_codebase`: Performs a semantic RAG query against the active project.
*   `refresh_index`: Triggers a background ingestion cycle to ensure the index is fresh.

## 2. REST API Reference
The Aether server provides several endpoints for management and querying.

### `POST /query`
Performs a semantic search and returns an AI-generated answer based on the code context.
*   **Body:** `{"prompt": "string"}`

### `POST /ingest`
Triggers an asynchronous background ingestion task for the active project.

### `GET /stats`
Returns metrics about the current index, including file count, node count, and RAM usage.

### `POST /switch`
Switches the active project context.
*   **Body:** `{"name": "ProjectName"}`

### `POST /release`
Purges the vector index from RAM. Useful for lowering system overhead when not in use.

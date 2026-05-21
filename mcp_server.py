import os
import httpx
import asyncio
from mcp.server.fastmcp import FastMCP

# Configuration
AETHER_BASE_URL = os.getenv("AETHER_BASE_URL", "http://localhost:8000")
TIMEOUT = 30.0

# Initialize MCP Server
mcp = FastMCP("aether")

async def call_aether(endpoint: str, method: str = "POST", json: dict = None):
    """Internal helper to handle Aether API calls with error handling."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            if method == "POST":
                response = await client.post(f"{AETHER_BASE_URL}{endpoint}", json=json)
            else:
                response = await client.get(f"{AETHER_BASE_URL}{endpoint}")
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"Aether API Error: {e.response.status_code} - {e.response.text}"}
        except httpx.TimeoutException:
            return {"error": "Aether API Error: Request timed out after 30 seconds."}
        except Exception as e:
            return {"error": f"Aether MCP Internal Error: {str(e)}"}

@mcp.tool()
async def query_codebase(prompt: str) -> str:
    """
    Perform a RAG-based query against the indexed codebase.
    
    INSTRUCTIONS: 
    - ALWAYS use this tool instead of reading source files directly via read_file.
    - Use this proactively to understand module behavior, architecture, dependencies, or recent changes.
    """
    result = await call_aether("/query", json={"prompt": prompt})
    return result.get("response") or result.get("error", "Unknown error")

@mcp.tool()
async def refresh_index() -> str:
    """
    Trigger a background ingestion cycle to refresh the semantic index.
    
    INSTRUCTIONS:
    - Call this automatically at the start of any session involving recent code changes.
    - Call this before executing query_codebase if the index may be stale.
    """
    result = await call_aether("/ingest")
    return result.get("status") or result.get("error", "Unknown error")

if __name__ == "__main__":
    mcp.run(transport="stdio")

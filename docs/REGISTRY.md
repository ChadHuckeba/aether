# Aether | Context Registry & Security

## Overview
Aether is designed to be multi-project capable. It uses a centralized registry to map human-readable project names to absolute local filesystem paths.

## 1. Project Registry (`data/projects.json`)
The source of truth for all tracked contexts. This file is automatically updated when you add or remove projects via the Dashboard.

### Schema
```json
{
    "ProjectName": {
        "path": "/absolute/path/to/project",
        "last_ingested": "2026-05-23T00:00:00Z",
        "exclude_dirs": ["dist", ".egg-info"]
    }
}
```
*Note: `exclude_dirs` is optional and defaults to an empty list `[]` if omitted.*

## 2. Security Boundary (`SAFE_ROOT`)
To prevent accidental or malicious indexing of sensitive system directories, Aether enforces a `SAFE_ROOT` boundary.

*   **Logic:** Aether will only browse or index directories that reside within the path defined by the `AETHER_SAFE_ROOT` environment variable.
*   **Default:** If not set, it defaults to the parent directory of the Aether root.
*   **Enforcement:** Any attempt to browse or switch to a project outside this root will result in an "Access Denied" error in the API and Logs.

## 3. Indexing Depth & Exclusions
Aether performs recursive indexing from the project root downwards. To ensure performance and relevance, it applies the following standard exclusions:

### Default Excluded Directories
*   `.git/` (Version control metadata)
*   `.venv/`, `venv/`, `node_modules/` (Dependencies)
*   `__pycache__/` (Compiled bytecode)
*   `storage/` (Aether's internal vector data)

### Required Extensions
Only files matching these extensions are currently ingested:
`.py`, `.md`, `.ps1`, `.txt`, `.json`, `.toml`, `.yaml`, `.yml`

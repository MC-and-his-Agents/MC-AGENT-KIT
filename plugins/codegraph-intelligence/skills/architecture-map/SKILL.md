---
name: architecture-map
description: Map the architecture of a repository using CodeGraph.
metadata:
  internal: true
---

Use this skill to get a high-level overview of how a repository is structured, how modules relate to each other and where responsibilities lie.

Goal: Produce a concise architectural map highlighting entry points, core modules, infrastructure, shared utilities and external integrations.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_files`, `codegraph_search`, `codegraph_node` and `codegraph_explore` for unclear major subsystems.

Workflow:
1. Verify the availability of the graph index with `codegraph_status`.
2. Use `codegraph_files` to retrieve a tree or list of files and directories. Group them into domains such as API layer, services, data layer, configuration, tests and assets.
3. Search for common entry points: `main` functions, server files, app initialisers, index files and CLI commands using `codegraph_search`. Confirm with `codegraph_node`.
4. Identify core modules and services by examining directories that are imported frequently or have many dependents. Use `codegraph_node` to see in-degree/out-degree if available.
5. Use `codegraph_explore` only when a major subsystem remains unclear after `codegraph_files` and targeted searches. Keep explore queries to symbol names, file names or short code terms.
6. Categorise modules as core logic, infrastructure (database, cache, message queue), external integrations (third-party APIs) and shared utilities.
7. Summarise the findings in sections such as:
   - Entry points
   - Core modules/services
   - Infrastructure components
   - External integrations
   - Shared utilities
   - Dependency direction and any circular dependencies
   - Architectural risks (e.g. tight coupling, missing abstractions)
8. Use lists or bullet points for clarity. Avoid exhaustive detail; focus on structural understanding.

Rules:
- Do not attempt to describe every file. Focus on patterns and structure.
- When using CLI fallback, note that the lack of graph metadata may limit dependency analysis.

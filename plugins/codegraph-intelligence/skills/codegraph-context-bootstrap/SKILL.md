---
name: codegraph-context-bootstrap
description: Build repository context using CodeGraph before starting tasks.
metadata:
  internal: true
---

Use this skill when exploring an unfamiliar project or subsystem, onboarding to a new area, or preparing for significant or cross-module changes. Do not trigger it automatically for every new session or for simple localized tasks.

Goal: Establish a concise, graph-backed context for the current task without scanning the entire repository.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_explore`, `codegraph_search` and `codegraph_files` for unfamiliar areas.

Workflow:
1. Call `codegraph_status` (or `codegraph status .`) to check if a graph index exists and is fresh. If missing or stale, request the user run `codegraph init -i` or `codegraph sync`.
2. Use one bounded `codegraph_explore` call to build context for the current task (for example, "refactor auth module"), anchored to known symbols or files when available.
3. Supplement with `codegraph_search` for specific keywords, classes, functions or services relevant to the task. Disambiguate by module, file path or symbol kind when multiple matches appear.
4. Use `codegraph_node` when one exact symbol needs more detail than the bounded survey returned.
5. Use `codegraph_files` to understand the repository structure and identify important directories and modules.
6. Summarise the context: key files, modules, classes, functions, entry points, external integrations, and potential risks. Use lists or tables for clarity.
7. For tasks that trigger this skill, build context before broad file reading or editing.

Rules:
- Do not read large numbers of files without first using CodeGraph to narrow down the scope.
- Keep the main session lightweight: prefer one bounded `codegraph_explore` call over broad file reading.
- Clearly state when the context is incomplete or when CodeGraph analysis is unavailable.

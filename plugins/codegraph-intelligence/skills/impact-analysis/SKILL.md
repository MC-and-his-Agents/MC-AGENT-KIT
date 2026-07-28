---
name: impact-analysis
description: Analyze the impact of modifying, renaming, deleting, or refactoring a symbol, module, API, route or service using CodeGraph.
metadata:
  internal: true
---

Use this skill before changing code that may affect callers, callees, tests, routes, public exports or shared modules.

Goal: Provide a structured report of the potential impact of a proposed change so the user can evaluate risk and plan the work safely.

Required reference:
- Use `reference/report-template.md` for the final report structure and risk levels.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_search`, `codegraph_explore`, `codegraph_node`, `codegraph_callers`, `codegraph_callees` and `codegraph_impact`.

Workflow:
1. Ensure a fresh graph index by calling `codegraph_status`. If missing, request the user run `codegraph init -i`; if stale, request `codegraph sync`.
2. Read `reference/report-template.md` and use it to shape the output.
3. Locate the target: use `codegraph_search` with the provided symbol name, route path, module or keyword. For ambiguous results, examine each candidate with `codegraph_node` and pick the most relevant; list others for transparency.
4. If the target sits inside an unfamiliar subsystem, use a bounded `codegraph_explore` query anchored to the target symbol before widening the analysis.
5. Inspect the selected node via `codegraph_node` to confirm its kind (function, class, method, module), file path, export status and context.
6. Use `codegraph_callers` to find direct callers. Note entrypoints such as routes, commands, controllers and test harnesses separately.
7. Use `codegraph_callees` to find downstream dependencies, including database calls, service calls, network calls and shared utilities.
8. Use `codegraph_impact` to compute a broader impact radius. Categorize results by:
   - Direct callers
   - Indirect callers
   - Tests
   - Routes or commands
   - Public exports or API surfaces
   - External integrations and side effects
9. Identify related tests and consider using `test-target-finder` to compute the minimal test suite.
10. Read only the smallest necessary set of source files to confirm details after the graph analysis is complete.
11. Produce a structured summary using the required sections in `reference/report-template.md`, including:
   - Target
   - Current role (public API, internal helper, CLI command, etc.)
   - Direct callers
   - Downstream dependencies
   - Broader impact
   - Tests likely affected
   - Files likely to edit
   - Risk level (e.g. low/medium/high)
   - Recommended implementation order
   - Uncertainties or questions for the user

Rules:
- Do not edit files until the impact summary is complete.
- Prefer graph-backed findings over broad grep or file scanning.
- Reserve `codegraph_explore` for unfamiliar areas; do not use it for narrow symbol lookups.
- Use the risk levels from `reference/report-template.md`.
- Clearly mark uncertain findings or dynamic behaviours.
- When using CLI fallback, state that results may be incomplete.

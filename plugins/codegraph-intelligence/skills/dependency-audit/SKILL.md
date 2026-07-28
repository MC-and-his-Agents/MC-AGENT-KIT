---
name: dependency-audit
description: Audit module dependencies and detect high coupling or cycles using CodeGraph.
metadata:
  internal: true
---

Use this skill when you need to understand how modules depend on each other, identify tight coupling or detect circular dependencies.

Goal: Provide insights into module relationships so you can plan refactoring, enforce architectural boundaries or improve maintainability.

Required reference:
- Use `reference/dependency-rules.md` for dependency categories, cycle severity and output fields.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_files`, `codegraph_search`, `codegraph_node`, `codegraph_callers`, `codegraph_callees` and `codegraph_explore` for unclear module boundaries. CodeGraph does not yet expose a dedicated dependency graph query, so combine available metadata and caller/callee queries.

Workflow:
1. Confirm the graph index is current with `codegraph_status`.
2. Read `reference/dependency-rules.md` before classifying coupling or cycles.
3. Identify the modules or packages under audit (e.g. `app`, `domain`, `infra`). Use `codegraph_files` to list directories and submodules.
4. For each module, use `codegraph_search` to find exports and their locations.
5. For each export, call `codegraph_node`, `codegraph_callers` and `codegraph_callees` to inspect incoming and outgoing references.
6. Use `codegraph_explore` only when module boundaries are unclear after the targeted queries.
7. Summarise dependencies:
   - **Inbound dependencies**: which modules depend on this module?
   - **Outbound dependencies**: which modules this module depends on?
8. Look for signs of high coupling using the coupling signals in the reference.
9. Attempt to detect circular dependencies by examining mutual imports. When node data shows that module A imports module B and module B imports module A, flag it as a cycle and classify severity from the reference.
10. Present findings in a table or bulleted list, highlighting:
   - Modules audited
   - Their inbound and outbound dependencies
   - Potential cycles
   - Recommendations to decouple or apply dependency inversion

Rules:
- Be explicit that the current CodeGraph API does not expose a dedicated full dependency graph endpoint; your analysis is based on available metadata and may miss dynamic or indirect imports.
- Use the dependency categories and cycle severity from `reference/dependency-rules.md`.
- Encourage incremental improvements rather than wholesale rewrites.

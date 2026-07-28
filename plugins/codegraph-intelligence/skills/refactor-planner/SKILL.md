---
name: refactor-planner
description: Plan a safe refactor using CodeGraph analysis.
metadata:
  internal: true
---

Use this skill when the user wants to refactor a module, class, component, or subsystem. A good plan identifies public surfaces, dependencies, callers and tests before making changes.

Goal: Create a phased refactor plan that minimises risk and maintains functionality.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_context`, `codegraph_explore`, `codegraph_search`, `codegraph_node`, `codegraph_callers`, `codegraph_callees` and `codegraph_impact`.

Workflow:
1. Validate that the CodeGraph index is available and fresh using `codegraph_status`. If not, prompt to run `codegraph init -i` or `codegraph sync`.
2. Identify the target to refactor using `codegraph_search`. Resolve ambiguities with `codegraph_node`.
3. Use `codegraph_context` for focused target context. Use `codegraph_explore` only for a broad subsystem survey, anchored to concrete symbols or files.
4. Determine the public surface: exported functions, classes, interfaces, REST endpoints, GraphQL resolvers, CLI commands. Use `codegraph_callers` to see who uses each export.
5. Map dependencies and downstream effects using `codegraph_callees`. Include database operations, caches, file I/O and external services.
6. Analyse impact using `codegraph_impact` to find indirectly affected modules and tests.
7. Identify tests that cover the target and its callers by combining impact analysis with `test-target-finder`.
8. Look for anti-patterns such as circular dependencies, tight coupling and deeply nested call chains.
9. Create a stepwise refactor plan:
   - **Phase 1**: Clean up and extract helpers or interfaces.
   - **Phase 2**: Introduce new abstractions while maintaining old interfaces.
   - **Phase 3**: Migrate callers to the new abstractions and remove the old ones.
   - **Phase 4**: Update tests and documentation.
10. Include a validation plan: which tests to run after each phase and how to verify correctness.

Rules:
- Do not begin editing until you have a clear plan.
- Communicate trade-offs and unknowns clearly.
- Encourage incremental changes over a big-bang rewrite.
- Mark areas requiring domain knowledge or user confirmation.

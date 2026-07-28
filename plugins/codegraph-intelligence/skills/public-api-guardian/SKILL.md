---
name: public-api-guardian
description: Evaluate changes to public API surfaces using CodeGraph to avoid breaking consumers.
metadata:
  internal: true
---

Use this skill when the user proposes renaming, removing or altering functions, classes, routes or modules that are exported publicly or consumed by other packages or services.

Goal: Determine whether the change will break downstream consumers and advise on safe migration strategies.

Required reference:
- Read `reference/public-api-rules.md` before deciding whether a change is safe, breaking or migration-only.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_explore`, `codegraph_search`, `codegraph_node`, `codegraph_callers` and `codegraph_impact`.

Workflow:
1. Verify the graph index is available using `codegraph_status`.
2. Read `reference/public-api-rules.md` and use it to classify public API signals and external consumer risk.
3. Locate the public API symbol (function, method, class, module, route) using `codegraph_search`. Confirm it is exported or reachable via an HTTP path.
4. Use one bounded `codegraph_explore` call for surrounding API context when the surface belongs to an unfamiliar subsystem.
5. Inspect the symbol with `codegraph_node` to understand its file path, export declaration and any documentation or annotations.
6. Use `codegraph_callers` to find direct consumers of the symbol. Distinguish internal callers (within the same codebase) from external callers (other packages, microservices, public entry points).
7. Use `codegraph_impact` to identify indirect consumers and test files that reference the symbol.
8. Evaluate change safety:
   - If no external callers exist, renaming or removal may be safe but still requires internal updates.
   - If external callers exist, propose migration strategies, such as:
     - Deprecate the old name and add a wrapper that forwards to the new implementation.
     - Introduce versioned routes.
     - Document the change and communicate to consumers.
   - If dynamic references (reflection, dynamic import) are suspected, warn that static analysis may miss some call sites.
9. Summarise:
   - The symbol and its role (public API, library helper, etc.)
   - Direct and indirect consumers
   - Tests affected
   - Recommended approach (e.g. add wrapper, create alias, avoid breaking change)
   - Required follow-up actions (update docs, notify consumers)

Rules:
- When in doubt, assume an exported symbol has external consumers.
- Avoid breaking public APIs without a migration path.
- Use the breaking change levels from `reference/public-api-rules.md`.
- Clearly state when the analysis cannot determine all consumers due to dynamic usage.

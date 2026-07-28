---
name: change-plan-with-graph
description: Generate a graph-backed implementation plan before modifying repository code.
metadata:
  internal: true
---

Use this skill for significant, unfamiliar, high-risk or cross-module implementation work, refactors, renames, removals or migrations. Also use it when the user explicitly asks for graph-backed planning. Do not trigger it for simple single-file edits, formatting, typos, straightforward test updates or direct command-output requests.

Goal: Produce a graph-backed implementation plan when the change is large or risky enough that caller, callee, test or public-surface impact matters.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_search`, `codegraph_node`, `codegraph_callers`, `codegraph_callees`, `codegraph_impact` and `codegraph_explore` for unfamiliar subsystems.

Workflow:
1. Summarise the user's goal in a single sentence to anchor the task.
2. Call `codegraph_status` to ensure the graph index is available and fresh. If not, ask the user to initialise or sync it.
3. Build task context with one bounded `codegraph_explore` call (e.g. "implement rate limiting for authenticated routes"), anchored to known symbols or files when available.
4. Use `codegraph_search` and `codegraph_node` to locate or disambiguate exact symbols.
5. Identify relevant symbols and modules using `codegraph_search`. Use `codegraph_node` to confirm details. Resolve ambiguities.
6. Run `impact-analysis` on the key symbols to understand who calls them, who they call and what tests are affected.
7. Use `test-target-finder` to determine which tests will need to run.
8. Draft a short implementation plan that includes:
   - High-level steps (analysis, code changes, tests, validation).
   - Files or modules to edit.
   - Supporting tasks (e.g. update documentation).
   - Estimated risks and unknowns.
9. Proceed after the plan for low-risk technical changes. Ask the user before editing only when the plan affects product behavior, cost, time, security, privacy, data, permissions or other externally visible outcomes.

Rules:
- For changes that trigger this skill, produce a graph-backed plan before editing. Do not block trivial edits that do not meet the trigger criteria.
- User confirmation is required only for the higher-risk cases above.
- Prefer CodeGraph findings; if using CLI fallback, clearly state that results may be incomplete.
- Encourage the user to ask clarifying questions or adjust the plan before execution.

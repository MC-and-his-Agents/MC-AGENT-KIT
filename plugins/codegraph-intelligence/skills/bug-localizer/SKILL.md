---
name: bug-localizer
description: Narrow down likely code locations from bug descriptions using CodeGraph.
metadata:
  internal: true
---

Use this skill when the user describes a bug (e.g. "users cannot reset password") and you need to identify where in the code the problem might reside.

Goal: Produce a short list of functions, classes or modules that are likely relevant to the bug, so you can focus your debugging efforts.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_search`, `codegraph_node`, `codegraph_callers`, `codegraph_callees` and `codegraph_explore` for unfamiliar bug areas.

Workflow:
1. Summarise the bug description into a few keywords (e.g. for "users cannot reset password", keywords might be "password reset", "reset password", "token", "forgotPassword", "resetPassword", etc.).
2. Ensure the graph index is available using `codegraph_status`.
3. Use `codegraph_search` with these keywords to locate candidate symbols. Include synonyms, route patterns and error messages if possible.
4. If the bug spans an unfamiliar subsystem, use one bounded `codegraph_explore` query anchored to the bug and any symbols or files found by search.
5. For each candidate, inspect details with `codegraph_node` and note the file path, symbol kind and any obvious misuse.
6. Examine callers and callees with `codegraph_callers` and `codegraph_callees` to see how the candidate fits into the broader system.
7. Prioritise candidates based on:
   - Direct relationship to the bug keywords (e.g. a `resetPassword` function)
   - Their role in critical flows (authentication, account management)
   - Proximity to recent changes (if change history is available)
8. Compile a ranked list of likely locations with brief explanations. Include file paths, functions/methods and why they are relevant.
9. Recommend additional investigation steps, such as reading logs, reproducing the bug locally or examining the latest commits touching those areas.

Rules:
- Do not attempt to fix the bug within this skill; the goal is to locate relevant code.
- Make it clear when the ranking is heuristic and subject to confirmation.
- If the graph does not provide enough signal, fall back to simple keyword and directory search and note the limitation.

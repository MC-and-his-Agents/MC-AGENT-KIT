---
name: test-target-finder
description: Identify the minimal set of tests to run after code changes using CodeGraph.
metadata:
  internal: true
---

Use this skill after code has been modified to determine which tests should be run to validate the change. It helps avoid running the entire test suite unnecessarily.

Goal: Recommend a focused set of tests that exercises the affected areas and an extended set for regression.

Auxiliary files:
- Use `scripts/codegraph-affected.sh` as the CLI fallback wrapper when MCP test discovery is unavailable or `codegraph affected` is preferred.
- Use `reference/test-selection-rules.md` to classify minimal, caller and regression tests.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_impact` through MCP or `scripts/codegraph-affected.sh` for CLI fallback. CodeGraph does not yet expose a dedicated test-finding MCP tool.

Workflow:
1. Identify the set of changed files. Use `git diff --name-only HEAD` or the list provided by the user.
2. Read `reference/test-selection-rules.md`.
3. Call `codegraph_status` to ensure the index is current.
4. **Prefer CLI fallback wrapper**: run `scripts/codegraph-affected.sh` with the changed files, or pipe file names into it. It calls `codegraph affected --stdin --json` and returns structured output.
5. If using MCP: for each changed symbol or file, run `codegraph_impact` and collect all test files (often under `__tests__`, `tests/` or similar) in the impact radius.
6. Classify tests:
   - **Minimal tests**: those directly referencing the changed symbols or changed files.
   - **Broader regression tests**: those indirectly affected through callers or shared modules.
7. Present the recommended test list with reasons. Explain why each test is included (direct dependency, indirect dependency, broad regression).
8. Advise the user to run the minimal set first and the broader set if time permits.

Rules:
- Do not recommend running the full test suite unless the impact analysis is inconclusive, the change touches shared contracts, or the project has no reliable focused test mapping.
- Use the escalation rules from `reference/test-selection-rules.md`.
- If test discovery is incomplete because CodeGraph analysis is unavailable, explicitly state this limitation.

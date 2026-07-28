---
name: dead-code-hunter
description: Identify potentially unused or unreachable code using CodeGraph.
metadata:
  internal: true
---

Use this skill to find functions, classes or modules that appear to be unused so they can be candidates for deletion or refactoring.

Goal: Provide a list of symbols with zero incoming references and suggest follow-up verification steps.

Required reference:
- Read `reference/false-positive-checklist.md` before classifying any candidate as high-confidence dead code.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_files`, `codegraph_search`, `codegraph_node` and `codegraph_callers`.

Workflow:
1. Ensure the graph index is up to date with `codegraph_status`.
2. Read `reference/false-positive-checklist.md` and use it as the exclusion standard.
3. Narrow the scope: specify a module, directory or pattern (e.g. functions in `utils/` or classes under `services/`) to avoid scanning the entire codebase.
4. Use `codegraph_files` and `codegraph_search` to retrieve candidate symbols matching the scope.
5. For each candidate, call `codegraph_callers` to see if any functions or modules reference it. If the callers list is empty, mark the symbol as a potential dead code candidate.
6. Exclude symbols that are:
   - Framework hooks or lifecycle methods automatically invoked (e.g. `onInit`, `componentDidMount`).
   - Publicly exported APIs or routes.
   - Reflectively invoked via strings or annotations.
   - Used in templates, configuration files or external resources outside CodeGraph's static analysis.
7. Compile a list of high-confidence and medium-confidence dead code using the confidence rules from the reference:
   - **High confidence**: No callers and no exports; likely safe to remove after verification.
   - **Medium confidence**: No callers, but exported or named in a way that suggests dynamic invocation; requires manual investigation.
8. Recommend verifying each candidate by:
   - Searching the codebase for string references.
   - Grepping templates or configuration files.
   - Running the application and monitoring logs or coverage reports.
9. Provide the list with file paths, symbol names, confidence levels, completed false-positive checks and remaining uncertainty.

Rules:
- Do not remove code automatically. This skill only surfaces candidates.
- Clearly state assumptions and potential sources of false positives.
- Treat framework hooks, generated entrypoints and exported symbols as unsafe to delete until separately verified.
- Never label a candidate high-confidence without evidence for every required field in `reference/false-positive-checklist.md`.
- Encourage thorough testing before deletion.

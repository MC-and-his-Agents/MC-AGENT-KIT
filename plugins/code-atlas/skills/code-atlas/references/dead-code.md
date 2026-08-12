# ASSESS：dead-code 候选与误报过滤

Use this reference only when the question includes unused, unreachable or
removable code. It is a candidate finder, never an automatic deletion workflow.

## Candidate evidence

Scope the scan to a module, directory, symbol set or changed files. Use visible
graph search/callers or local search to collect zero-incoming-reference
candidates, then record symbol, file, export status and caller evidence.

Before calling a candidate high confidence, search for:

- public exports, package entrypoints, routes, CLI commands and workers;
- framework lifecycle hooks, dependency injection, decorators and reflection;
- string references in configuration, templates, manifests and generated code;
- migrations, fixtures, snapshots, compatibility shims and external consumers.

`no callers` is **observed** only for the inspected static scope; safety of
deletion is **unknown** when dynamic or external references are possible.

## Output

Separate high-confidence candidates (no callers, no public/dynamic signal, all
false-positive checks complete) from medium-confidence candidates requiring a
human check. Recommend a small verification test or runtime observation. Do not
remove code, open issues or claim certainty by default.

# CHANGE：变更影响、重构与测试选择

Use this as the primary reference before a rename, removal, refactor, API or
cross-module change. Combine with `test-selection.md` when a concrete test set
is required and with `codegraph.md` when graph availability is uncertain.

## Workflow

1. Restate the requested change and list its target files/symbols. Do not edit
   before this impact summary is complete.
2. Find the target and confirm its role (internal, entrypoint, exported API,
   route, persistence or external integration).
3. Inspect direct callers, callees, imports, tests and public surfaces using
   only visible MCP tools or focused local evidence. Use one bounded
   `codegraph_explore` for an unfamiliar subsystem.
4. Classify impact as direct callers, indirect dependents, routes/commands,
   tests, public consumers and side effects. Mark observed/inferred/unknown.
5. Choose the smallest behavior-preserving change. For removals, check string,
   configuration, template, generated and external references before claiming
   safety. For public APIs, assume external consumers when evidence is missing.
6. Select minimal direct tests, caller/regression tests and an escalation suite;
   see `test-selection.md`. If tests are weak, propose characterization tests
   before refactoring.
7. Return order, files, risks, validation and unknowns. Ask for user input only
   when product behavior, security, privacy, data, permissions, cost or roadmap
   changes.

## Guardrails

Do not add compatibility wrappers for one internal caller without evidence.
Do not call a missing graph edge proof of safety. Do not run a mutating
formatter, migration, install or index operation in this lane.

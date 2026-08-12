# UNDERSTAND：探索与架构上下文

Use this as the primary reference for an unfamiliar repository, module,
entrypoint or subsystem. Read `codegraph.md` first only when availability or
fallback behavior affects the answer.

## Workflow

1. State the target, scope and what is still unknown.
2. If native MCP is visibly available, make one bounded `codegraph_explore` call
   anchored to the task, a known file, symbol or short code term. Do not survey
   the whole repository.
3. Supplement with visible `codegraph_search` or `codegraph_files` only when
   needed; otherwise use focused local file and Git inspection.
4. Confirm entrypoints, major modules, data/infrastructure boundaries and
   external integrations from files or returned nodes.
5. Label every relation observed, inferred or unknown. Keep dynamic dispatch,
   generated code and external consumers explicitly unknown unless evidence
   exists.
6. Return a compact map: entrypoints, core modules, infrastructure, external
   integrations, dependency direction, tests and risks.

## Output

Prefer a table or short bullets. Include file paths and symbols when observed;
do not claim that a missing search result means dead code. Do not edit files or
create tasks as part of UNDERSTAND.

# CodeGraph contract

Use this reference whenever graph availability or a fallback changes the
confidence of the answer.

## Necessary local scope

CodeGraph evidence is valid only when both conditions hold:

1. the `codegraph` executable is discoverable on the current process `PATH`;
2. the current Git worktree contains the regular file
   `<worktree-root>/.codegraph/codegraph.db`.

Resolve `<worktree-root>` with `git rev-parse --show-toplevel` from the current
working directory. Resolve the absolute shared Git directory with
`git rev-parse --git-common-dir` for identity only. Do not use a parent index,
another worktree, `CODEGRAPH_DIR`, a guessed cache, or a path copied from a
different checkout.

The lifecycle hook checks these facts read-only. It does not run a CodeGraph
subcommand, access the network, start a watcher/daemon, read stdin, or write
files. A missing or unreadable fact is `unknown`, not a reason to invent graph
results.

## MCP negotiation

The plugin ships no MCP server configuration. When the host provides native MCP,
call `tools/list` through the host capability and use only names returned there.
The default is one bounded `codegraph_explore` call for an unfamiliar area. Use
`codegraph_search`, `codegraph_node`, `codegraph_callers`,
`codegraph_callees`, `codegraph_impact` or `codegraph_files` only when the
runtime visibly exposes the exact name and the task needs it. Never assume
`codegraph_status` or an undocumented wrapper.

If no MCP capability is visible, use the CLI only for a read-only query already
supported by the installed version, or use local file/Git inspection. Do not
use `codegraph context`; it is not part of this contract. Do not run status,
sync, index, serve or any other CLI command merely to improve a report.

## Availability states

Report one of these states at the top of graph-backed work:

- `full`: CLI, exact worktree database and explicit host evidence that MCP is
  available;
- `cli-only`: CLI and exact worktree database are present, but MCP is absent or
  not explicitly evidenced;
- `unavailable`: either CLI or exact database is missing.

The hook reports `mcp: unknown` unless the host explicitly supplies a runtime
marker. Do not promote `unknown` to `full` because a plugin is installed.

## Authorization

Installing CodeGraph, running `codegraph install`, and running
`codegraph init <worktree-root>` are separate user-authorized operations. Before
asking, explain: (a) why graph evidence helps this task, (b) the official
source/package, (c) the exact worktree scope and files that may be written
(`.codegraph`, possibly `.gitignore`), and (d) side effects such as a full
build, prompted watcher/Git-hook setup, host MCP config, update checks,
telemetry or daemon startup. Only then execute and verify the authorized
command. The init form has no `-i` flag.

Live MCP smoke is optional and must be temp-only, short-timeout, with update
checks, telemetry, daemon and watcher disabled. This task does not run a live
CodeGraph install, init or MCP smoke.

## Evidence discipline

Mark each edge and status as:

- **observed** — directly returned by a visible tool or read-only local command;
- **inferred** — a conclusion from observed names, imports, paths or history;
- **unknown** — dynamic, unavailable, out of index, or not checked.

CLI output may be less structured than MCP output. Missing graph coverage never
proves that a caller, route, public consumer or test does not exist.

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
`git rev-parse --git-common-dir` for identity only, and resolve the actual hooks
directory with `git rev-parse --git-path hooks` (including `core.hooksPath`) for
the before/after write-scope check. Do not use a parent index,
another worktree, `CODEGRAPH_DIR`, a guessed cache, or a path copied from a
different checkout.

The lifecycle hook resolves these facts for the exact current worktree. On
`SessionStart`, it runs a bounded `codegraph init <worktree-root>` when the DB is
missing, or `codegraph sync --quiet <worktree-root>` when it exists. The command
environment disables downloads, update checks, telemetry and daemon behavior.
For init it forces the normal watcher policy so CodeGraph does not offer its
interactive Git-hook fallback; for sync it disables watcher behavior. The
process exits after the command, so no watcher remains. A fresh or unreadable
`.codegraph/codegraph.lock` is detected read-only before sync and becomes
`needs-agent`; the hook never deletes or unlocks it. Only the current
worktree's `.codegraph` and an init-required `.gitignore` change are allowed.
`SubagentStart` never runs these commands. A missing or unreadable fact is
`unknown`, not a reason to invent graph results.

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
use `codegraph context`; it is not part of this contract. The lifecycle hook is
the exception for bounded `init`/`sync` plus its `status --json` verification: it
performs the automatic freshness attempt before returning SessionStart context.
Do not run unrelated status, index, serve or install commands merely to improve
a report.

## Availability states

Report one of these states at the top of graph-backed work:

- `full`: CLI, exact worktree database and explicit host evidence that MCP is
  available;
- `ready`: the SessionStart lifecycle action completed and the exact worktree
  database is present; MCP may still be unknown;
- `cli-only`: CLI and exact worktree database are present, but MCP is absent or
  not explicitly evidenced;
- `needs-agent`: the hook attempted lifecycle work but hit a timeout, non-zero
  exit, lock/interaction/write-scope failure or partial database and supplied a
  takeover command;
- `unavailable`: either CLI or exact database is missing and no automatic action
  could start.

The hook reports `mcp: unknown` unless the host explicitly supplies a runtime
marker. Do not promote `unknown` to `full` because a plugin is installed.

## Authorization

Installing CodeGraph and running `codegraph install` remain separate
user-authorized operations. If the CLI is missing, the hook does not install it;
it explains the official `@colbymchenry/codegraph` source and gives the Agent an
exact same-session takeover. A manual takeover must explain why graph evidence
helps, the exact worktree scope (`.codegraph`, possibly `.gitignore`) and any
additional side effects before execution. The init form has no `-i` flag.

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

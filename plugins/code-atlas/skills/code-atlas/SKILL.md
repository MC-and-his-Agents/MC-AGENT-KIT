---
name: code-atlas
description: CodeAtlas analysis workflows are read-only; SessionStart maintains only the current worktree's .codegraph index and any required .gitignore. Route work through UNDERSTAND, TRACE, CHANGE or ASSESS; use the worktree-local CodeGraph index and label evidence as observed, inferred or unknown.
metadata:
  internal: true
  version: 0.3.1
---

# CodeAtlas

CodeAtlas is one private skill with four narrow lanes. The analysis workflows
remain read-only: they do not edit source code or create issues. The lifecycle
hook keeps the current worktree's CodeGraph index usable by automatically
running a bounded `init` or `sync` at `SessionStart`; it never installs the CLI,
configures MCP, installs Git hooks or starts a daemon/watcher.

## Route first

Choose one primary reference for ordinary work. Combine references only when the
request crosses lanes:

| Lane | Use when | Primary reference |
|---|---|---|
| **UNDERSTAND** | unfamiliar repository, module, entrypoint or architecture | `references/exploration.md` |
| **TRACE** | request, route, symbol, bug or runtime path | `references/trace-and-debug.md` |
| **CHANGE** | rename, removal, refactor, impact or test plan | `references/change-analysis.md` |
| **ASSESS** | dead code, tests, code smells or maintainability decisions | `references/maintainability.md`, then `references/dead-code.md` or `references/test-selection.md` as needed |

Read `references/codegraph.md` whenever graph availability, CLI fallback,
installation, initialization, MCP negotiation or evidence labels matter.

## Evidence contract

Every material claim is labelled:

- **observed** — directly returned by a visible MCP tool, a read-only CLI query,
  a file, Git history, or a reproducible local command;
- **inferred** — a reasoned interpretation of observed evidence;
- **unknown** — not available, dynamic, outside the index, or not verified.

Do not turn an inferred edge into a deletion or migration claim. If the graph is
missing, keep conclusions conservative and say that the result is CLI-only or
local-only.

## CodeGraph preflight

The necessary local evidence is the CodeGraph CLI plus the exact current
worktree file `<worktree-root>/.codegraph/codegraph.db`. CodeAtlas never borrows
an index from a parent directory, another worktree or `CODEGRAPH_DIR`.

Native MCP is not bundled or declared by this plugin. At runtime, negotiate
capabilities with `tools/list` when the host exposes it. Default to
`codegraph_explore`; use another tool only when that exact tool is visible. Do
not assume `codegraph_status`, `codegraph context`, or any undocumented tool.

If the local database or CLI is absent, proceed with conservative file/Git
inspection and report `unavailable` or `needs-agent`. A successful lifecycle
action is `ready`; a present CLI/index without explicit MCP runtime evidence is
`cli-only` (the normal SubagentStart observation). Never imply that MCP is active.

The shared `hooks/claude-codex-hooks.json` runner receives `SessionStart` or
`SubagentStart` as its argument. Native Claude receives raw SessionStart context
and `hookSpecificOutput` JSON for SubagentStart; Codex (`PLUGIN_DATA`) receives
`systemMessage` plus `hookSpecificOutput`. SessionStart preserves the current
worktree boundary and reports the action/result. SubagentStart is intentionally
cheap: it never repeats `init`/`sync` and only carries the current evidence and
the observed/inferred/unknown rules.

## Authorization boundaries

The lifecycle hook is already authorized as part of installing CodeAtlas and may
write only the current worktree's `.codegraph` directory and an init-required
`.gitignore` change. It runs with a short timeout, disables download/update,
telemetry and daemon behavior. Init forces the normal watcher policy to avoid
CodeGraph's interactive Git-hook fallback; sync disables watcher behavior. A
fresh `.codegraph/codegraph.lock` is observed read-only and handed to the Agent;
the hook never deletes or unlocks it.

The following actions still require a separate user authorization after
explaining the value, official source, exact write scope and side effects:

- installing CodeGraph (for example, the official package source);
- `codegraph install` (state the target host/config file);
- manual `codegraph init <worktree-root>` outside the lifecycle hook (writes the
  requested worktree's `.codegraph` data, may update `.gitignore`, and performs
  a full build);
- any live MCP or daemon smoke.

The initialization shape is exactly `codegraph init <worktree-root>`; do not add
`-i`. The hook runs only `init` for a missing index or `sync --quiet` for an
existing index. A timeout, non-zero exit, lock conflict, interaction risk or
partial database becomes `needs-agent` with the exact takeover command; the
Agent may run it in the same session after explaining any additional scope.
After `init`/`sync`, it performs one bounded `codegraph status --json` check and
requires the exact worktree path, initialized state and zero pending changes
before reporting `ready`. The hook never runs `codegraph install`, configures MCP,
installs Git hooks or uses a parent/other-worktree index.

## Read-only maintainability behavior

The seven bundled scanners and evidence-pack builder print JSON to stdout and
must not modify the analyzed repository. Scanner output is candidate evidence,
not an engineering decision. By default, produce a report only; do not create
issues, apply fixes or run mutating formatters.

```bash
python3 scripts/scan-size-complexity.py <target>
python3 scripts/scan-duplication.py <target>
python3 scripts/scan-dependencies.py <target>
python3 scripts/scan-tests.py <target> --repo <worktree-root>
python3 scripts/scan-literals-comments.py <target>
python3 scripts/scan-git-churn.py <target> --repo <worktree-root>
python3 scripts/build-evidence-pack.py --target <target> <reports...>
```

The config example and JSON schemas live under `assets/`. Load only the one
reference needed for the current lane, then add a second reference when the
evidence crosses a lane boundary.

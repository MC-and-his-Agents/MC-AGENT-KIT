---
name: code-atlas
description: Read-only CodeAtlas workflows for repository understanding, request tracing, change impact and maintainability decisions. Route work through UNDERSTAND, TRACE, CHANGE or ASSESS; use the worktree-local CodeGraph index when available and label evidence as observed, inferred or unknown.
metadata:
  internal: true
  version: 0.3.0
---

# CodeAtlas

CodeAtlas is one private skill with four narrow lanes. It builds evidence for the
current Git worktree and does not edit code, create issues, initialize indexes,
install software or run mutating commands unless the user explicitly requests a
separate action and authorizes it.

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
inspection and report `unavailable`. A CLI plus local database without explicit
MCP runtime evidence is `cli-only`; never imply that MCP is active.

The shared `hooks/claude-codex-hooks.json` runner receives `SessionStart` or
`SubagentStart` as its argument. Native Claude receives raw SessionStart context
and `hookSpecificOutput` JSON for SubagentStart; Codex (`PLUGIN_DATA`) receives
`systemMessage` plus `hookSpecificOutput`. Subagent context is intentionally
shorter and contains only worktree/CLI/index evidence and the observed/inferred/
unknown rules.

## Authorization boundaries

The following actions require a separate user authorization after explaining
the value, official source, exact write scope and side effects:

- installing CodeGraph (for example, the official package source);
- `codegraph install` (state the target host/config file);
- `codegraph init <worktree-root>` (writes the requested worktree's `.codegraph`
  data, may update `.gitignore`, perform a full build, and may prompt for
  watcher or Git-hook side effects);
- any live MCP or daemon smoke.

The initialization shape is exactly `codegraph init <worktree-root>`; do not add
`-i`. CodeAtlas does not run `codegraph --version`, `status`, `serve`, `install`,
`init`, `index` or `sync` from a lifecycle hook. The hook only reports PATH and
the exact local database file. `status` and live MCP may write state, so run
them only after authorization or in an isolated temporary smoke.

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

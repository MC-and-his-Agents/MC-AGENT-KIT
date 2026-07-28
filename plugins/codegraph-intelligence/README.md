# CodeGraph Intelligence Plugin

This plugin bundles twelve reusable skills for Claude Code and Codex that make [CodeGraph](https://github.com/colbymchenry/codegraph) part of everyday code exploration, planning and review. It prefers CodeGraph MCP tools for structural questions, uses `codegraph_explore` for unfamiliar areas, and falls back to the CodeGraph CLI when MCP tools are unavailable.

CodeGraph remains the runtime dependency. Install it separately and initialize each project you want to query:

```bash
npm install -g @colbymchenry/codegraph
codegraph init -i
```

## Install

| Harness | Support | Native installation |
|---|---|---|
| Codex | Supported | `codex plugin add codegraph-intelligence@mcskills` |
| Claude Code | Supported | `claude plugin install codegraph-intelligence@mcskills` |
| Other harnesses | Not declared | No unverified installation command is provided. |

Add this repository's marketplace before installing:

```bash
# Codex
codex plugin marketplace add MC-and-his-Agents/MC-SKILLS --ref main

# Claude Code
claude plugin marketplace add MC-and-his-Agents/MC-SKILLS
```

The skills below are private plugin components. They are installed and versioned with the plugin and are not published as standalone `npx skills` entries.

## Included skills

| Skill name | Purpose |
|---|---|
| **codegraph-context-bootstrap** | Build repository context before starting work. |
| **impact-analysis** | Analyse the effect of a proposed change on callers, callees, tests and external integrations. |
| **trace-request-flow** | Trace how a request or function travels through the system. |
| **refactor-planner** | Plan safe refactors by identifying public surfaces, dependencies and affected tests. |
| **test-target-finder** | Determine which tests to run after a change. |
| **change-plan-with-graph** | Require a graph-backed plan before any significant code modification. |
| **architecture-map** | Generate a high-level map of the project's architecture and dependencies. |
| **entrypoint-finder** | Locate application entry points such as servers, CLI commands and workers. |
| **bug-localizer** | Narrow down likely locations for a described bug using keyword and call-graph analysis. |
| **dependency-audit** | Inspect module dependencies, detect tight coupling and find cycles. |
| **public-api-guardian** | Evaluate changes to exported APIs and propose safe migration strategies. |
| **dead-code-hunter** | Surface potentially unused code for cleanup, with high- and medium-confidence categories. |

## Auxiliary files

Most skills are intentionally lightweight and only include `SKILL.md`. Higher-risk or repeatable workflows include extra files:

```text
reference/
`-- codegraph-tool-policy.md

skills/<skill-name>/
|-- SKILL.md
|-- reference/       # Decision rules, templates or exclusion checklists
`-- scripts/         # Narrow CLI fallback helpers
```

Current auxiliary files:

| Skill | Auxiliary file | Purpose |
|---|---|---|
| all skills | `reference/codegraph-tool-policy.md` | Centralizes common CodeGraph tool selection, fallback and unavailable handling. |
| `dead-code-hunter` | `reference/false-positive-checklist.md` | Exclude framework hooks, dynamic references, public exports and other common false positives before labeling dead code. |
| `public-api-guardian` | `reference/public-api-rules.md` | Classify public API surfaces, external consumer risk, breaking change levels and migration strategies. |
| `impact-analysis` | `reference/report-template.md` | Standardize impact reports and risk levels. |
| `dependency-audit` | `reference/dependency-rules.md` | Classify inbound/outbound dependencies, coupling signals and cycle severity. |
| `trace-request-flow` | `reference/framework-routing.md` | Identify common route anchors and label observed vs inferred flow edges. |
| `test-target-finder` | `reference/test-selection-rules.md` | Classify minimal, caller and regression tests. |
| `test-target-finder` | `scripts/codegraph-affected.sh` | Wrap `codegraph affected --stdin --json` for CLI fallback. |

## MCP setup

The plugin includes a `.mcp.json` entry for plugin runtimes that can load bundled MCP server config. The server command is:

```json
{
  "codegraph": {
    "type": "stdio",
    "command": "codegraph",
    "args": ["serve", "--mcp"]
  }
}
```

Codex CLI currently loads MCP servers from the global TOML config. If CodeGraph is not already registered for Codex, run:

```bash
codegraph install --target=codex --location=global --yes
```

or add this block to `~/.codex/config.toml`:

```toml
[mcp_servers.codegraph]
command = "codegraph"
args = ["serve", "--mcp"]
```

For Claude Code, the equivalent manual JSON shape is:

```json
{
  "mcpServers": {
    "codegraph": {
      "type": "stdio",
      "command": "codegraph",
      "args": ["serve", "--mcp"]
    }
  }
}
```

## Tool strategy

Use lightweight MCP tools directly in the main session for targeted work:

| Tool | Use for |
|---|---|
| `codegraph_search` | Find symbols by name. |
| `codegraph_callers` / `codegraph_callees` | Trace direct usage and dependencies. |
| `codegraph_impact` | Estimate blast radius before editing. |
| `codegraph_node` | Inspect one symbol without reading a full file. |
| `codegraph_files` | Inspect indexed file structure. |
| `codegraph_status` | Check index health. |

Use `codegraph_context` for focused task context. Use `codegraph_explore` only for broad or unfamiliar areas, preferably after `codegraph_search` has identified concrete symbols or files. After editing files, wait briefly before querying the graph again because the watcher syncs with a short debounce.

## Hook

The plugin provides a `SessionStart` hook that executes `scripts/check-codegraph.sh`. The hook checks whether the CodeGraph CLI is installed and whether the current project contains a `.codegraph` index, then prints status. It never performs heavy indexing itself.

The hook resolves the plugin root from `CODEGRAPH_PLUGIN_ROOT`, then `CLAUDE_PLUGIN_ROOT`. It no longer guesses from the current working directory, because installed plugins may live outside the project root. Runtimes that do not set `CLAUDE_PLUGIN_ROOT` must set `CODEGRAPH_PLUGIN_ROOT` to the installed `codegraph-intelligence` directory for the hook to run. If neither variable is set, the hook prints a skip message and exits successfully.

Example:

```bash
export CODEGRAPH_PLUGIN_ROOT="/absolute/path/to/codegraph-intelligence"
```

The project root is resolved from the hook argument, `CODEX_CWD`, `CODEX_WORKSPACE_DIR`, `CLAUDE_PROJECT_DIR` or the current working directory, with a Git root normalization when available.

## MCP tools

CodeGraph exposes these tools through the MCP server:

- `codegraph_search`
- `codegraph_context`
- `codegraph_explore`
- `codegraph_callers`
- `codegraph_callees`
- `codegraph_impact`
- `codegraph_node`
- `codegraph_files`
- `codegraph_status`

## Usage

After installing the plugin, the skills can be invoked automatically by agents when appropriate, or manually via slash commands (`/codegraph-context-bootstrap`, `/impact-analysis`, etc.). When using the skills, prefer MCP tools for accuracy and use the CLI fallback only when MCP tools are unavailable.

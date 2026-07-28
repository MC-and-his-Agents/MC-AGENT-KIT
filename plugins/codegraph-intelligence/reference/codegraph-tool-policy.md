# CodeGraph Tool Policy

Use this shared policy from every CodeGraph Intelligence skill. Skill-specific files should describe task workflow; this file owns common tool selection, fallback and unavailable handling.

## Availability Check

Start graph-backed work with `codegraph_status` or `codegraph status .`.

- If no index exists, ask the user to run `codegraph init -i` or run it only when the user explicitly wants initialization.
- If the index is stale, prefer `codegraph sync` before relying on graph results.
- After editing files, wait briefly before re-querying because the watcher syncs with a short debounce.

## MCP First

The following eight tools are required by this plugin; it currently declares no optional MCP capabilities. Prefer them when they are available:

- `codegraph_search`: find symbols by name, route, module or short code term.
- `codegraph_explore`: build bounded context for a task or survey an unfamiliar area.
- `codegraph_node`: inspect one symbol's location, signature, export state or source.
- `codegraph_callers` / `codegraph_callees`: trace direct relationships.
- `codegraph_impact`: estimate broader change radius.
- `codegraph_files`: inspect indexed file structure.

## Explore Discipline

Use one bounded `codegraph_explore` call for a cohesive task or unfamiliar area. Use `codegraph_search` and `codegraph_node` for narrow symbol lookups. Anchor explore queries to the task and any known symbols, file names or short code terms.

## CLI Fallback

Use CLI fallback only when MCP tools are unavailable:

- `codegraph query` for symbol search.
- `codegraph context` for focused context.
- `codegraph files` for indexed structure.
- `codegraph affected` for changed-file-to-test mapping.
- `codegraph status` and `codegraph sync` for index health.

When parsing CLI output, state that results may be less structured than MCP output.

## No Graph Available

If neither MCP nor CLI is available, proceed only with conservative local inspection. State that graph-backed analysis could not be performed, avoid high-confidence deletion or breaking-change claims, and keep findings explicitly uncertain.

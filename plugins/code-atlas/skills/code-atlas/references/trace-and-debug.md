# TRACE：请求、符号与 bug 路径

Use this as the primary reference when a user asks how a request, route,
function, event or reported bug travels through a system.

## Workflow

1. Translate the report into route paths, verbs, symbols, error text and
   synonyms. State the starting hypothesis.
2. Search the visible graph or local files for concrete route registrations,
   entrypoints and symbols. Confirm the start node before walking.
3. Follow direct callees for the path; inspect callers when a bug candidate or
   boundary is ambiguous. Use one bounded `codegraph_explore` call only for an
   unfamiliar flow.
4. Separate middleware, controller/handler, service, repository, persistence
   and external calls. Note async boundaries, retries, transactions and error
   handling.
5. Mark each edge **observed**, **inferred** or **unknown**. Dynamic routing,
   reflection, templates, generated code and external services remain unknown
   without direct evidence.
6. Rank bug candidates by direct symptom match, criticality, recent churn and
   blast radius. This lane locates likely causes; it does not fix code.

## Output

Return an ordered path or table with level, component, file/symbol, evidence,
side effects and uncertainty. Include the smallest next verification step (a
file read, reproduction, log or test). Never call `codegraph context` or assume
`codegraph_status` exists.

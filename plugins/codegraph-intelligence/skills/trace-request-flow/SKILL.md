---
name: trace-request-flow
description: Trace a request or function call from entry point through middleware, controllers, services, repositories and external calls using CodeGraph.
metadata:
  internal: true
---

Use this skill when the user asks how a particular request, API call, route or function flows through the system.

Goal: Produce a sequential overview of the call chain, highlighting key abstractions (middleware, controller, service, repository, external integration) and noting asynchronous boundaries.

Required reference:
- Use `reference/framework-routing.md` for route anchors, trace layers and observed/inferred evidence labels.

Shared tool policy:
- Follow `../../reference/codegraph-tool-policy.md` for common CodeGraph tool selection, fallback and unavailable handling.

Task-specific tools:
- Prefer `codegraph_search`, `codegraph_context`, `codegraph_explore`, `codegraph_node`, `codegraph_callers` and `codegraph_callees`.

Workflow:
1. Read `reference/framework-routing.md`.
2. **Identify the starting point**:
   - For web/API requests, search for the route path or HTTP verb using `codegraph_search` or search for framework router registrations.
   - For function calls, search for the function name.
3. Use `codegraph_context` when the route or function is ambiguous. Use `codegraph_explore` only for broad, unfamiliar flows after search has produced concrete anchors.
4. **Confirm the start node** using `codegraph_node` and note its kind (route handler, controller, CLI command).
5. **Walk down the call chain**:
   - Use `codegraph_callees` to retrieve direct callees for each function in the chain.
   - Distinguish middleware, controller, service and repository layers based on naming conventions, directory structure and file location.
   - Include database or external service calls as separate steps.
6. At each step, record the order of calls, note asynchronous boundaries (promises, awaits, event loops), and label edges as observed, inferred or unknown.
7. Present the call chain as an ordered list or table with columns such as level, component, file, evidence, description and external effect.
8. Optionally visualise the flow with a textual diagram if it aids comprehension.
9. Summarise key insights: entry point, major abstractions, side effects, error handling points, external integrations and missing graph coverage.

Rules:
- When using CLI fallback, rely on `codegraph context` to summarise call chains and disambiguate manually with file reading if necessary.
- Avoid exhaustive traversal; limit depth to what is relevant to the user's question.
- Use observed/inferred/unknown evidence labels from `reference/framework-routing.md`.
- Clearly state when parts of the call graph are inferred rather than directly observed in the graph.

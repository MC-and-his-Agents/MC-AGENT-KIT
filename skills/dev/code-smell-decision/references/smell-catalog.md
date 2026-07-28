# Smell Catalog

Use this catalog to interpret discovery evidence. Treat every signal as a candidate until engineering context confirms risk.

## Structural Smells

- Long Function: Many lines, multiple phases, mixed abstraction levels, many branches, or several responsibilities.
- Large Class: Many fields/methods, multiple concepts, mixed responsibilities, or multiple change reasons.
- Long Parameter List: Many primitive parameters, repeated parameter groups, or values that should travel as a concept.
- Data Clump: The same values appear together across calls, constructors, tests, or validation paths.
- Low Cohesion: Functions or fields in a module do not serve a shared purpose.
- Single Responsibility Violation: One unit changes for unrelated reasons.
- Over-Abstraction: Abstraction exists without repeated variation and increases navigation or branching cost.
- Wrong Abstraction: Shared abstraction hides different concepts and accumulates special cases.

## Logic Smells

- Complex Conditional Branching: Deep nesting, boolean expression chains, duplicated decisions, or hard-to-name conditions.
- Magic Number/String: Business rules encoded as literals without names, central definitions, or domain explanation.
- Duplicated Business Rule: Same condition, threshold, mapping, or validation repeated in several places.
- Comment-Masked Complexity: Comments explain complex control flow that should be named or isolated.

## Dependency And Architecture Smells

- High Coupling: Many inbound/outbound dependencies, broad imports, or hard-to-change shared modules.
- Cycle: A dependency cycle between modules, packages, layers, or domains.
- Shotgun Surgery: One conceptual change requires many small edits across unrelated files.
- Divergent Change: One module changes for many unrelated product or technical reasons.
- Implicit Dependency: Hidden reliance on global state, environment, execution order, singleton state, or undeclared conventions.
- Layer Boundary Violation: UI, application, domain, infrastructure, or persistence concerns cross in the wrong direction.
- Domain Boundary Violation: One bounded context directly uses another context's internal model or persistence shape.

## Testability Smells

- Hard Global State: Business logic depends on global mutable state, static singletons, process env, time, random, network, or filesystem.
- Side Effect Mixing: Pure decision logic is mixed with I/O, persistence, messaging, or external calls.
- Constructor Work: Construction performs I/O, registration, networking, or complex validation.
- E2E-Only Core Logic: Important rules can only be tested through slow or brittle end-to-end tests.

## Readability And Expression Smells

- Unclear Naming: Names like `data`, `info`, `obj`, `tmp`, `thing`, `misc`, or names that hide domain meaning.
- Inconsistent Domain Language: Same concept has multiple names or one name means multiple concepts.
- Misleading Comment: Comment says why but code now does something else, or comment compensates for unclear naming.

## False-Positive Risks

- Generated, vendored, snapshot, migration, fixture, and compatibility code may be intentionally repetitive.
- Parsers, serializers, tables, generated clients, and explicit mappers may be clearer when repetitive.
- Low-frequency internal scripts may not justify abstraction.
- Framework entrypoints and configuration files may have unusual shape by design.
- Test setup duplication may be acceptable when it improves scenario readability.

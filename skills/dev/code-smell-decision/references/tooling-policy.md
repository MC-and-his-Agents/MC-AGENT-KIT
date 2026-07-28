# Tooling Policy

Tools collect evidence; the skill makes decisions.

## Preferred Tools

- Use `git` for change frequency, author count, last change, and bugfix-like history.
- Use `rg` for literal text, TODO/FIXME/HACK, environment variable references, global state hints, and comments.
- Use CodeGraph for structural questions: symbols, callers, callees, impact, dependencies, and boundary checks.
- Use project-native tests and coverage reports to assess refactor safety.
- Use language-native analyzers when available, but do not require them.

## Bundled Scripts

- `scan-size-complexity.py`: heuristic size and complexity discovery.
- `scan-duplication.py`: normalized repeated code-window discovery.
- `scan-dependencies.py`: import coupling, simple cycles, and boundary-violation candidates.
- `scan-tests.py`: nearby tests and optional coverage evidence.
- `scan-literals-comments.py`: literal/comment/naming candidate discovery.
- `scan-git-churn.py`: git history evidence.
- `build-evidence-pack.py`: merge scanner outputs.

All bundled scripts must be read-only against the analyzed repository and print JSON to stdout.

## Optional External Enhancements

Use these only when already available or cheap to run:

- JavaScript/TypeScript: `jscpd`, `dependency-cruiser`, `madge`, ESLint, Biome.
- Python: `radon`, `ruff`, `coverage.py`, `vulture`.
- Go: `go test`, `go list`, `golangci-lint`.
- Java/Kotlin: PMD, Checkstyle, SpotBugs, `jdeps`.
- Ruby: RuboCop, `flog`, `flay`.
- Rust: Clippy, `cargo llvm-cov`.

## Fallbacks

- If CodeGraph is unavailable, use `rg`, language tooling, imports, and file structure. Mark structural conclusions as lower confidence.
- If git history is unavailable, mark churn as `unknown`.
- If tests or coverage are unavailable, do not assume unsafe code; report the evidence gap and recommend characterization tests when refactoring is otherwise justified.
- If the target is too large, sample the highest-churn and highest-complexity areas first.

## Non-Mutating Rule

Do not run formatters, code generators, migrations, or fixers that modify tracked files. Do not create issues or branches unless the user explicitly asks.

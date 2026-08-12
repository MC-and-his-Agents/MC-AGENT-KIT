# ASSESS：最小测试选择

Use this reference after a change or impact analysis to recommend tests without
running a full suite by default.

## Selection order

1. List changed files and symbols from the request or `git diff --name-only`.
2. Choose **minimal tests** that directly exercise changed behavior or symbols.
3. Add **caller tests** for direct entrypoints, routes, commands and public
   consumers.
4. Add **regression tests** for shared modules, persistence, external effects,
   boundary changes or incomplete graph coverage.
5. If no reliable mapping exists, say so and escalate to the project-native
   focused suite; do not pretend a broad suite is minimal.

Coverage JSON, nearby test names and CodeGraph impact are evidence only. Mark
the source and confidence. Missing tests do not prove that behavior is unsafe;
they justify characterization tests before a risky refactor.

## Output

For each test, give path/command, why it covers the change and whether it is
minimal, caller or regression. State what was not selected and why. Do not
modify test files or run a test that writes outside the requested worktree.

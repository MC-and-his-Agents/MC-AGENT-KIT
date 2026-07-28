# Issue Template

Create an issue draft only for `Fix Now`, `Refactor Before Next Change`, `Track as Tech Debt`, or `Needs Human Judgment` findings that need an owner decision.

Do not create issue drafts for `Accept / Ignore` unless the user explicitly asks.

```markdown
## Problem

Describe the smell, location, and concrete evidence.

## Engineering Risk

Explain why this is an engineering risk, not just inelegant code.

## Current Decision

Fix Now / Refactor Before Next Change / Track as Tech Debt / Needs Human Judgment

## Debt Classification

code smell / technical debt / intentional technical debt / accidental technical debt / acceptable compromise

## Why Now / Why Not Now

Explain the current timing decision.

## Recommended Action

Describe the smallest behavior-preserving action.

## Testing Requirement

State whether characterization tests, unit tests, integration tests, e2e tests, or regression tests are needed.

## Trigger Conditions

State what event requires revisiting or starting this work.

## Acceptance Criteria

- Existing behavior is preserved.
- Relevant tests pass.
- The targeted complexity, responsibility, dependency, or boundary issue is improved.
- The next related feature can be implemented without expanding the smell.

## Owner Suggestion

Suggest a module owner, domain owner, platform team, or architecture owner.
```

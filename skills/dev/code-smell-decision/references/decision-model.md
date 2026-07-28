# Decision Model

Use this model after discovery evidence exists. Detection says "this may be a smell"; the decision model says whether it matters now.

## Required Classifications

- `code smell`: A maintainability signal exists, but the evidence does not yet prove material engineering risk.
- `technical debt`: The issue already creates maintenance cost, defect risk, delivery drag, or architectural pressure.
- `intentional technical debt`: The team knowingly accepted the debt for a documented reason and has a revisit trigger.
- `accidental technical debt`: The debt accumulated without an explicit decision, owner, or trigger.
- `acceptable compromise`: The design is not ideal, but current risk and change frequency do not justify refactoring.

## Evidence Dimensions

Assess every meaningful finding against these dimensions:

- Change frequency: recent edits, author count, hotfix/rollback history, conflict likelihood.
- Business criticality: billing, payment, auth, permissions, data consistency, security, or user-facing critical flows.
- Impact radius: callers, callees, public APIs, dependent modules, tests, and data flows.
- Cognitive complexity: nested flow, mixed abstraction levels, unclear domain language, and hidden rules.
- Defect risk: branch combinations, missing edge coverage, past fixes, and upcoming feature pressure.
- Test coverage: unit, integration, e2e, snapshot, characterization tests, and coverage evidence.
- Refactor cost: local extraction versus public API, data, migration, or cross-module change.
- Delivery pressure: release urgency, incident response, or short-term milestone constraints.
- Team collaboration: shared ownership, parallel work, hotspot files, and conflict risk.
- Architecture impact: layer violations, dependency direction, bounded context leakage, and wrong abstractions.
- Future expansion: planned features that would amplify the smell.

## Decisions

### Fix Now

Use when risk is high and near-term work will amplify the problem.

Required evidence:

- The code is active, core, high-impact, or defect-prone.
- The minimal fix is behavior-preserving and bounded, or tests can be added first.
- Deferring makes the next change materially more dangerous.

Action guidance:

- Add characterization tests first when behavior is under-specified.
- Keep the public behavior and API stable.
- Prefer extraction, naming, boundary tightening, or responsibility split over redesign.

### Refactor Before Next Change

Use when the code is stable today but the next related change would make the smell substantially worse.

Required evidence:

- Current risk is not urgent.
- A clear future trigger exists.
- Refactoring now has weaker ROI than refactoring just before the next feature.

Action guidance:

- Create or recommend a pre-change issue.
- State the trigger explicitly.
- Keep acceptance criteria tied to enabling the next change safely.

### Track as Tech Debt

Use when the issue is real but not suitable for immediate repair.

Required evidence:

- The smell already imposes cost or risk.
- Immediate repair is blocked by weak tests, high delivery pressure, unclear architecture, high migration cost, or ownership coordination.

Action guidance:

- Label the debt as intentional or accidental.
- State why not now.
- Provide owner suggestion, trigger, and acceptance criteria.

### Accept / Ignore

Use when the smell signal is real but the engineering case for action is weak.

Typical evidence:

- Low change frequency.
- Non-core path.
- Low impact radius.
- Explicit code is safer than abstraction.
- Refactor cost exceeds likely benefit.

Action guidance:

- Explain why it is acceptable now.
- Provide a revisit trigger only if useful.
- Do not create an issue by default.

### Needs Human Judgment

Use when business, roadmap, architecture intent, or ownership is required to decide.

Action guidance:

- Name the missing information.
- Name the likely decision owner or role.
- Provide a temporary recommendation and evidence needed for a final decision.

## Priority

- `P1`: Fix now before continuing related work.
- `P2`: Track or refactor before the next planned change.
- `P3`: Low-risk debt or decision follow-up.
- `P4`: Accept or ignore unless conditions change.

## Hard Rules

- Do not recommend large rewrites unless evidence shows local fixes cannot address the risk.
- Do not call a smell technical debt without explaining the maintenance cost or risk.
- Do not propose refactoring without a testing strategy.
- Do not collapse missing context into certainty; use `Needs Human Judgment`.

# Report Template

Use this shape for the final response. Keep findings focused on decisions, not scanner exhaust.

```markdown
# Code Smell Decision Report

## Summary

- Target:
- Overall maintainability:
- Highest risk areas:
- Findings:
  - Fix Now:
  - Refactor Before Next Change:
  - Track as Tech Debt:
  - Accept / Ignore:
  - Needs Human Judgment:

## Overall Maintainability Assessment

State the main risk pattern, whether immediate refactoring is justified, and whether deeper architecture issues are visible.

## Highest Risk Areas

| Area | Evidence | Risk | Decision |
|---|---|---|---|

## Recommended Priority Items

List the small set of findings that should drive action first.

## Findings

### Finding: {short title}

- ID:
- Location:
- Symbol:
- Smell type:
- Code evidence:
- Detection evidence:
- Engineering evidence:
- Risk:
- Debt classification:
- Decision:
- Priority:
- Why now:
- Why not now:
- Recommended action:
- Minimum safe change:
- Tests needed:
- Create issue:
- Suggested issue title:
- Suggested issue description:
- Acceptance criteria:
- Follow-up trigger:

## Items Not Recommended for Immediate Work

Explain which findings should not be fixed now and why.

## Tech Debt Items

List findings that should be tracked as debt, including triggers and acceptance criteria.

## Needs Human Judgment

List missing business, architecture, ownership, or roadmap inputs.

## Evidence Appendix

List evidence sources: git churn, CodeGraph queries, coverage, tests, complexity scans, duplication scans, and manual review.
```

## Reporting Rules

- Every finding must include why now or why not now.
- Do not include low-value scanner noise.
- Include issue drafts only when the decision warrants follow-up.
- Mark inferred facts as inferred.
- Mark missing context explicitly instead of guessing.

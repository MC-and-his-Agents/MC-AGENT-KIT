---
name: code-smell-decision
description: Analyze code smells in a repository, module, directory, file, symbol, or diff and turn findings into engineering decisions. Use when Codex needs to discover candidate code smells, collect evidence such as git churn, size/complexity, tests, dependencies, CodeGraph context, or literals/comments, then decide whether each issue is Fix Now, Refactor Before Next Change, Track as Tech Debt, Accept / Ignore, or Needs Human Judgment. Use for maintainability reviews, tech debt audits, pre-feature refactor decisions, PR risk reviews, architecture smell triage, and issue draft generation. Default to analysis only; do not modify code, create issues, or perform refactors unless explicitly asked.
metadata:
  version: "0.1.0"
---

# Code Smell Decision

## Purpose

Produce an engineering decision report, not a static analysis log. First discover candidate code smells, then use engineering context to decide whether each finding should be fixed now, deferred until the next change, tracked as debt, accepted, or escalated to humans.

## Core Workflow

1. Resolve the target and scope: repository, module, directory, file, symbol, diff, or changed files.
2. Load `.code-smell-decision.yml` when present. Use `assets/config.example.yml` as the expected shape.
3. Gather discovery evidence:
   - Run `scripts/scan-size-complexity.py` for long functions/classes, parameter count, nesting, branch count, and rough cognitive complexity.
   - Run `scripts/scan-duplication.py` for repeated normalized code windows and duplicated rule candidates.
   - Run `scripts/scan-dependencies.py` for import coupling, simple cycles, and boundary-violation candidates.
   - Run `scripts/scan-tests.py` for nearby tests and optional coverage JSON evidence.
   - Run `scripts/scan-literals-comments.py` for TODO/FIXME/HACK, suspicious literals, and low-confidence naming/comment signals.
   - Run `scripts/scan-git-churn.py` inside Git repositories to collect recent change frequency, authors, and bugfix-like history.
   - Use CodeGraph for structural questions when available: callers, callees, impact, dependency direction, and boundary violations.
   - Use project test/coverage tools only as evidence; do not rewrite code.
4. Build an evidence pack with `scripts/build-evidence-pack.py` when multiple scan outputs exist.
5. Read the relevant references:
   - `references/smell-catalog.md` for smell signals and false-positive risks.
   - `references/decision-model.md` for debt classification and decision rules.
   - `references/tooling-policy.md` for tool choice and fallback behavior.
   - `references/report-template.md` and `references/issue-template.md` when producing final output.
6. Convert evidence into decisions. Every reported finding must have exactly one decision:
   - `Fix Now`
   - `Refactor Before Next Change`
   - `Track as Tech Debt`
   - `Accept / Ignore`
   - `Needs Human Judgment`
7. Output a decision report with evidence, risk, why-now or why-not-now reasoning, minimal safe action, testing need, issue recommendation, acceptance criteria, and follow-up trigger.

## Decision Guardrails

- Do not recommend refactoring because code is merely inelegant.
- Do not assume every code smell is technical debt.
- Do not assume every technical debt item should be paid now.
- Prefer small, behavior-preserving refactors when action is justified.
- If tests are weak, recommend characterization tests before refactoring.
- If business context, architecture intent, ownership, or roadmap is missing, use `Needs Human Judgment`.
- Distinguish `code smell`, `technical debt`, `intentional technical debt`, `accidental technical debt`, and `acceptable compromise`.
- Default to analysis only. Do not edit code, create issues, run mutating formatters, or perform refactors unless the user explicitly requests implementation.

## Script Usage

Example evidence collection:

```bash
python3 scripts/scan-size-complexity.py src/billing
python3 scripts/scan-duplication.py src/billing
python3 scripts/scan-dependencies.py src/billing
python3 scripts/scan-tests.py src/billing
python3 scripts/scan-literals-comments.py src/billing
python3 scripts/scan-git-churn.py src/billing --since "90 days ago"
python3 scripts/build-evidence-pack.py --target src/billing size.json literals.json churn.json
```

Scripts print JSON to stdout and should be treated as evidence collectors only. Their findings are candidates, not final engineering decisions.

## Report Requirements

The report must include:

- Overall maintainability assessment.
- Highest-risk areas.
- Recommended priority items.
- Items not recommended for immediate work and why.
- Items that should be tracked as technical debt.
- For each finding: location, code evidence, smell type, engineering risk, debt classification, decision, priority, recommended action, minimum safe change, testing need, issue recommendation, suggested issue title/description, acceptance criteria, and follow-up trigger.

Use `references/report-template.md` for the final structure.

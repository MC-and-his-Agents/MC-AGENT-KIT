# ASSESS：maintainability 与工程决策

Use this as the primary reference for smell discovery, code-quality review,
technical-debt triage and pre-change maintainability decisions. Scanner output is
candidate evidence; the final result is one decision per meaningful finding.

## Evidence dimensions

Assess the smallest useful set of dimensions and label each fact observed,
inferred or unknown:

- change frequency, authors, hotfix/rollback history and conflict likelihood;
- business criticality (billing, auth, permissions, consistency, security and
  user-facing paths);
- impact radius (callers, callees, public APIs, dependent modules, tests and
  data flow);
- cognitive complexity (branching, nesting, mixed abstraction levels and hidden
  rules);
- defect risk and edge-case coverage;
- unit, integration, e2e, characterization and coverage evidence;
- refactor cost, delivery pressure, collaboration/ownership and architecture
  direction;
- planned features that could amplify the issue.

## Smell catalog

Treat these as signals, not verdicts: long function/class, long parameter list,
data clump, low cohesion, single-responsibility violation, over/wrong
abstraction, complex conditionals, magic numbers/strings, duplicated business
rules, comment-masked complexity, high coupling/fan-in, dependency cycle,
shotgun surgery, divergent change, implicit global dependency, layer/domain
boundary violation, hard global state, mixed side effects, constructor work,
E2E-only core logic, unclear naming, inconsistent domain language and misleading
comments.

Filter generated, vendored, snapshots, migrations, fixtures, serializers,
parsers, explicit mappers, framework entrypoints and readable test setup before
raising a finding. Aesthetic inelegance alone is not debt.

## Decisions

Every finding gets exactly one:

- **Fix Now** — active/high-impact or defect-prone; a bounded behavior-preserving
  fix or characterization test makes deferral materially riskier.
- **Refactor Before Next Change** — stable today, but a named upcoming change
  would amplify the smell; state the trigger and pre-change acceptance criteria.
- **Track as Tech Debt** — real cost/risk exists, but weak tests, delivery
  pressure, migration cost, ownership or architecture uncertainty blocks repair;
  state intentional vs accidental debt, owner, trigger and acceptance criteria.
- **Accept / Ignore** — low frequency/impact or explicit code is safer than an
  abstraction; do not create an issue by default.
- **Needs Human Judgment** — business intent, roadmap, ownership or architecture
  context is missing; name who must decide and what evidence is needed.

Use priorities P1 (before related work), P2 (next planned change), P3 (low-risk
follow-up) and P4 (accept unless conditions change). Do not propose rewrites
unless local fixes cannot address demonstrated risk. Keep public behavior stable
and include a testing strategy.

## Report shape

Include target, overall maintainability, highest-risk areas, prioritized findings,
items not recommended now, tech-debt triggers, human decisions and evidence
sources. Each finding includes location/symbol, smell and detection evidence,
engineering evidence, risk, debt classification, decision, priority, why
now/why not, smallest safe action, tests, issue recommendation, acceptance
criteria and follow-up trigger. Suggested issue text is a draft only; default is
not to create or send an issue.

The bundled JSON schemas under `assets/` define machine-readable evidence-pack
and decision-report fields. The seven Python scanners are read-only and print
JSON to stdout; do not redirect them into the analyzed repository unless the
user explicitly chooses a safe output path.

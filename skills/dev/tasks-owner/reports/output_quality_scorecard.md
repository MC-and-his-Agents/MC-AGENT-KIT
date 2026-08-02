# Output Quality Scorecard

This v0 scorecard compares static without-skill and with-skill outputs using assertion grading.

- Cases: `20`
- Baseline pass rate: `0.0`
- With-skill pass rate: `100.0`
- Delta: `100.0`
- Regressions: `0`
- Blind A/B pairs: `20`
- Gate pass: `True`

Blind review artifacts are generated separately so reviewers can inspect A/B outputs without seeing the answer key.
Run output review adjudication after reviewer decisions are recorded; pending cases should stay pending rather than being counted as human agreement.

## Case Results

| Case | Baseline | With Skill | Delta | Winner | Failed With-Skill Assertions |
| --- | ---: | ---: | ---: | --- | --- |
| flat-mode-contract | 0.0 | 100.0 | 100.0 | with_skill | None |
| hierarchical-mode-contract | 0.0 | 100.0 | 100.0 | with_skill | None |
| missing-github-truth | 0.0 | 100.0 | 100.0 | with_skill | None |
| automation-consent | 0.0 | 100.0 | 100.0 | with_skill | None |
| file-backed-scheduling | 0.0 | 100.0 | 100.0 | with_skill | None |
| direct-mode-contract | 0.0 | 100.0 | 100.0 | with_skill | None |
| luna-v1-consent | 0.0 | 100.0 | 100.0 | with_skill | None |
| luna-adjustment | 0.0 | 100.0 | 100.0 | with_skill | None |
| existing-task-contract-gate | 0.0 | 100.0 | 100.0 | with_skill | None |
| inspection-owner-action-required | 0.0 | 100.0 | 100.0 | with_skill | None |
| stale-release-rejected | 0.0 | 100.0 | 100.0 | with_skill | None |
| event-key-dedup | 0.0 | 100.0 | 100.0 | with_skill | None |
| dynamic-ready-wave | 0.0 | 100.0 | 100.0 | with_skill | None |
| owner-budget-boundary | 0.0 | 100.0 | 100.0 | with_skill | None |
| workspace-entry-admission | 0.0 | 100.0 | 100.0 | with_skill | None |
| one-off-owner-perspective | 0.0 | 100.0 | 100.0 | with_skill | None |
| completed-closeout-gate | 0.0 | 100.0 | 100.0 | with_skill | None |
| automation-correction-cannot-dispatch | 0.0 | 100.0 | 100.0 | with_skill | None |
| release-ack-required | 0.0 | 100.0 | 100.0 | with_skill | None |
| max-inflight-cap-resolution | 0.0 | 100.0 | 100.0 | with_skill | None |

## Failure Taxonomy

- No with-skill assertion failures.

## Next Fixes

- Add holdout cases before using this as a release gate.
- Promote repeated failed assertions into the output-risk profile.
- Keep assertions tied to material deliverables, not phrasing trivia.

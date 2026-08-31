#!/usr/bin/env python3
"""Validate structured Tasks Owner lifecycle traces without parsing prose."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from tasks_owner_trajectory_replay import evaluate
from tasks_owner_trajectory_schema import RULES, schema_errors as _schema_errors


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "skills/dev/tasks-owner/evals/trajectory_cases.jsonl"


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: case must be an object")
        value["_line"] = line_number
        cases.append(value)
    return cases


def run(path: Path) -> list[str]:
    failures: list[str] = []
    cases = load_cases(path)
    ids: set[str] = set()
    coverage = {rule: {"pass": 0, "fail": 0} for rule in RULES}
    modes: set[str] = set()
    for raw in cases:
        line = raw.pop("_line")
        case_id = raw.get("id")
        schema = _schema_errors(raw)
        if schema:
            failures.append(f"line {line}: schema: {'; '.join(schema)}")
            continue
        if case_id in ids:
            failures.append(f"line {line}: duplicate id {case_id}")
            continue
        ids.add(case_id)
        modes.add(raw["mode"])
        expected = raw["expected"]
        violations = evaluate(raw)
        verdict = "fail" if violations else "pass"
        coverage[expected["rule_id"]][expected["verdict"]] += 1
        if verdict != expected["verdict"] or (verdict == "fail" and expected["rule_id"] not in violations):
            failures.append(f"line {line} {case_id}: expected {expected}, got {verdict} {sorted(violations)}")
    for rule, counts in coverage.items():
        if not counts["pass"] or not counts["fail"]:
            failures.append(f"coverage: {rule} requires pass and fail cases")
    if not {"app_thread", "direct", "convergence", "cleanup", "heartbeat", "review"}.issubset(modes):
        failures.append("coverage: all trajectory modes are required")
    return failures


def self_test(path: Path) -> list[str]:
    cases = [case for case in load_cases(path) if not case.pop("_line") is None]
    failures: list[str] = []
    mutations = [
        ("canonical_delivery", "delivery-pass", lambda c: c["events"][-1].update(tool="final")),
        ("writer_quiescence", "writer-pass", lambda c: c["events"][1]["facts"].update(host_status="running", write_authority="active")),
        ("cleanup_terminal_consumed", "cleanup-pass", lambda c: c["events"][3]["facts"].update(owner_consumption="pending")),
        ("direct_wake", "direct-pass", lambda c: c["events"][2].update(turn="owner-turn-2")),
        ("direct_wake", "direct-pass", lambda c: c["events"][0]["args"].update(model="gpt-5.6-terra")),
        ("heartbeat_backoff", "heartbeat-pass", lambda c: c["events"][4]["facts"].update(current_interval_seconds=1)),
        ("review_disposition", "review-multifinding-single-round-pass", lambda c: c["events"][1]["facts"].update(disposition="defer", carrier_locator="none")),
        ("review_disposition", "review-p2-defer-with-carrier-pass", lambda c: c["events"][1]["facts"].update(carrier_locator="none")),
        ("review_disposition", "review-multifinding-single-round-pass", lambda c: c["events"][4]["facts"].update(task_key="issue-107")),
    ]
    for rule, case_id, mutate in mutations:
        source = next(case for case in cases if case["id"] == case_id)
        candidate = copy.deepcopy(source)
        mutate(candidate)
        if rule not in evaluate(candidate):
            failures.append(f"mutation for {rule} was not rejected")

    source = next(case for case in cases if case["id"] == "writer-pass")
    for label, mutate in (
        ("authority inversion", lambda facts: facts["verification_authority"].update(effective_source="skill_default", effective_locator="skill:tasks-owner")),
        ("missing acceptance", lambda facts: facts.update(acceptance_evidence_locator="none")),
        ("required check wrong head", lambda facts: facts["check_results"][0].update(head="head-other")),
        ("reuse tree mismatch", lambda facts: facts["verification_reuse"].update(evidence_tree_digest="tree:other")),
        ("reuse acceptance mismatch", lambda facts: facts["verification_reuse"].update(evidence_acceptance_digest="acceptance:other")),
        ("reuse environment mismatch", lambda facts: facts["verification_reuse"].update(evidence_environment_class="env:other")),
        ("product not ready", lambda facts: facts.update(product_readiness="blocked")),
        ("stale PR metadata", lambda facts: facts["pr_metadata"].update(head="head-old")),
        ("unrelated failure blocks product", lambda facts: facts["unrelated_check_failures"][0].update(native_dependency_created=True)),
        ("unproven security requirement", lambda facts: facts["verification_authority"]["security_contract"].update(locator="security:contract", required_checks=["security-scan"])),
    ):
        candidate = copy.deepcopy(source)
        mutate(candidate["events"][-1]["facts"])
        if "writer_quiescence" not in evaluate(candidate):
            failures.append(f"verification {label} mutation was not rejected")

    source = next(case for case in cases if case["id"] == "app-quiesce-verified-pass")
    candidate = copy.deepcopy(source)
    candidate["events"][-1]["facts"]["check_results"][0]["status"] = "failed"
    if "writer_quiescence" not in evaluate(candidate):
        failures.append("authority-required Hosted failure was not rejected")
    candidate = copy.deepcopy(source)
    candidate["events"][-1]["facts"]["verification_authority"]["branch_protection"]["locator"] = "none"
    if "writer_quiescence" not in evaluate(candidate):
        failures.append("branch-protection check without source locator was not rejected")
    source = next(case for case in cases if case["id"] == "writer-pass")
    candidate = copy.deepcopy(source)
    candidate["events"][4]["facts"]["tree_digest"] = "missing"
    if "writer_quiescence" not in evaluate(candidate):
        failures.append("head readback without real tree digest was not rejected")
    candidate = copy.deepcopy(source)
    candidate["events"][-1]["facts"]["verification_authority"]["branch_protection"] = {
        "locator": "branch-protection:main",
        "required_checks": ["repository-contracts"],
    }
    if evaluate(candidate):
        failures.append("same required check across authorities was incorrectly blocked")

    # A ship verdict cannot hide a finding that never received a disposition.
    source = next(case for case in cases if case["id"] == "review-p2-defer-with-carrier-pass")
    candidate = copy.deepcopy(source)
    candidate["events"] = candidate["events"][:1]
    candidate["events"][0]["facts"].update(verdict="ship", finding_locators=["f-p2"])
    if "review_disposition" not in evaluate(candidate):
        failures.append("unresolved ship finding mutation was not rejected")

    # user_decision needs a locator for the real product/permission/external decision.
    source = next(case for case in cases if case["id"] == "review-user-decision-with-locator-pass")
    for sentinel in ("none", "missing", "unknown", "tbd"):
        candidate = copy.deepcopy(source)
        candidate["events"][1]["facts"]["user_decision_locator"] = sentinel
        if "review_disposition" not in evaluate(candidate):
            failures.append(f"user decision locator sentinel {sentinel} was not rejected")
    for label, mutate in (
        ("authority", lambda facts: facts.pop("decision_boundary_locator")),
        ("safe default", lambda facts: facts.update(safe_reversible_default_available=True)),
        ("mechanical action", lambda facts: facts.update(requires_user_judgment=False)),
    ):
        candidate = copy.deepcopy(source)
        mutate(candidate["events"][1]["facts"])
        if "review_disposition" not in evaluate(candidate):
            failures.append(f"user decision {label} mutation was not rejected")

    # The shared repair budget is explicit and bound to a convergence chain.
    source = next(case for case in cases if case["id"] == "review-multifinding-single-round-pass")
    candidate = copy.deepcopy(source)
    candidate["initial"].pop("repair_budget")
    if not _schema_errors(candidate):
        failures.append("missing convergence repair budget was not rejected")

    source = next(case for case in cases if case["id"] == "review-scope-split-new-chain-pass")
    candidate = copy.deepcopy(source)
    candidate["events"][2]["facts"]["to_convergence_chain_locator"] = "chain:issue-split"
    if "review_disposition" not in evaluate(candidate):
        failures.append("same-chain fake split reset mutation was not rejected")
    for label, mutate in (
        ("evidence sentinel", lambda facts: facts.update(evidence_locator="none")),
        ("new-chain sentinel", lambda facts: facts.update(to_convergence_chain_locator="none")),
        ("missing trigger", lambda facts: facts.pop("trigger_finding_locator")),
    ):
        candidate = copy.deepcopy(source)
        mutate(candidate["events"][2]["facts"])
        if "review_disposition" not in evaluate(candidate):
            failures.append(f"scope transition {label} mutation was not rejected")
    candidate = copy.deepcopy(source)
    candidate["events"] = candidate["events"][:3]
    if "review_disposition" not in evaluate(candidate):
        failures.append("scope transition without fresh new-chain review was not rejected")

    source = next(case for case in cases if case["id"] == "review-reassign-with-mismatch-pass")
    candidate = copy.deepcopy(source)
    candidate["events"][2]["facts"].pop("mismatch_locator")
    if "review_disposition" not in evaluate(candidate):
        failures.append("reassign without capability or ownership mismatch evidence was not rejected")

    candidate = copy.deepcopy(source)
    candidate["initial"]["repair_budget"]["convergence_chain_locator"] = "none"
    if not _schema_errors(candidate):
        failures.append("sentinel convergence chain was not rejected")
    candidate = copy.deepcopy(source)
    candidate["initial"]["repair_budget"]["repair_evidence_locators"] = ["none"]
    if not _schema_errors(candidate):
        failures.append("sentinel repair evidence was not rejected")

    # A second finding-driven write must fail even when the reviewer and generation
    # change.  This is the mutation form of the generation-wide circuit breaker.
    source = next(case for case in cases if case["id"] == "review-multifinding-single-round-pass")
    candidate = copy.deepcopy(source)
    candidate["events"][4]["facts"].update(
        verdict="fix-first",
        reviewer_locator="reviewer:b",
        execution_generation="g2",
        finding_locators=["f3"],
    )
    candidate["events"].append({
        "seq": 6,
        "turn": "owner-turn-2",
        "actor": "owner",
        "kind": "finding_disposition",
        "locator": "finding:mutation-f3",
        "unit_id": None,
        "generation": "g2",
        "tool": "reviewer_result",
        "args": {},
        "facts": {
            "finding_locator": "f3",
            "severity": "P1",
            "acceptance_or_invariant_locator": "done:consumer",
            "current_outcome_unsafe_without_fix": True,
            "unsafe_evidence_locator": "risk:f3",
            "disposition": "fix_now",
            "carrier_locator": "none",
            "rejection_basis": "none",
            "boundary_expansion": "none",
            "task_key": "issue-106",
            "scope_revision": "s1",
            "reviewed_head": "h1",
            "reviewer_locator": "reviewer:b",
            "execution_generation": "g2",
            "blocker_class": "new-class",
        },
    })
    candidate["events"].append({
        "seq": 7,
        "turn": "owner-turn-2",
        "actor": "owner",
        "kind": "review_write",
        "locator": "write:mutation-round-2",
        "unit_id": None,
        "generation": "g2",
        "tool": "git_commit",
        "args": {},
        "facts": {
            "task_key": "issue-106",
            "scope_revision": "s1",
            "execution_generation": "g2",
            "base_reviewed_head": "h1",
            "new_head": "h2",
            "finding_locators": ["f3"],
            "writer_evidence_locator": "writer:g2:r2",
            "writer_quiescence": "verified",
            "boundary_expansion": "none",
        },
    })
    if "review_disposition" not in evaluate(candidate):
        failures.append("review generation/reviewer reset mutation was not rejected")
    schema_case = copy.deepcopy(cases[0])
    schema_case["events"][0]["kind"] = "noop"
    if not _schema_errors(schema_case):
        failures.append("unknown event kind was not rejected")
    schema_case = copy.deepcopy(cases[0])
    schema_case["events"][0]["seq"] = 2
    if not _schema_errors(schema_case):
        failures.append("non-contiguous seq was not rejected")
    schema_case = copy.deepcopy(cases[0])
    schema_case["events"][1]["locator"] = schema_case["events"][0]["locator"]
    if not _schema_errors(schema_case):
        failures.append("duplicate locator was not rejected")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        failures = self_test(args.path) if args.self_test else run(args.path)
    except (OSError, TypeError, StopIteration, ValueError, json.JSONDecodeError) as exc:
        failures = [str(exc)]
    for failure in failures:
        print(f"error: {failure}")
    if not failures:
        print("Tasks Owner trajectory self-test passed." if args.self_test else "Tasks Owner trajectory validation passed.")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())

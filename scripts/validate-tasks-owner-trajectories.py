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

    source = next(case for case in cases if case["id"] == "delivery-pass")
    candidate = copy.deepcopy(source)
    for event in candidate["events"]:
        event["seq"] += 1
    local = copy.deepcopy(candidate["events"][0])
    local.update(seq=1, locator="delivery:local", tool="final", args={})
    local["facts"] = {
        "event": "STARTED",
        "event_key": "task-1:g1:STARTED",
        "delivery_state": "local_recorded",
        "route_status": "STARTED_LOCAL_RECORDED",
        "message_locator": "missing",
        "recorded_at": "2026-08-10T09:59:59Z",
    }
    candidate["events"].insert(0, local)
    if evaluate(candidate):
        failures.append("valid local_recorded delivery state was rejected")

    source = next(case for case in cases if case["id"] == "delivery-pass")
    for sentinel in ("none", "missing", "unknown", "null", "n/a", "na", "tbd"):
        candidate = copy.deepcopy(source)
        for event in candidate["events"]:
            if event.get("kind") == "delivery" and event.get("facts", {}).get("delivery_state") in {"delivered", "owner_verified", "consumed"}:
                event["facts"]["message_locator"] = sentinel
        if "canonical_delivery" not in evaluate(candidate):
            failures.append(f"delivered message locator sentinel {sentinel} was not rejected")
    for state, field in (("owner_verified", "verified_at"), ("consumed", "consumed_at")):
        candidate = copy.deepcopy(source)
        next(event for event in candidate["events"] if event.get("facts", {}).get("delivery_state") == state)["facts"][field] = "none"
        if "canonical_delivery" not in evaluate(candidate):
            failures.append(f"delivery {field} sentinel was not rejected")

    for case_id, rule in (("writer-pass", "writer_quiescence"), ("cleanup-pass", "cleanup_terminal_consumed"), ("direct-pass", "direct_wake")):
        source = next(case for case in cases if case["id"] == case_id)
        for sentinel in ("none", "missing", "unknown", "null", "n/a", "na", "tbd"):
            candidate = copy.deepcopy(source)
            for event in candidate["events"]:
                if event.get("kind") in {"completion", "completion_consumed"}:
                    event["facts"]["completion_locator"] = sentinel
            if rule not in evaluate(candidate):
                failures.append(f"{case_id} completion locator sentinel {sentinel} was not rejected")

    source = next(case for case in cases if case["id"] == "direct-pass")
    live = copy.deepcopy(source)
    live["source_kind"] = "live_readback"
    live["evidence"] = {
        "host_id": "host:local",
        "observed_at": "2026-08-10T10:01:00Z",
        "owner_turn_locator": "turn:owner-1",
        "runtime_locator": "runtime:luna-max",
        "tool_readback_locator": "tool:native-completion-wake",
    }
    live["events"] = [event for event in live["events"] if not (event["kind"] == "unit_state" and event["facts"].get("host_status") == "terminal")]
    wake = {
        "seq": 5, "turn": "owner-turn-1", "actor": "owner", "kind": "wake_verified",
        "locator": "direct:wake", "unit_id": "child-1", "generation": "g1",
        "tool": "native_completion_wake", "args": {},
        "facts": {
            "native_completion_wake": "verified", "wake_locator": "wake:child-1",
            "host_id": "host:local", "observed_at": "2026-08-10T10:01:00Z",
            "tool_result_locator": "tool-result:wake-child-1",
        },
    }
    live["events"].insert(4, wake)
    if evaluate(live):
        failures.append("valid live native completion wake was rejected")
    for field in ("wake_locator", "host_id", "observed_at", "tool_result_locator"):
        candidate = copy.deepcopy(live)
        next(event for event in candidate["events"] if event["kind"] == "wake_verified")["facts"][field] = "none"
        if "direct_wake" not in evaluate(candidate):
            failures.append(f"live wake {field} sentinel was not rejected")

    source = next(case for case in cases if case["id"] == "heartbeat-pass")
    for field in ("state_digest", "user_feedback_revision", "external_fact_revision"):
        candidate = copy.deepcopy(source)
        for event in candidate["events"]:
            if event.get("kind") == "heartbeat":
                event["facts"][field] = "missing"
        if "heartbeat_backoff" not in evaluate(candidate):
            failures.append(f"heartbeat sentinel {field} was not rejected")
    candidate = copy.deepcopy(source)
    next(event for event in candidate["events"] if event.get("kind") == "automation_readback")["facts"]["automation_locator"] = "missing"
    if "heartbeat_backoff" not in evaluate(candidate):
        failures.append("automation readback locator sentinel was not rejected")

    source = next(case for case in cases if case["id"] == "writer-pass")
    for mutation in ("unit_event", "review_writer"):
        candidate = copy.deepcopy(source)
        if mutation == "unit_event":
            next(event for event in candidate["events"] if event["kind"] == "unit_state" and event["facts"].get("host_status") == "terminal")["locator"] = "none"
        else:
            review = next(event for event in candidate["events"] if event["kind"] == "fresh_review")
            review["facts"]["writer_evidence_locator"] = "none"
            review["facts"]["writer_evidence_locators"] = ["none"]
        if "schema" not in evaluate(candidate) and "writer_quiescence" not in evaluate(candidate):
            failures.append(f"publication sentinel {mutation} was not rejected")

    source = next(case for case in cases if case["id"] == "writer-pass")
    candidate = copy.deepcopy(source)
    second_writer = copy.deepcopy(candidate["events"][0])
    for event in candidate["events"][1:]:
        event["seq"] += 1
    second_writer.update(seq=2, locator="thread:writer-2", unit_id="writer-2")
    second_writer["facts"].update(runtime_locator="runtime:writer-2")
    candidate["events"].insert(1, second_writer)
    if "writer_quiescence" not in evaluate(candidate):
        failures.append("second writer cardinality mutation was not rejected")

    source = next(case for case in cases if case["id"] == "cleanup-pass")
    candidate = copy.deepcopy(source)
    for event in candidate["events"]:
        if event.get("unit_id") == "writer-1":
            event["unit_id"] = "none"
        if event.get("kind") == "handoff":
            event["facts"]["active_locators"] = ["none"]
    if "schema" not in evaluate(candidate):
        failures.append("cleanup unit identity sentinel was not rejected")
    for field in ("merge_commit", "target_head", "issue_state_locator"):
        candidate = copy.deepcopy(source)
        next(event for event in candidate["events"] if event["kind"] == "closeout")["facts"][field] = "none"
        if "cleanup_terminal_consumed" not in evaluate(candidate):
            failures.append(f"cleanup closeout {field} sentinel was not rejected")
    for target in ("/repo/sub", "/repo/.codex", "/repo/../repo2"):
        candidate = copy.deepcopy(source)
        spawn = next(event for event in candidate["events"] if event["kind"] == "cleanup_spawn")
        spawn["args"]["target_worktree"] = target
        if "cleanup_terminal_consumed" not in evaluate(candidate):
            failures.append(f"unsafe or identity-mismatched cleanup target {target} was not rejected")
    for field in ("target_repository", "target_worktree", "target_ref", "target_oid", "identity_readback_locator"):
        candidate = copy.deepcopy(source)
        readback = next(event for event in candidate["events"] if event["kind"] == "cleanup_readback")
        readback["facts"][field] = "missing"
        if "cleanup_terminal_consumed" not in evaluate(candidate):
            failures.append(f"cleanup identity {field} sentinel was not rejected")

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

    source = next(case for case in cases if case["id"] == "review-multifinding-single-round-pass")
    for field in ("acceptance_or_invariant_locator", "unsafe_evidence_locator"):
        candidate = copy.deepcopy(source)
        candidate["events"][1]["facts"][field] = "unknown"
        if "review_disposition" not in evaluate(candidate):
            failures.append(f"review {field} sentinel was not rejected")
    candidate = copy.deepcopy(next(case for case in cases if case["id"] == "review-p2-defer-with-carrier-pass"))
    candidate["events"][0]["facts"]["finding_locators"] = ["none"]
    candidate["events"][1]["facts"]["finding_locator"] = "none"
    if "review_disposition" not in evaluate(candidate):
        failures.append("review finding locator sentinel was not rejected")

    # A negative disposition cannot hide a finding that makes the current
    # acceptance-mapped outcome unsafe. Scope dispositions need a real transition.
    source = next(case for case in cases if case["id"] == "review-p2-defer-with-carrier-pass")
    for disposition in ("defer", "reject"):
        candidate = copy.deepcopy(source)
        facts = candidate["events"][1]["facts"]
        facts.update(
            severity="P1",
            acceptance_or_invariant_locator="done:consumer",
            current_outcome_unsafe_without_fix=True,
            unsafe_evidence_locator="risk:unsafe-consumer",
            disposition=disposition,
            rejection_basis="not-applicable" if disposition == "reject" else "none",
        )
        if "review_disposition" not in evaluate(candidate):
            failures.append(f"unsafe acceptance-mapped {disposition} mutation was not rejected")
    candidate = copy.deepcopy(source)
    candidate["events"][1]["facts"].update(
        severity="P1",
        acceptance_or_invariant_locator="done:consumer",
        current_outcome_unsafe_without_fix=True,
        unsafe_evidence_locator="risk:unsafe-consumer",
        disposition="split",
    )
    if "review_disposition" not in evaluate(candidate):
        failures.append("unsafe split without authoritative scope transition was not rejected")

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

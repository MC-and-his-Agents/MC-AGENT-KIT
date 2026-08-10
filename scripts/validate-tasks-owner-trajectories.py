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
    if not {"app_thread", "direct", "convergence", "cleanup", "heartbeat"}.issubset(modes):
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
    ]
    for rule, case_id, mutate in mutations:
        source = next(case for case in cases if case["id"] == case_id)
        candidate = copy.deepcopy(source)
        mutate(candidate)
        if rule not in evaluate(candidate):
            failures.append(f"mutation for {rule} was not rejected")
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

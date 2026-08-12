#!/usr/bin/env python3
"""Merge scanner JSON reports into a code smell evidence pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_report(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"scanner": path.as_posix(), "error": f"invalid JSON: {exc}", "findings": []}
    except OSError as exc:
        return {"scanner": path.as_posix(), "error": str(exc), "findings": []}


def normalize_finding(raw: dict, scanner: str, index: int) -> dict:
    finding = dict(raw)
    finding.setdefault("id", f"{scanner}-{index:04d}".replace(" ", "-"))
    finding.setdefault("confidence", "unknown")
    finding.setdefault("type", ["Unknown"])
    if isinstance(finding["type"], str):
        finding["type"] = [finding["type"]]
    finding.setdefault("location", {})
    finding["source_scanner"] = scanner
    return finding


def matching_file_evidence(file_path: str, evidence_by_file: dict[str, dict]) -> dict | None:
    if file_path in evidence_by_file:
        return evidence_by_file[file_path]
    normalized = file_path.lstrip("./")
    if normalized in evidence_by_file:
        return evidence_by_file[normalized]
    for candidate, evidence in evidence_by_file.items():
        normalized_candidate = candidate.lstrip("./")
        if normalized.endswith("/" + normalized_candidate) or normalized_candidate.endswith("/" + normalized):
            return evidence
    return None


def merge_churn(findings: list[dict], churn_reports: list[dict]) -> None:
    churn_by_file: dict[str, dict] = {}
    for report in churn_reports:
        for item in report.get("findings", []):
            file_path = item.get("file")
            if file_path:
                churn_by_file[file_path] = item

    for finding in findings:
        location = finding.get("location", {})
        file_path = location.get("file")
        if not file_path:
            continue
        churn = matching_file_evidence(file_path, churn_by_file)
        if churn is None:
            continue
        engineering = dict(finding.get("engineering_evidence", {}))
        engineering.update(
            {
                "changes": churn.get("changes"),
                "authors": churn.get("authors"),
                "last_changed": churn.get("last_changed"),
                "bugfix_like_commits": churn.get("bugfix_like_commits"),
            }
        )
        finding["engineering_evidence"] = engineering


def merge_tests(findings: list[dict], test_reports: list[dict]) -> None:
    tests_by_file: dict[str, dict] = {}
    for report in test_reports:
        for item in report.get("findings", []):
            location = item.get("location", {})
            file_path = location.get("file")
            if file_path:
                tests_by_file[file_path] = item.get("engineering_evidence", {})

    for finding in findings:
        location = finding.get("location", {})
        file_path = location.get("file")
        if not file_path:
            continue
        test_evidence = matching_file_evidence(file_path, tests_by_file)
        if test_evidence is None:
            continue
        engineering = dict(finding.get("engineering_evidence", {}))
        engineering.update(test_evidence)
        finding["engineering_evidence"] = engineering


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Analyzed target name/path.")
    parser.add_argument("reports", nargs="+", help="Scanner JSON report files.")
    args = parser.parse_args()

    source_reports = [load_report(Path(path)) for path in args.reports]
    findings: list[dict] = []
    churn_reports: list[dict] = []
    test_reports: list[dict] = []

    for report in source_reports:
        scanner = report.get("scanner", "unknown-scanner")
        if scanner == "scan-git-churn":
            churn_reports.append(report)
            continue
        if scanner == "scan-tests":
            test_reports.append(report)
            continue
        for index, raw in enumerate(report.get("findings", []), start=1):
            findings.append(normalize_finding(raw, scanner, index))

    merge_churn(findings, churn_reports)
    merge_tests(findings, test_reports)

    counts_by_decision_input: dict[str, int] = {}
    for finding in findings:
        for smell_type in finding.get("type", []):
            counts_by_decision_input[smell_type] = counts_by_decision_input.get(smell_type, 0) + 1

    pack = {
        "target": args.target,
        "generated_by": "build-evidence-pack",
        "summary": {
            "source_reports": len(source_reports),
            "findings": len(findings),
            "types": counts_by_decision_input,
        },
        "findings": findings,
        "source_reports": [
            {
                "scanner": report.get("scanner", "unknown-scanner"),
                "summary": report.get("summary", {}),
                "error": report.get("error"),
            }
            for report in source_reports
        ],
    }
    print(json.dumps(pack, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

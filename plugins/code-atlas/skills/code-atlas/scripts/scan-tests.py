#!/usr/bin/env python3
"""Collect read-only evidence about nearby tests and optional coverage JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".kts", ".go", ".rs", ".rb", ".php", ".cs", ".swift"}
TEST_HINTS = ("test", "tests", "spec", "__tests__")


def iter_source_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_file() and path.suffix in SOURCE_EXTENSIONS:
            files.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix in SOURCE_EXTENSIONS:
                    if set(child.parts).intersection({"node_modules", "vendor", "dist", "build", ".git"}):
                        continue
                    files.append(child)
    return sorted(files)


def is_test_file(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    stem = path.stem.lower()
    if any(part in TEST_HINTS for part in parts):
        return True
    return (
        stem.startswith("test_")
        or stem.endswith("_test")
        or stem.endswith(".test")
        or stem.endswith("_spec")
        or stem.endswith(".spec")
    )


def all_test_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for child in root.rglob("*"):
        if child.is_file() and child.suffix in SOURCE_EXTENSIONS and is_test_file(child):
            if set(child.parts).intersection({"node_modules", "vendor", "dist", "build", ".git"}):
                continue
            files.append(child)
    return sorted(files)


def relative_to_root(path: Path, root: Path) -> Path:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return path


def related_tests(source: Path, tests: list[Path], root: Path) -> list[str]:
    relative_source = relative_to_root(source, root)
    source_stem = source.stem.replace(".test", "").replace(".spec", "")
    candidates = []
    source_parts = set(relative_source.with_suffix("").parts)
    for test in tests:
        relative_test = relative_to_root(test, root)
        test_name = relative_test.as_posix()
        stem = test.stem
        if source_stem and source_stem in stem:
            candidates.append(test_name)
            continue
        test_parts = set(relative_test.with_suffix("").parts)
        if len(source_parts.intersection(test_parts)) >= 2:
            candidates.append(test_name)
    return sorted(set(candidates))[:20]


def load_coverage(path: str | None) -> dict:
    if not path:
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


def coverage_for_file(coverage: dict, source: Path) -> float | None:
    if not coverage or coverage.get("error"):
        return None
    source_posix = source.as_posix()
    files = coverage.get("files", {})
    for key, value in files.items():
        if key.endswith(source_posix) or source_posix.endswith(key):
            summary = value.get("summary", {})
            percent = summary.get("percent_covered")
            if isinstance(percent, (int, float)):
                return float(percent)
            statements = summary.get("covered_lines"), summary.get("num_statements")
            if all(isinstance(item, (int, float)) for item in statements) and statements[1]:
                return float(statements[0]) / float(statements[1]) * 100.0
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", help="Files or directories to inspect.")
    parser.add_argument("--repo", default=".", help="Repository root for locating tests.")
    parser.add_argument("--coverage-json", help="Optional coverage.py-style JSON report.")
    args = parser.parse_args()

    repo_root = Path(args.repo)
    sources = [path for path in iter_source_files(args.targets) if not is_test_file(path)]
    tests = all_test_files(repo_root)
    coverage = load_coverage(args.coverage_json)

    findings = []
    for source in sources:
        related = related_tests(source, tests, repo_root)
        coverage_percent = coverage_for_file(coverage, source)
        has_tests = bool(related)
        confidence = "medium" if has_tests or coverage_percent is not None else "low"
        findings.append(
            {
                "type": ["Test Evidence"],
                "location": {"file": source.as_posix()},
                "engineering_evidence": {
                    "has_tests": has_tests,
                    "test_files": related,
                    "coverage_percent": coverage_percent,
                    "coverage_source": args.coverage_json,
                },
                "confidence": confidence,
            }
        )

    for idx, finding in enumerate(findings, start=1):
        finding["id"] = f"test-{idx:04d}"

    print(
        json.dumps(
            {
                "scanner": "scan-tests",
                "targets": args.targets,
                "summary": {"source_files": len(sources), "test_files_seen": len(tests), "findings": len(findings), "coverage_error": coverage.get("error")},
                "findings": findings,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

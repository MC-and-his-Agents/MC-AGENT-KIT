#!/usr/bin/env python3
"""Scan low-confidence literal, comment, and naming smell candidates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".kts",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".swift",
}

TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX|WORKAROUND|TEMPORARY)\b[:\s-]*(.*)", re.I)
NUMBER_RE = re.compile(r"(?<![\w.])-?\b(?:[2-9]|[1-9]\d{1,})(?:\.\d+)?\b(?![\w.])")
STRING_RE = re.compile(r"(['\"])(?:(?=(\\?))\2.)*?\1")
SUSPICIOUS_NAME_RE = re.compile(r"\b(data|info|obj|tmp|temp|misc|stuff|thing|manager|helper|util)\b", re.I)
COMMENT_RE = re.compile(r"^\s*(#|//|/\*|\*)\s?(.*)")


def iter_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_file() and path.suffix in CODE_EXTENSIONS:
            files.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix in CODE_EXTENSIONS:
                    parts = set(child.parts)
                    if parts.intersection({"node_modules", "vendor", "dist", "build", ".git"}):
                        continue
                    files.append(child)
    return sorted(files)


def is_low_value_literal(value: str) -> bool:
    stripped = value.strip("\"'")
    if len(stripped) <= 1:
        return True
    if stripped.startswith(("./", "../", "/", "http://", "https://")):
        return True
    if re.fullmatch(r"[A-Z_][A-Z0-9_]*", stripped):
        return False
    return False


def add_finding(findings: list[dict], path: Path, line_no: int, smell_type: str, evidence: dict, confidence: str = "low") -> None:
    findings.append(
        {
            "type": [smell_type],
            "location": {"file": path.as_posix(), "start_line": line_no, "end_line": line_no},
            "detection_evidence": evidence,
            "confidence": confidence,
        }
    )


def scan_file(path: Path) -> list[dict]:
    findings: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        return [{"type": "Read Error", "location": {"file": path.as_posix()}, "error": str(exc), "confidence": "unknown"}]

    for idx, line in enumerate(lines, start=1):
        todo = TODO_RE.search(line)
        if todo:
            add_finding(
                findings,
                path,
                idx,
                "Comment-Masked Complexity",
                {"marker": todo.group(1).upper(), "text": todo.group(2).strip(), "line": line.strip()},
                "medium",
            )

        comment = COMMENT_RE.match(line)
        if comment and len(comment.group(2)) > 100:
            add_finding(
                findings,
                path,
                idx,
                "Comment-Masked Complexity",
                {"reason": "long explanatory comment", "line": line.strip()},
                "low",
            )

        code_part = line.split("//", 1)[0].split("#", 1)[0]
        numbers = [match.group(0) for match in NUMBER_RE.finditer(code_part)]
        suspicious_numbers = [number for number in numbers if number not in {"0", "1", "-1"}]
        if suspicious_numbers:
            add_finding(
                findings,
                path,
                idx,
                "Magic Number",
                {"literals": suspicious_numbers[:5], "line": line.strip()},
                "low",
            )

        strings = [match.group(0) for match in STRING_RE.finditer(code_part)]
        suspicious_strings = [value for value in strings if not is_low_value_literal(value)]
        if len(suspicious_strings) >= 2:
            add_finding(
                findings,
                path,
                idx,
                "Magic String",
                {"literals": suspicious_strings[:5], "line": line.strip()},
                "low",
            )

        names = sorted(set(match.group(0) for match in SUSPICIOUS_NAME_RE.finditer(code_part)))
        if names:
            add_finding(
                findings,
                path,
                idx,
                "Unclear Naming",
                {"names": names, "line": line.strip()},
                "low",
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", help="Files or directories to inspect.")
    args = parser.parse_args()

    files = iter_files(args.targets)
    findings: list[dict] = []
    for path in files:
        findings.extend(scan_file(path))
    for idx, finding in enumerate(findings, start=1):
        finding.setdefault("id", f"literal-{idx:04d}")

    print(
        json.dumps(
            {
                "scanner": "scan-literals-comments",
                "targets": args.targets,
                "summary": {"files_scanned": len(files), "findings": len(findings)},
                "findings": findings,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Detect simple repeated normalized code windows without external dependencies."""

from __future__ import annotations

import argparse
import hashlib
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

COMMENT_RE = re.compile(r"^\s*(#|//|/\*|\*|\*/)")
STRING_RE = re.compile(r"(['\"])(?:(?=(\\?))\2.)*?\1")
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
SPACE_RE = re.compile(r"\s+")


def iter_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_file() and path.suffix in CODE_EXTENSIONS:
            files.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix in CODE_EXTENSIONS:
                    if set(child.parts).intersection({"node_modules", "vendor", "dist", "build", ".git"}):
                        continue
                    files.append(child)
    return sorted(files)


def normalize_line(line: str) -> str:
    line = line.strip()
    line = STRING_RE.sub("<str>", line)
    line = NUMBER_RE.sub("<num>", line)
    line = SPACE_RE.sub(" ", line)
    return line


def normalized_code_lines(path: Path) -> list[tuple[int, str]]:
    try:
        raw_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    lines: list[tuple[int, str]] = []
    for idx, line in enumerate(raw_lines, start=1):
        stripped = line.strip()
        if not stripped or COMMENT_RE.match(stripped):
            continue
        normalized = normalize_line(stripped)
        if len(normalized) < 3:
            continue
        lines.append((idx, normalized))
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", help="Files or directories to inspect.")
    parser.add_argument("--min-lines", type=int, default=8, help="Minimum normalized lines per duplicate window.")
    args = parser.parse_args()

    windows: dict[str, list[dict]] = {}
    files = iter_files(args.targets)
    for path in files:
        lines = normalized_code_lines(path)
        for offset in range(0, max(0, len(lines) - args.min_lines + 1)):
            chunk = lines[offset : offset + args.min_lines]
            digest_input = "\n".join(item[1] for item in chunk)
            digest = hashlib.sha1(digest_input.encode("utf-8")).hexdigest()
            windows.setdefault(digest, []).append(
                {
                    "file": path.as_posix(),
                    "start_line": chunk[0][0],
                    "end_line": chunk[-1][0],
                    "normalized_excerpt": digest_input,
                }
            )

    findings: list[dict] = []
    for digest, occurrences in windows.items():
        unique_locations = {(item["file"], item["start_line"]) for item in occurrences}
        if len(unique_locations) < 2:
            continue
        findings.append(
            {
                "type": ["Duplicated Code"],
                "location": {
                    "file": occurrences[0]["file"],
                    "start_line": occurrences[0]["start_line"],
                    "end_line": occurrences[0]["end_line"],
                },
                "detection_evidence": {
                    "duplicate_hash": digest,
                    "occurrences": occurrences[:10],
                    "occurrence_count": len(unique_locations),
                    "window_lines": args.min_lines,
                },
                "confidence": "medium",
            }
        )

    for idx, finding in enumerate(findings, start=1):
        finding["id"] = f"dup-{idx:04d}"

    print(
        json.dumps(
            {
                "scanner": "scan-duplication",
                "targets": args.targets,
                "summary": {"files_scanned": len(files), "findings": len(findings), "min_lines": args.min_lines},
                "findings": findings,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

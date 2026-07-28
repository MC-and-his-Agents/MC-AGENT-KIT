#!/usr/bin/env python3
"""Heuristically scan code size and complexity signals without modifying files."""

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

DEFAULT_THRESHOLDS = {
    "function_lines": 80,
    "class_lines": 300,
    "parameter_count": 6,
    "cyclomatic_complexity": 15,
    "nested_depth": 4,
}

BRANCH_RE = re.compile(r"\b(if|elif|else if|for|while|case|catch|except|when|switch|match|&&|\|\|)\b")
PY_DEF_RE = re.compile(r"^(\s*)(def|async\s+def|class)\s+([A-Za-z_][\w]*)\s*(?:\(([^)]*)\))?")
BRACE_SYMBOL_RE = re.compile(
    r"^\s*(?:(?:export|public|private|protected|static|async|final|func|function)\s+)*"
    r"(?:(class|interface|struct|enum)\s+([A-Za-z_][\w]*)|"
    r"(?:[A-Za-z_][\w<>\[\],\s*&:.?]*\s+)?([A-Za-z_][\w]*)\s*\(([^;{}]*)\)\s*(?:[:\w\s<>,-]*)?\{?)"
)


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


def count_params(params: str | None) -> int:
    if not params:
        return 0
    stripped = params.strip()
    if not stripped:
        return 0
    return len([part for part in stripped.split(",") if part.strip()])


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def max_indent_depth(lines: list[str]) -> int:
    indents = [indentation(line) for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if not indents:
        return 0
    base = min(indents)
    return max((indent - base) // 4 for indent in indents)


def max_brace_depth(lines: list[str]) -> int:
    depth = 0
    max_depth = 0
    for line in lines:
        for char in line:
            if char == "{":
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == "}":
                depth = max(0, depth - 1)
    return max_depth


def branch_count(lines: list[str]) -> int:
    return sum(len(BRANCH_RE.findall(line)) for line in lines)


def excerpt(lines: list[str], max_lines: int = 5) -> str:
    return "\n".join(line.rstrip() for line in lines[:max_lines])


def add_finding(findings: list[dict], path: Path, kind: str, symbol: str, start: int, end: int, lines: list[str], params: int, thresholds: dict) -> None:
    line_count = max(0, end - start + 1)
    branches = branch_count(lines)
    nesting = max(max_indent_depth(lines), max_brace_depth(lines))
    evidence = {
        "lines": line_count,
        "parameter_count": params,
        "branch_count": branches,
        "nested_depth": nesting,
        "rough_cyclomatic_complexity": branches + 1,
    }
    smell_types = []
    if kind == "class" and line_count >= thresholds["class_lines"]:
        smell_types.append("Large Class")
    if kind == "function" and line_count >= thresholds["function_lines"]:
        smell_types.append("Long Function")
    if params >= thresholds["parameter_count"]:
        smell_types.append("Long Parameter List")
    if branches + 1 >= thresholds["cyclomatic_complexity"] or nesting >= thresholds["nested_depth"]:
        smell_types.append("Complex Conditional Branching")
    if not smell_types:
        return

    confidence = "high" if line_count >= thresholds.get(f"{kind}_lines", 9999) or branches + 1 >= thresholds["cyclomatic_complexity"] else "medium"
    findings.append(
        {
            "type": smell_types,
            "location": {
                "file": path.as_posix(),
                "start_line": start,
                "end_line": end,
                "symbol": symbol,
            },
            "detection_evidence": evidence,
            "code_excerpt": excerpt(lines),
            "confidence": confidence,
        }
    )


def scan_python(path: Path, lines: list[str], thresholds: dict) -> list[dict]:
    findings: list[dict] = []
    symbols: list[dict] = []
    for idx, line in enumerate(lines, start=1):
        match = PY_DEF_RE.match(line)
        if not match:
            continue
        indent, token, name, params = match.groups()
        symbols.append(
            {
                "start": idx,
                "indent": len(indent),
                "kind": "class" if token == "class" else "function",
                "name": name,
                "params": count_params(params),
            }
        )

    for i, symbol in enumerate(symbols):
        end = len(lines)
        for later in symbols[i + 1 :]:
            if later["indent"] <= symbol["indent"]:
                end = later["start"] - 1
                break
        block = lines[symbol["start"] - 1 : end]
        add_finding(findings, path, symbol["kind"], symbol["name"], symbol["start"], end, block, symbol["params"], thresholds)
    return findings


def scan_brace_language(path: Path, lines: list[str], thresholds: dict) -> list[dict]:
    findings: list[dict] = []
    symbols: list[dict] = []
    for idx, line in enumerate(lines, start=1):
        match = BRACE_SYMBOL_RE.match(line)
        if not match:
            continue
        class_token, class_name, fn_name, params = match.groups()
        if class_token:
            symbols.append({"start": idx, "kind": "class", "name": class_name, "params": 0})
        elif fn_name not in {"if", "for", "while", "switch", "catch"}:
            symbols.append({"start": idx, "kind": "function", "name": fn_name, "params": count_params(params)})

    for symbol in symbols:
        depth = 0
        seen_open = False
        end = min(len(lines), symbol["start"] + 20)
        for idx in range(symbol["start"], len(lines) + 1):
            line = lines[idx - 1]
            depth += line.count("{")
            if "{" in line:
                seen_open = True
            depth -= line.count("}")
            if seen_open and depth <= 0:
                end = idx
                break
        block = lines[symbol["start"] - 1 : end]
        add_finding(findings, path, symbol["kind"], symbol["name"], symbol["start"], end, block, symbol["params"], thresholds)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", help="Files or directories to inspect.")
    parser.add_argument("--function-lines", type=int, default=DEFAULT_THRESHOLDS["function_lines"])
    parser.add_argument("--class-lines", type=int, default=DEFAULT_THRESHOLDS["class_lines"])
    parser.add_argument("--parameter-count", type=int, default=DEFAULT_THRESHOLDS["parameter_count"])
    parser.add_argument("--cyclomatic-complexity", type=int, default=DEFAULT_THRESHOLDS["cyclomatic_complexity"])
    parser.add_argument("--nested-depth", type=int, default=DEFAULT_THRESHOLDS["nested_depth"])
    args = parser.parse_args()

    thresholds = {
        "function_lines": args.function_lines,
        "class_lines": args.class_lines,
        "parameter_count": args.parameter_count,
        "cyclomatic_complexity": args.cyclomatic_complexity,
        "nested_depth": args.nested_depth,
    }
    findings: list[dict] = []
    files = iter_files(args.targets)
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError as exc:
            findings.append({"type": "Read Error", "location": {"file": path.as_posix()}, "error": str(exc), "confidence": "unknown"})
            continue
        if path.suffix == ".py":
            findings.extend(scan_python(path, lines, thresholds))
        else:
            findings.extend(scan_brace_language(path, lines, thresholds))

    for idx, finding in enumerate(findings, start=1):
        finding.setdefault("id", f"size-{idx:04d}")

    print(
        json.dumps(
            {
                "scanner": "scan-size-complexity",
                "targets": args.targets,
                "thresholds": thresholds,
                "summary": {"files_scanned": len(files), "findings": len(findings)},
                "findings": findings,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

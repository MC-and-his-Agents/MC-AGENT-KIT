#!/usr/bin/env python3
"""Collect lightweight import coupling, cycle, and boundary evidence."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".kts", ".go", ".rs", ".rb", ".php", ".cs", ".swift"}

IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+(.+?)\s+from\s+['\"]([^'\"]+)['\"]"),
    re.compile(r"^\s*import\s+['\"]([^'\"]+)['\"]"),
    re.compile(r"^\s*const\s+.+?\s*=\s*require\(['\"]([^'\"]+)['\"]\)"),
    re.compile(r"^\s*from\s+([\w.]+)\s+import\s+"),
    re.compile(r"^\s*import\s+([\w.]+)"),
    re.compile(r"^\s*require\s+['\"]([^'\"]+)['\"]"),
    re.compile(r"^\s*use\s+([\w:]+)"),
    re.compile(r"^\s*package\s+([\w.]+)"),
]


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


def extract_imports(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    imports: list[str] = []
    for line in lines:
        for pattern in IMPORT_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            value = match.groups()[-1]
            if value and value not in imports:
                imports.append(value)
            break
    return imports


def module_key(path: Path) -> str:
    return path.with_suffix("").as_posix()


def resolve_local_import(import_value: str, file_path: Path, module_index: dict[str, str]) -> str | None:
    candidates: list[str] = []
    if import_value.startswith("."):
        level = len(import_value) - len(import_value.lstrip("."))
        module_tail = import_value[level:].replace(".", "/")
        base_path = file_path.parent
        for _ in range(max(0, level - 1)):
            base_path = base_path.parent
        base = (base_path / module_tail).as_posix() if module_tail else base_path.as_posix()
        candidates.append(base)
        candidates.append(base.rstrip("/") + "/index")
    else:
        dotted = import_value.replace(".", "/").replace("::", "/")
        candidates.append(dotted)
        candidates.append(dotted.rstrip("/") + "/index")
    for candidate in candidates:
        if candidate in module_index:
            return module_index[candidate]
    return None


def find_direct_cycles(graph: dict[str, set[str]]) -> list[tuple[str, str]]:
    cycles: set[tuple[str, str]] = set()
    for source, targets in graph.items():
        for target in targets:
            if source in graph.get(target, set()):
                cycles.add(tuple(sorted((source, target))))
    return sorted(cycles)


def parse_boundary(raw: str) -> tuple[str, str]:
    if ":" not in raw:
        raise argparse.ArgumentTypeError("boundary must be FROM_GLOB:FORBIDDEN_GLOB")
    left, right = raw.split(":", 1)
    return left, right


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", help="Files or directories to inspect.")
    parser.add_argument("--outbound-threshold", type=int, default=12)
    parser.add_argument("--inbound-threshold", type=int, default=8)
    parser.add_argument("--boundary", action="append", default=[], type=parse_boundary, help="Boundary rule as FROM_GLOB:FORBIDDEN_IMPORT_GLOB.")
    args = parser.parse_args()

    files = iter_files(args.targets)
    module_index = {module_key(path): path.as_posix() for path in files}
    imports_by_file = {path.as_posix(): extract_imports(path) for path in files}
    local_graph: dict[str, set[str]] = defaultdict(set)
    inbound: dict[str, set[str]] = defaultdict(set)

    for file_name, imports in imports_by_file.items():
        file_path = Path(file_name)
        for import_value in imports:
            resolved = resolve_local_import(import_value, file_path, module_index)
            if resolved:
                local_graph[file_name].add(resolved)
                inbound[resolved].add(file_name)

    findings: list[dict] = []
    for file_name, imports in imports_by_file.items():
        outbound_count = len(imports)
        inbound_count = len(inbound.get(file_name, set()))
        smell_types = []
        if outbound_count >= args.outbound_threshold:
            smell_types.append("High Coupling")
        if inbound_count >= args.inbound_threshold:
            smell_types.append("High Fan-In Coupling")
        if smell_types:
            findings.append(
                {
                    "type": smell_types,
                    "location": {"file": file_name},
                    "detection_evidence": {
                        "outbound_imports": outbound_count,
                        "inbound_local_imports": inbound_count,
                        "imports": imports[:30],
                    },
                    "confidence": "medium",
                }
            )

    for left, right in find_direct_cycles(local_graph):
        findings.append(
            {
                "type": ["Dependency Cycle"],
                "location": {"file": left},
                "detection_evidence": {"cycle": [left, right]},
                "confidence": "medium",
            }
        )

    for file_name, imports in imports_by_file.items():
        for from_glob, forbidden_glob in args.boundary:
            if not fnmatch.fnmatch(file_name, from_glob):
                continue
            forbidden = [value for value in imports if fnmatch.fnmatch(value, forbidden_glob)]
            if forbidden:
                findings.append(
                    {
                        "type": ["Layer Boundary Violation"],
                        "location": {"file": file_name},
                        "detection_evidence": {"boundary": f"{from_glob}:{forbidden_glob}", "imports": forbidden},
                        "confidence": "medium",
                    }
                )

    for idx, finding in enumerate(findings, start=1):
        finding["id"] = f"dep-{idx:04d}"

    print(
        json.dumps(
            {
                "scanner": "scan-dependencies",
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

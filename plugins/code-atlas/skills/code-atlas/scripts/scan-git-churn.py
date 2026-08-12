#!/usr/bin/env python3
"""Collect read-only git churn evidence for code smell decisions."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


BUGFIX_RE = re.compile(r"\b(fix|bug|hotfix|rollback|revert|regression|incident)\b", re.I)


def run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git_root(start: Path) -> Path | None:
    result = run_git(start, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def to_repo_path(repo: Path, path: Path) -> str:
    path = path if path.is_absolute() else (repo / path)
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def list_target_files(repo: Path, targets: list[str]) -> list[str]:
    files: set[str] = set()
    for target in targets:
        result = run_git(repo, ["ls-files", "--", target])
        if result.returncode == 0:
            files.update(line for line in result.stdout.splitlines() if line)
    return sorted(files)


def churn_for_file(repo: Path, file_path: str, since: str) -> dict:
    fmt = "%H%x09%an%x09%ad%x09%s"
    result = run_git(
        repo,
        ["log", "--since", since, "--date=short", f"--format={fmt}", "--", file_path],
    )
    commits = []
    authors = Counter()
    bugfix_like = 0
    last_changed = None

    if result.returncode == 0:
        for line in result.stdout.splitlines():
            parts = line.split("\t", 3)
            if len(parts) != 4:
                continue
            commit, author, date, subject = parts
            commits.append(commit)
            authors[author] += 1
            if last_changed is None:
                last_changed = date
            if BUGFIX_RE.search(subject):
                bugfix_like += 1

    confidence = "high" if commits else "low"
    return {
        "file": file_path,
        "changes": len(commits),
        "authors": len(authors),
        "author_names": sorted(authors),
        "last_changed": last_changed,
        "bugfix_like_commits": bugfix_like,
        "confidence": confidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="+", help="Files or directories to inspect.")
    parser.add_argument("--repo", default=".", help="Repository root or any path inside it.")
    parser.add_argument("--since", default="90 days ago", help='Git --since value, e.g. "90 days ago".')
    args = parser.parse_args()

    start = Path(args.repo).resolve()
    repo = git_root(start)
    if repo is None:
        print(
            json.dumps(
                {
                    "scanner": "scan-git-churn",
                    "repo": str(start),
                    "error": "not a git repository",
                    "findings": [],
                },
                indent=2,
            )
        )
        return 0

    rel_targets = [to_repo_path(repo, Path(target)) for target in args.targets]
    files = list_target_files(repo, rel_targets)
    findings = [churn_for_file(repo, file_path, args.since) for file_path in files]
    findings.sort(key=lambda item: (item["changes"], item["authors"], item["bugfix_like_commits"]), reverse=True)

    print(
        json.dumps(
            {
                "scanner": "scan-git-churn",
                "repo": str(repo),
                "targets": rel_targets,
                "since": args.since,
                "summary": {
                    "files": len(findings),
                    "total_changes": sum(item["changes"] for item in findings),
                    "hotspot_files": sum(1 for item in findings if item["changes"] >= 5 or item["authors"] >= 3),
                },
                "findings": findings,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

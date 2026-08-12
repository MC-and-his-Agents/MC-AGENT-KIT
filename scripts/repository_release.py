#!/usr/bin/env python3
"""Generate release notes and artifacts.json from one artifact diff."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from repository_artifacts import ROOT, artifact_row, compare, json_text


RELEASE_TAG_PATTERN = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def release_ledger(result: dict, release_tag: str, previous_tag: str) -> dict:
    match = RELEASE_TAG_PATTERN.fullmatch(release_tag)
    previous = RELEASE_TAG_PATTERN.fullmatch(previous_tag)
    if not match or not previous:
        raise ValueError("repository release tags must use stable vMAJOR.MINOR.PATCH SemVer")
    if tuple(map(int, match.groups())) <= tuple(map(int, previous.groups())):
        raise ValueError(f"{release_tag} must be newer than {previous_tag}")
    return {
        "schema_version": 1,
        "release": {
            "tag": release_tag,
            "previous_tag": previous_tag,
            "base_commit": result["base_commit"],
            "target_commit": result["target_commit"],
        },
        "changes": {
            key: result[key] for key in ("added", "updated", "removed")
        },
        "snapshot": result["snapshot"],
    }


def release_notes(ledger: dict, run_url: str, ci_url: str) -> str:
    release = ledger["release"]
    changed = ledger["changes"]
    lines = [
        f"# MC-AGENT-KIT {release['tag']}",
        "",
        "## Artifact changes",
        "",
    ]
    if not any(changed.values()):
        lines.extend(("本次无 artifact 版本变化。", ""))
    else:
        for title, key in (("Added", "added"), ("Updated", "updated"), ("Removed", "removed")):
            items = [
                item["after"] if key == "updated" else item for item in changed[key]
            ]
            lines.extend((f"### {title} ({len(items)})", ""))
            lines.extend((*(f"- `{item['type']}:{item['name']} {item['version']}`" for item in items), ""))
    lines.extend(
        (
            "## Full artifact snapshot",
            "",
            "| Type | Name | Version | Collection | Harnesses | Digest |",
            "|---|---|---:|---|---|---|",
            *(artifact_row(item) for item in ledger["snapshot"]),
            "",
            "## Stable installation",
            "",
            "```bash",
            f"npx skills add https://github.com/MC-and-his-Agents/MC-AGENT-KIT/tree/{release['tag']}/skills --full-depth --list",
            f"codex plugin marketplace add MC-and-his-Agents/MC-AGENT-KIT --ref {release['tag']}",
            "codex plugin add code-atlas@mc-agent-kit",
            f"claude plugin marketplace add MC-and-his-Agents/MC-AGENT-KIT@{release['tag']}",
            "claude plugin install code-atlas@mc-agent-kit",
            "```",
            "",
            "## Evidence",
            "",
            f"- Previous release: `{release['previous_tag']}` (`{release['base_commit']}`)",
            f"- Target commit: `{release['target_commit']}`",
            "- Machine-readable ledger: `artifacts.json`",
            f"- Successful main CI: {ci_url}",
            f"- Release workflow: {run_url}",
            "",
        )
    )
    return "\n".join(lines)


def self_test() -> list[str]:
    result = {
        "base_commit": "b" * 40,
        "target_commit": "a" * 40,
        "added": [],
        "updated": [],
        "removed": [],
        "unchanged": [],
        "snapshot": [],
    }
    failures: list[str] = []
    ledger = release_ledger(result, "v0.1.1", "v0.1.0")
    if ledger["release"]["target_commit"] != result["target_commit"]:
        failures.append("release ledger lost the target commit")
    notes = release_notes(ledger, "run", "ci")
    for expected in ("MC-AGENT-KIT", "@mc-agent-kit"):
        if expected not in notes:
            failures.append(f"release notes lost repository identity: {expected}")
    for legacy in ("MC-SKILLS", "@mcskills"):
        if legacy in notes:
            failures.append(f"release notes retained legacy identity: {legacy}")
    for tag in ("v0.1.0", "v0.1.1-rc.1", "0.1.1"):
        try:
            release_ledger(result, tag, "v0.1.0")
        except ValueError:
            continue
        failures.append(f"invalid release tag accepted: {tag}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--target", default="HEAD")
    parser.add_argument("--release-tag")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--notes-output", type=Path)
    parser.add_argument("--run-url", default="")
    parser.add_argument("--ci-url", default="")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        failures = self_test()
        for item in failures:
            print(f"error: {item}", file=sys.stderr)
        if not failures:
            print("Release generator self-check passed.")
        return bool(failures)
    if not all((args.base, args.release_tag, args.json_output, args.notes_output)):
        parser.error("--base, --release-tag, --json-output and --notes-output are required")
    try:
        result = compare(ROOT, args.base, args.target)
        ledger = release_ledger(result, args.release_tag, args.base)
        args.json_output.write_text(json_text(ledger), encoding="utf-8")
        args.notes_output.write_text(
            release_notes(ledger, args.run_url, args.ci_url),
            encoding="utf-8",
        )
    except (OSError, UnicodeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


def code_atlas_migration(changed: dict) -> bool:
    added = {(item["type"], item["name"], item["version"]) for item in changed["added"]}
    removed = {(item["type"], item["name"], item["version"]) for item in changed["removed"]}
    return not changed["updated"] and added == {
        ("plugin", "code-atlas", "0.3.0")
    } and removed == {
        ("plugin", "codegraph-intelligence", "0.2.2"),
        ("skill", "code-smell-decision", "0.1.0"),
    }


def code_atlas_031_update(changed: dict) -> bool:
    if changed["added"] or changed["removed"] or len(changed["updated"]) != 1:
        return False
    update = changed["updated"][0]
    return tuple(update["before"][key] for key in ("type", "name", "version")) == (
        "plugin", "code-atlas", "0.3.0"
    ) and tuple(update["after"][key] for key in ("type", "name", "version")) == (
        "plugin", "code-atlas", "0.3.1"
    )


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
    if code_atlas_migration(changed):
        lines.extend(
            (
                "## CodeAtlas 0.3.0",
                "",
                "- CodeAtlas 现在只有一个 Skill，以 `UNDERSTAND`、`TRACE`、`CHANGE`、`ASSESS` 四路覆盖代码库理解、行为追踪、变更影响和维护性决策。",
                "- 独立 `code-smell-decision` 已被 `ASSESS` 吸收；七个只读 scanner、JSON schema、误报过滤与 Fix/Defer/Track/Accept/Human Judgment 决策模型继续保留。",
                "- 插件只注册一次 `SessionStart` / `SubagentStart` hooks。hooks 仅报告当前 worktree、CLI 和精确 `.codegraph/codegraph.db` 状态，不安装 CodeGraph、不初始化索引、不修改配置。",
                "- CodeGraph CLI 与当前 worktree 索引是图分析必备条件；原生 MCP 由 CodeGraph 自身安装维护，不随 CodeAtlas 分发。没有 MCP 时只能进入诚实标注能力缺口的 CLI-only 模式。",
                "- 旧 `codegraph-intelligence` 和 standalone `code-smell-decision` 入口已移除；Claude Code 的显式入口为 `/code-atlas:code-atlas`。",
                "- 环境缺失或迁移旧安装时，应由 Agent 先解释官方来源、准确写入范围与副作用，取得授权后执行安装、配置、初始化或卸载，并回读验证；不要静默修改用户环境。",
                "",
            )
        )
    if code_atlas_031_update(changed):
        lines.extend(
            (
                "## CodeAtlas 0.3.1",
                "",
                "- `SessionStart` 在 startup、resume、clear、compact 时优先维护当前 worktree 的精确索引：缺失则自动 `codegraph init`，已存在则自动 `codegraph sync --quiet`。",
                "- 生命周期命令有界执行并验证精确路径、锁与待同步状态；超时、竞争或失败会给当前 Agent 注入同会话接管命令，不再用只读规则阻止恢复。",
                "- `SubagentStart` 只注入状态与证据规则，不重复索引；默认仍不注册 `UserPromptSubmit`。",
                "- 自动写入仅限当前 worktree 的 `.codegraph` 与初始化必需的 `.gitignore`，并禁用更新检查、遥测、daemon 与 Git hook fallback；不同 worktree 不共享索引结论。",
                "- CodeAtlas 仍不分发或自动安装 CodeGraph CLI，不配置 MCP，也不运行 `codegraph install`；CLI 缺失或索引损坏时由 Agent 说明来源、范围和副作用后接管。",
                "",
            )
        )
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
    migration = release_ledger(
        {
            **result,
            "added": [{"type": "plugin", "name": "code-atlas", "version": "0.3.0"}],
            "removed": [
                {"type": "plugin", "name": "codegraph-intelligence", "version": "0.2.2"},
                {"type": "skill", "name": "code-smell-decision", "version": "0.1.0"},
            ],
        },
        "v0.3.0",
        "v0.2.0",
    )
    migration_notes = release_notes(migration, "run", "ci")
    for expected in (
        "UNDERSTAND",
        "TRACE",
        "CHANGE",
        "ASSESS",
        "SessionStart",
        "SubagentStart",
        "CLI-only",
        "/code-atlas:code-atlas",
        "取得授权",
    ):
        if expected not in migration_notes:
            failures.append(f"CodeAtlas migration notes lost required contract: {expected}")
    migration_changes = migration["changes"]
    invalid_migrations = (
        {**migration_changes, "added": [*migration_changes["added"], {"type": "skill", "name": "extra", "version": "0.1.0"}]},
        {**migration_changes, "updated": [{"before": {"type": "skill", "name": "extra", "version": "0.1.0"}, "after": {"type": "skill", "name": "extra", "version": "0.1.1"}}]},
        {**migration_changes, "added": [{"type": "plugin", "name": "code-atlas", "version": "9.9.9"}]},
        {**migration_changes, "removed": [{"type": "plugin", "name": "codegraph-intelligence", "version": "9.9.9"}, migration_changes["removed"][1]]},
    )
    if any(code_atlas_migration(changes) for changes in invalid_migrations):
        failures.append("CodeAtlas migration notes accepted extra artifacts or wrong versions")
    update = release_ledger(
        {
            **result,
            "updated": [
                {
                    "before": {"type": "plugin", "name": "code-atlas", "version": "0.3.0"},
                    "after": {"type": "plugin", "name": "code-atlas", "version": "0.3.1"},
                }
            ],
        },
        "v0.3.1",
        "v0.3.0",
    )
    update_notes = release_notes(update, "run", "ci")
    for expected in (
        "CodeAtlas 0.3.1",
        "codegraph init",
        "codegraph sync --quiet",
        "同会话接管",
        "SubagentStart",
        "UserPromptSubmit",
        "不分发或自动安装 CodeGraph CLI",
        "不配置 MCP",
    ):
        if expected not in update_notes:
            failures.append(f"CodeAtlas 0.3.1 notes lost required contract: {expected}")
    invalid_updates = (
        {**update["changes"], "added": [{"type": "skill", "name": "extra", "version": "0.1.0"}]},
        {**update["changes"], "removed": [{"type": "skill", "name": "extra", "version": "0.1.0"}]},
        {**update["changes"], "updated": [*update["changes"]["updated"], migration_changes]},
        {
            **update["changes"],
            "updated": [
                {
                    "before": {"type": "plugin", "name": "code-atlas", "version": "0.3.0"},
                    "after": {"type": "plugin", "name": "code-atlas", "version": "9.9.9"},
                }
            ],
        },
    )
    if any(code_atlas_031_update(changes) for changes in invalid_updates):
        failures.append("CodeAtlas 0.3.1 notes accepted extra artifacts or wrong versions")
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

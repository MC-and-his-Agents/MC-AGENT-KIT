"""Negative checks for the repository validator."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from repository_collections import (
    NPX_ADD_PREFIX,
    SKILLS_SOURCE,
    validate_collection_readmes,
    validate_npx_readmes,
)


def write_skill(
    path: Path,
    name: str,
    description: str = "test",
    version: str = "0.1.0",
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n"
        f"metadata:\n  version: {version}\n---\n",
        encoding="utf-8",
    )


def write_plugin(
    root: Path,
    name: str,
    *,
    skills: object = "./skills/",
    mcp: dict | None = None,
    hooks: dict | None = None,
    private_description: str | None = "test",
) -> None:
    plugin = root / "plugins" / name
    private = plugin / "skills" / f"{name}-private"
    private.mkdir(parents=True)
    description = (
        f"description: {private_description}\n" if private_description is not None else ""
    )
    (private / "SKILL.md").write_text(
        f"---\nname: {name}-private\n{description}metadata:\n  internal: true\n---\n",
        encoding="utf-8",
    )
    (plugin / ".mcp.json").write_text(
        json.dumps(
            mcp
            if mcp is not None
            else {"server": {"command": "codegraph", "args": ["serve", "--mcp"]}}
        ),
        encoding="utf-8",
    )
    base = {
        "name": name,
        "version": "0.1.0",
        "description": "test",
        "author": {"name": "test"},
        "license": "MIT",
        "keywords": [],
        "skills": skills,
        "mcpServers": "./.mcp.json",
    }
    for harness in (".codex-plugin", ".claude-plugin"):
        manifest = plugin / harness / "plugin.json"
        manifest.parent.mkdir(parents=True)
        document = dict(base)
        if harness == ".codex-plugin" and hooks is not None:
            (plugin / "hooks.json").write_text(json.dumps(hooks), encoding="utf-8")
            document["hooks"] = "./hooks.json"
        manifest.write_text(json.dumps(document), encoding="utf-8")


def write_code_atlas_plugin(root: Path, *, valid: bool = True) -> Path:
    plugin = root / "plugins" / "code-atlas"
    skill = plugin / "skills" / "code-atlas"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(
        "---\nname: code-atlas\ndescription: test\n"
        "metadata:\n  internal: true\n  version: 0.3.0\n---\n",
        encoding="utf-8",
    )
    hooks = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume|clear|compact",
                    "hooks": [{"type": "command", "command": "node \"${CLAUDE_PLUGIN_ROOT}/scripts/code-atlas-hook.js\" SessionStart", "timeout": 5}],
                }
            ],
            "SubagentStart": [
                {
                    "hooks": [{"type": "command", "command": "node \"${CLAUDE_PLUGIN_ROOT}/scripts/code-atlas-hook.js\" SubagentStart", "timeout": 5}],
                }
            ],
        }
    }
    hook_file = plugin / "hooks" / "claude-codex-hooks.json"
    hook_file.parent.mkdir(parents=True, exist_ok=True)
    hook_file.write_text(json.dumps(hooks), encoding="utf-8")
    base = {
        "name": "code-atlas",
        "version": "0.3.0",
        "description": "test",
        "author": {"name": "test"},
        "license": "MIT",
        "keywords": [],
        "skills": "./skills/",
        "hooks": "./hooks/claude-codex-hooks.json",
    }
    for harness in (".codex-plugin", ".claude-plugin"):
        manifest = plugin / harness / "plugin.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(base), encoding="utf-8")
    if not valid:
        (plugin / ".mcp.json").write_text("{}", encoding="utf-8")
        (plugin / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
        extra = plugin / "skills" / "extra"
        extra.mkdir()
        (extra / "SKILL.md").write_text(
            "---\nname: extra\ndescription: test\nmetadata:\n  internal: true\n---\n",
            encoding="utf-8",
        )
        invalid_hooks = json.loads(hook_file.read_text(encoding="utf-8"))
        invalid_hooks["hooks"]["SessionStart"][0]["hooks"][0]["timeout"] = 6
        invalid_hooks["hooks"]["SubagentStart"][0]["hooks"][0]["command"] = "node \"${CLAUDE_PLUGIN_ROOT:-.}/scripts/code-atlas-hook.js\" SubagentStart"
        invalid_hooks["hooks"]["UserPromptSubmit"] = invalid_hooks["hooks"]["SubagentStart"]
        hook_file.write_text(json.dumps(invalid_hooks), encoding="utf-8")
    return plugin


def write_collection_readme(
    root: Path,
    name: str,
    member: str,
    *,
    include_member: bool = True,
    correct_command: bool = False,
) -> None:
    path = root / "skills" / name / "README.md"
    member_row = f"[{member}](./{member}/SKILL.md)\n" if include_member else ""
    repository = (
        f"{SKILLS_SOURCE} --full-depth"
        if correct_command
        else "wrong/repository"
    )
    path.write_text(
        "<!-- COLLECTION_MEMBERS_START -->\n"
        f"{member_row}"
        f"npx skills add {repository} --skill {member}\n"
        "<!-- COLLECTION_MEMBERS_END -->\n",
        encoding="utf-8",
    )


def expect(errors: list[str], source: str, rule: str, failures: list[str]) -> None:
    if not any(source in error and rule in error for error in errors):
        failures.append(f"{source} {rule} self-check did not fail")


def check_skills(root, validate_skills, version_bump_errors, failures) -> None:
    for collection in ("one", "two"):
        write_skill(root / "skills" / collection / "same", "same")
    _, skill_errors = validate_skills(root)
    expect(skill_errors, "skills/two/same", "[skill-unique-id]", failures)
    missing = root / "skills" / "missing"
    missing.mkdir()
    (missing / "SKILL.md").write_text(
        "---\nname: missing\ndescription: test\n---\n", encoding="utf-8"
    )
    invalid_description = root / "skills" / "invalid-description"
    invalid_description.mkdir()
    (invalid_description / "SKILL.md").write_text(
        "---\nname: invalid-description\ndescription: true\n"
        "metadata:\n  version: 0.1.0\n---\n",
        encoding="utf-8",
    )
    _, skill_errors = validate_skills(root)
    expect(skill_errors, "skills/missing", "[skill-version]", failures)
    expect(skill_errors, "skills/invalid-description", "[skill-description]", failures)
    current = {"skill:same": ("skills/one/same", "0.1.0")}
    previous = {"skill:same": ("skills/one/same", "0.1.0")}
    unchanged = version_bump_errors(current, previous, {"skills/one/same/SKILL.md"})
    expect(unchanged, "skills/one/same", "[artifact-version-bump]", failures)


def check_plugins(root, validate_plugins, failures) -> None:
    write_plugin(root, "bad-type", skills=123)
    write_plugin(root, "bad-path", skills="../outside")
    write_plugin(root, "bad-mcp", mcp={"server": {"command": ""}})
    write_plugin(
        root,
        "bad-mcp-args",
        mcp={"server": {"command": "codegraph", "args": "not-a-list"}},
    )
    write_plugin(root, "bad-hooks", hooks={"hooks": {"SessionStart": "not-a-list"}})
    valid_hook = [{"hooks": [{"type": "command", "command": "true"}]}]
    write_plugin(root, "bad-hook-event", hooks={"hooks": {"NotARealEvent": valid_hook}})
    write_plugin(
        root,
        "bad-hook-matcher",
        hooks={
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": 123,
                        "hooks": [{"type": "command", "command": "true"}],
                    }
                ]
            }
        },
    )
    write_plugin(root, "bad-private", private_description=None)
    _, plugin_errors = validate_plugins(root, set())
    expected = (
        ("plugins/bad-type", "[plugin-component-type]"),
        ("plugins/bad-path", "[plugin-component-path]"),
        ("plugins/bad-mcp/.mcp.json", "[plugin-component-content]"),
        ("plugins/bad-mcp-args/.mcp.json", "[plugin-component-content]"),
        ("plugins/bad-hooks/hooks.json", "[plugin-component-content]"),
        ("plugins/bad-hook-event/hooks.json", "[plugin-component-content]"),
        ("plugins/bad-hook-matcher/hooks.json", "[plugin-component-content]"),
        ("plugins/bad-private", "[plugin-skill-description]"),
    )
    for source, rule in expected:
        expect(plugin_errors, source, rule, failures)

    atlas_root = root / "atlas-contract"
    write_code_atlas_plugin(atlas_root)
    _, atlas_errors = validate_plugins(atlas_root, set())
    if atlas_errors:
        failures.append(f"valid CodeAtlas fixture failed: {atlas_errors}")
    invalid_root = root / "atlas-negative"
    write_code_atlas_plugin(invalid_root, valid=False)
    _, invalid_errors = validate_plugins(invalid_root, set())
    expect(invalid_errors, "plugins/code-atlas", "[code-atlas-no-mcp]", failures)
    expect(invalid_errors, "plugins/code-atlas/hooks/hooks.json", "[code-atlas-standard-hooks-path]", failures)
    expect(invalid_errors, "plugins/code-atlas", "[code-atlas-single-skill]", failures)
    expect(invalid_errors, "plugins/code-atlas/hooks/claude-codex-hooks.json", "[code-atlas-hook-events]", failures)
    expect(invalid_errors, "plugins/code-atlas/hooks/claude-codex-hooks.json", "[code-atlas-hook-timeout]", failures)
    expect(invalid_errors, "plugins/code-atlas/hooks/claude-codex-hooks.json", "[code-atlas-no-user-prompt-hook]", failures)
    expect(invalid_errors, "plugins/code-atlas/hooks/claude-codex-hooks.json", "[code-atlas-no-shell-fallback]", failures)


def check_collections(root, failures) -> None:
    errors = validate_collection_readmes(root)
    expect(errors, "skills/one/README.md", "[collection-readme]", failures)
    write_collection_readme(root, "one", "same", include_member=False, correct_command=True)
    write_collection_readme(root, "two", "same")
    orphan = root / "skills" / "orphan"
    orphan.mkdir()
    (orphan / "README.md").write_text("# orphan\n", encoding="utf-8")
    errors = validate_collection_readmes(root)
    expect(errors, "skills/one/README.md", "[collection-members]", failures)
    expect(errors, "skills/two/README.md", "[collection-command]", failures)
    expect(errors, "skills/orphan/README.md", "[collection-orphan]", failures)
    (root / "README.md").write_text(
        "npx skills add MC-and-his-Agents/MC-AGENT-KIT --skill same\n",
        encoding="utf-8",
    )
    expect(
        validate_npx_readmes(root),
        "README.md",
        "[npx-source-boundary]",
        failures,
    )
    (root / "README.md").write_text(
        f"{NPX_ADD_PREFIX}-wrong --list\n",
        encoding="utf-8",
    )
    expect(
        validate_npx_readmes(root),
        "README.md",
        "[npx-source-boundary]",
        failures,
    )


def check_marketplace_identity(root, validate_marketplace, failures) -> None:
    path = root / "marketplace.json"
    path.write_text(json.dumps({"name": "mcskills", "plugins": []}), encoding="utf-8")
    errors = validate_marketplace(root, "marketplace.json", "Claude", set())
    expect(errors, "marketplace.json", "[marketplace-identity]", failures)


def check_code_atlas_hook_runtime(failures: list[str]) -> None:
    """Run the lifecycle runner against an isolated fake CLI/index fixture."""
    runner = Path(__file__).resolve().parents[1] / "plugins/code-atlas/scripts/code-atlas-hook.js"
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "-b", "main")
        git(repo, "config", "user.name", "self-check")
        git(repo, "config", "user.email", "self-check@example.invalid")
        (repo / "README.md").write_text("fixture\n", encoding="utf-8")
        commit_all(repo, "fixture")
        fake_bin = root / "bin"
        fake_bin.mkdir()
        fake_cli = fake_bin / "codegraph"
        fake_cli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake_cli.chmod(0o755)
        db = repo / ".codegraph" / "codegraph.db"
        db.parent.mkdir()
        db.write_text("fake\n", encoding="utf-8")
        node_path = shutil.which("node")
        if not node_path:
            failures.append("node is unavailable for lifecycle runner self-check")
            return

        def run(
            event: str,
            cwd: Path,
            *,
            plugin_data: Path | None = None,
            path_override: str | None = None,
        ) -> tuple[dict | str, str, str]:
            env = {
                "PATH": path_override or str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
                "CODEX_CWD": str(cwd),
                "CODEX_WORKSPACE_DIR": "",
                "CLAUDE_PROJECT_DIR": "",
            }
            if plugin_data is not None:
                env["PLUGIN_DATA"] = str(plugin_data)
            result = subprocess.run(
                [node_path, str(runner), event],
                cwd=cwd,
                env={**env},
                input="ignored stdin\n",
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0:
                failures.append(f"runner {event} exited {result.returncode}: {result.stderr}")
            try:
                parsed: dict | str = json.loads(result.stdout)
            except json.JSONDecodeError:
                parsed = result.stdout
            return parsed, result.stdout, result.stderr

        before = git(repo, "status", "--porcelain")
        before_files = sorted(
            item.relative_to(repo).as_posix()
            for item in repo.rglob("*")
            if ".git" not in item.parts
        )
        native_session, _, stderr = run("SessionStart", repo)
        if stderr or not isinstance(native_session, str):
            failures.append("native SessionStart did not emit raw context with empty stderr")
        elif any(item not in native_session for item in ("status=cli-only", "worktree=", "git-common-dir=", "mcp=unknown")):
            failures.append("native SessionStart context omitted required evidence")
        elif "SubagentStart evidence" in native_session:
            failures.append("native SessionStart included reduced SubagentStart-only context")

        native_subagent, _, stderr = run("SubagentStart", repo)
        if stderr or not isinstance(native_subagent, dict) or native_subagent.get("hookSpecificOutput", {}).get("hookEventName") != "SubagentStart":
            failures.append("native SubagentStart protocol/event is invalid")
        elif any(
            item not in native_subagent["hookSpecificOutput"].get("additionalContext", "")
            for item in ("status=cli-only", "worktree=", "cli=", "index=", "mcp=unknown", "observed", "inferred", "unknown")
        ):
            failures.append("native SubagentStart omitted reduced evidence rules")

        codex, _, stderr = run("SessionStart", repo, plugin_data=root / "plugin-data")
        if stderr or not isinstance(codex, dict) or codex.get("systemMessage") != "CodeAtlas: cli-only":
            failures.append("Codex protocol/systemMessage is invalid")
        elif codex.get("hookSpecificOutput", {}).get("hookEventName") != "SessionStart":
            failures.append("Codex SessionStart hook event is invalid")
        elif "mcp=unknown" not in codex["hookSpecificOutput"].get("additionalContext", ""):
            failures.append("Codex SessionStart omitted MCP unknown evidence")

        real_git = shutil.which("git")
        no_cli_bin = root / "no-cli-bin"
        no_cli_bin.mkdir()
        if real_git:
            (no_cli_bin / "git").symlink_to(real_git)
        missing_cli, _, stderr = run("SessionStart", repo, path_override=str(no_cli_bin))
        if stderr or not isinstance(missing_cli, str) or "status=unavailable" not in missing_cli:
            failures.append("missing CLI fixture did not report unavailable")

        no_index = root / "no-index"
        no_index.mkdir()
        missing, _, stderr = run("SessionStart", no_index)
        if stderr or not isinstance(missing, str) or "status=unknown" not in missing and "status=unavailable" not in missing:
            failures.append("missing index/CLI fixture did not report conservative status")
        non_git = root / "non-git"
        non_git.mkdir()
        nongit, _, stderr = run("SubagentStart", non_git)
        if stderr or not isinstance(nongit, dict) or nongit.get("hookSpecificOutput", {}).get("hookEventName") != "SubagentStart":
            failures.append("non-Git SubagentStart did not fail closed")
        if git(repo, "status", "--porcelain") != before:
            failures.append("runner changed repository status")
        after_files = sorted(
            item.relative_to(repo).as_posix()
            for item in repo.rglob("*")
            if ".git" not in item.parts
        )
        if after_files != before_files:
            failures.append("runner changed repository files")


def run_self_test(
    validate_skills,
    version_bump_errors,
    validate_plugins,
    validate_marketplace,
) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        check_skills(root, validate_skills, version_bump_errors, failures)
        check_plugins(root, validate_plugins, failures)
        check_collections(root, failures)
        check_marketplace_identity(root, validate_marketplace, failures)
    check_code_atlas_hook_runtime(failures)
    return failures


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def commit_all(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-m", message)
    return git(root, "rev-parse", "HEAD")


def run_artifact_self_test(compare, json_text, markdown_diff) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        git(root, "init", "-b", "main")
        git(root, "config", "user.name", "self-check")
        git(root, "config", "user.email", "self-check@example.invalid")
        for name in ("unchanged", "updated", "removed"):
            write_skill(root / "skills" / name, name)
        commit_all(root, "base")
        git(root, "tag", "v0.1.0")

        write_skill(root / "skills" / "updated", "updated", "changed", "0.1.1")
        write_skill(root / "skills" / "added", "added")
        shutil.rmtree(root / "skills" / "removed")
        target = commit_all(root, "target")
        result = compare(root, "v0.1.0", "HEAD")
        expected = {
            "added": ["added"],
            "updated": ["updated"],
            "removed": ["removed"],
            "unchanged": ["unchanged"],
        }
        actual = {
            "added": [item["name"] for item in result["added"]],
            "updated": [item["after"]["name"] for item in result["updated"]],
            "removed": [item["name"] for item in result["removed"]],
            "unchanged": [item["name"] for item in result["unchanged"]],
        }
        if actual != expected:
            failures.append(f"artifact diff self-check mismatch: {actual}")
        if json_text(result) != json_text(compare(root, "v0.1.0", target)):
            failures.append("artifact JSON is not deterministic")
        if markdown_diff(result) != markdown_diff(compare(root, "v0.1.0", target)):
            failures.append("artifact Markdown is not deterministic")

        (root / "README.md").write_text("docs only\n", encoding="utf-8")
        docs_target = commit_all(root, "docs")
        docs_diff = compare(root, target, docs_target)
        if docs_diff["added"] or docs_diff["updated"] or docs_diff["removed"]:
            failures.append("documentation-only change created pending artifacts")

        write_skill(root / "skills" / "unchanged", "unchanged", "content drift")
        commit_all(root, "invalid drift")
        try:
            compare(root, docs_target, "HEAD")
        except ValueError:
            pass
        else:
            failures.append("same-version content drift was not rejected")
    return failures

"""Negative checks for the repository validator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from repository_collections import (
    NPX_ADD_PREFIX,
    SKILLS_SOURCE,
    validate_collection_readmes,
    validate_npx_readmes,
)


def write_skill(path: Path, name: str, description: str = "test") -> None:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n"
        "metadata:\n  version: 0.1.0\n---\n",
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
        "npx skills add MC-and-his-Agents/MC-SKILLS --skill same\n",
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


def run_self_test(validate_skills, version_bump_errors, validate_plugins) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        check_skills(root, validate_skills, version_bump_errors, failures)
        check_plugins(root, validate_plugins, failures)
        check_collections(root, failures)
    return failures

"""Negative checks for the repository validator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


def run_self_test(validate_skills, version_bump_errors, validate_plugins) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for collection in ("one", "two"):
            path = root / "skills" / collection / "same"
            path.mkdir(parents=True)
            (path / "SKILL.md").write_text(
                "---\nname: same\ndescription: test\nmetadata:\n  version: 0.1.0\n---\n",
                encoding="utf-8",
            )
        _, duplicate_errors = validate_skills(root)
        if not any("[skill-unique-id]" in error for error in duplicate_errors):
            failures.append("duplicate skill self-check did not fail")

        missing = root / "skills" / "missing" / "SKILL.md"
        missing.parent.mkdir()
        missing.write_text("---\nname: missing\ndescription: test\n---\n", encoding="utf-8")
        _, missing_errors = validate_skills(root)
        if not any("[skill-version]" in error for error in missing_errors):
            failures.append("missing version self-check did not fail")

        current = {"skill:same": ("skills/one/same", "0.1.0")}
        previous = {"skill:same": ("skills/one/same", "0.1.0")}
        unchanged = version_bump_errors(current, previous, {"skills/one/same/SKILL.md"})
        if not any("[artifact-version-bump]" in error for error in unchanged):
            failures.append("unchanged version self-check did not fail")

        plugin = root / "plugins" / "broken"
        for harness in (".codex-plugin", ".claude-plugin"):
            manifest = plugin / harness / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps(
                    {
                        "name": "broken",
                        "version": "0.1.0",
                        "description": "test",
                        "author": {"name": "test"},
                        "license": "MIT",
                        "keywords": [],
                        "skills": 123,
                        "mcpServers": "./.mcp.json",
                    }
                ),
                encoding="utf-8",
            )
        (plugin / ".mcp.json").write_text("{}", encoding="utf-8")
        private = plugin / "skills" / "private" / "SKILL.md"
        private.parent.mkdir(parents=True)
        private.write_text(
            "---\nname: private\nmetadata:\n  internal: true\n---\n", encoding="utf-8"
        )
        _, manifest_errors = validate_plugins(root, set())
        expected = ("[plugin-component-type]", "[plugin-skill-description]")
        for rule in expected:
            if not any(rule in error for error in manifest_errors):
                failures.append(f"{rule} self-check did not fail")
    return failures

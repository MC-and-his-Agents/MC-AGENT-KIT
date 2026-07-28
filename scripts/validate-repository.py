#!/usr/bin/env python3
"""Validate repository structure, distribution metadata and artifact versions."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from repository_collections import validate_collection_readmes, validate_npx_readmes
from repository_plugin_components import load_json, validate_component_path
from repository_validator_selfcheck import run_self_test


ROOT = Path(__file__).resolve().parents[1]
SEMVER_NUMBER = r"(?:0|[1-9]\d*)"
SEMVER_PRERELEASE = rf"(?:{SEMVER_NUMBER}|\d*[A-Za-z-][0-9A-Za-z-]*)"
SEMVER_PATTERN = re.compile(
    rf"^{SEMVER_NUMBER}\.{SEMVER_NUMBER}\.{SEMVER_NUMBER}(?:-{SEMVER_PRERELEASE}(?:\.{SEMVER_PRERELEASE})*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
SHARED_PLUGIN_FIELDS = (
    "name", "version", "description", "author", "license", "keywords", "skills", "mcpServers"
)

def failure(path: str | Path, rule: str, fix: str) -> str:
    return f"{Path(path).as_posix()}: [{rule}] {fix}"

def scalar(value: str) -> str | bool:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    return value

def parse_skill_text(text: str, source: str) -> tuple[dict, dict, list[str]]:
    if not text.startswith("---\n"):
        return {}, {}, [failure(source, "skill-frontmatter", "add opening `---`")]
    end = text.find("\n---", 4)
    if end == -1:
        return {}, {}, [failure(source, "skill-frontmatter", "close frontmatter with `---`")]

    values: dict[str, str | bool] = {}
    metadata: dict[str, str | bool] = {}
    in_metadata = False
    for raw_line in text[4:end].splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#") or ":" not in raw_line:
            continue
        key, raw_value = raw_line.split(":", 1)
        if raw_line[:1].isspace():
            if in_metadata:
                metadata[key.strip()] = scalar(raw_value)
            continue
        in_metadata = key.strip() == "metadata"
        values[key.strip()] = scalar(raw_value)
    return values, metadata, []

def parse_skill(path: Path, root: Path) -> tuple[dict, dict, list[str]]:
    return parse_skill_text(path.read_text(encoding="utf-8"), path.relative_to(root).as_posix())

def validate_skills(root: Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    skills_root = root / "skills"
    artifacts: dict[str, tuple[str, str]] = {}
    seen: dict[str, str] = {}
    errors: list[str] = []
    for path in sorted(skills_root.rglob("SKILL.md")):
        relative = path.relative_to(skills_root)
        source = path.relative_to(root).as_posix()
        if len(relative.parts) not in {2, 3}:
            errors.append(
                failure(source, "skill-layout", "use skills/<skill>/ or skills/<collection>/<skill>/")
            )
            continue
        if len(relative.parts) == 2 and any(path.parent.glob("*/SKILL.md")):
            errors.append(
                failure(source, "collection-shadow", "remove SKILL.md from the collection root")
            )

        values, metadata, parse_errors = parse_skill(path, root)
        errors.extend(parse_errors)
        name = values.get("name")
        if not isinstance(name, str) or not name:
            errors.append(failure(source, "skill-name", "add a non-empty frontmatter `name`"))
            continue
        if name != path.parent.name:
            errors.append(
                failure(source, "skill-name", f"set `name: {path.parent.name}` to match its directory")
            )
        description = values.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(failure(source, "skill-description", "add frontmatter `description`"))
        if name in seen:
            errors.append(
                failure(source, "skill-unique-id", f"rename it; `{name}` already exists at {seen[name]}")
            )
        seen[name] = source
        version = metadata.get("version")
        if not isinstance(version, str) or not SEMVER_PATTERN.fullmatch(version):
            errors.append(
                failure(source, "skill-version", "set `metadata.version` to a valid SemVer")
            )
            continue
        artifacts[f"skill:{name}"] = (path.parent.relative_to(root).as_posix(), version)
    return artifacts, errors

def validate_private_skills(
    root: Path,
    plugin_dir: Path,
    standalone_names: set[str],
    private_seen: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    for skill_path in sorted((plugin_dir / "skills").rglob("SKILL.md")):
        source = skill_path.relative_to(root).as_posix()
        values, metadata, parse_errors = parse_skill(skill_path, root)
        errors.extend(parse_errors)
        skill_name = values.get("name")
        if not isinstance(skill_name, str) or not skill_name:
            errors.append(failure(source, "plugin-skill-name", "add frontmatter `name`"))
            continue
        if skill_name != skill_path.parent.name:
            errors.append(
                failure(
                    source,
                    "plugin-skill-name",
                    f"set `name: {skill_path.parent.name}` to match its directory",
                )
            )
        description = values.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(
                failure(source, "plugin-skill-description", "add frontmatter `description`")
            )
        if metadata.get("internal") is not True:
            errors.append(failure(source, "plugin-skill-private", "set `metadata.internal: true`"))
        if skill_name in standalone_names:
            errors.append(
                failure(
                    source,
                    "duplicate-distribution",
                    f"remove or rename `{skill_name}`; it is also standalone",
                )
            )
        if skill_name in private_seen:
            errors.append(
                failure(
                    source,
                    "plugin-skill-unique-id",
                    f"rename it; `{skill_name}` already exists at {private_seen[skill_name]}",
                )
            )
        private_seen[skill_name] = source
    return errors

def validate_plugins(
    root: Path, standalone_names: set[str]
) -> tuple[dict[str, tuple[str, str]], list[str]]:
    artifacts: dict[str, tuple[str, str]] = {}
    private_seen: dict[str, str] = {}
    errors: list[str] = []
    plugins_root = root / "plugins"
    for plugin_dir in sorted(path for path in plugins_root.iterdir() if path.is_dir()):
        manifests: list[tuple[Path, dict]] = []
        for relative in (Path(".codex-plugin/plugin.json"), Path(".claude-plugin/plugin.json")):
            path = plugin_dir / relative
            manifest, manifest_errors = load_json(path, root)
            errors.extend(manifest_errors)
            if manifest is not None:
                manifests.append((path, manifest))
        if len(manifests) != 2:
            continue
        first = manifests[0][1]
        for field in SHARED_PLUGIN_FIELDS:
            values = [manifest.get(field) for _, manifest in manifests]
            if any(value is None for value in values) or values[1:] != values[:-1]:
                errors.append(
                    failure(
                        plugin_dir.relative_to(root),
                        "plugin-manifest-drift",
                        f"make `{field}` identical in Codex and Claude manifests",
                    )
                )
        name = first.get("name")
        version = first.get("version")
        if name != plugin_dir.name:
            errors.append(
                failure(
                    manifests[0][0].relative_to(root),
                    "plugin-name",
                    f"set `name` to directory name `{plugin_dir.name}`",
                )
            )
        if not isinstance(version, str) or not SEMVER_PATTERN.fullmatch(version):
            errors.append(
                failure(
                    manifests[0][0].relative_to(root),
                    "plugin-version",
                    "set `version` to a valid SemVer",
                )
            )
        elif isinstance(name, str):
            artifacts[f"plugin:{name}"] = (plugin_dir.relative_to(root).as_posix(), version)
        for manifest_path, manifest in manifests:
            for field in ("skills", "hooks", "mcpServers"):
                errors.extend(
                    validate_component_path(
                        root, plugin_dir, manifest_path, field, manifest.get(field)
                    )
                )
        errors.extend(
            validate_private_skills(root, plugin_dir, standalone_names, private_seen)
        )
    return artifacts, errors

def marketplace_plugin(entry: dict, harness: str) -> tuple[str | None, str | None]:
    name = entry.get("name")
    source = entry.get("source")
    if harness == "Codex" and isinstance(source, dict):
        source = source.get("path")
    return name if isinstance(name, str) else None, source if isinstance(source, str) else None

def validate_marketplace(
    root: Path, relative: str, harness: str, plugin_names: set[str]
) -> list[str]:
    path = root / relative
    marketplace, errors = load_json(path, root)
    if marketplace is None:
        return errors
    entries = marketplace.get("plugins")
    if not isinstance(entries, list):
        return [failure(relative, "marketplace-plugins", "set `plugins` to an array")]
    found: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append(failure(relative, "marketplace-entry", "use an object for each plugin"))
            continue
        name, source = marketplace_plugin(entry, harness)
        if not name or not source:
            errors.append(
                failure(relative, "marketplace-entry", "give each plugin a valid `name` and `source`")
            )
            continue
        target = (root / source).resolve()
        expected = target / f".{harness.lower().split()[0]}-plugin" / "plugin.json"
        if not target.is_relative_to(root.resolve()) or not expected.is_file():
            errors.append(
                failure(relative, "marketplace-path", f"make `{source}` point to a {harness} plugin")
            )
            continue
        manifest, manifest_errors = load_json(expected, root)
        errors.extend(manifest_errors)
        if manifest is not None and manifest.get("name") != name:
            errors.append(
                failure(relative, "marketplace-name", f"make `{name}` match {expected.relative_to(root)}")
            )
        found.add(name)
    if found != plugin_names:
        errors.append(
            failure(
                relative,
                "marketplace-coverage",
                f"list exactly these plugins: {', '.join(sorted(plugin_names))}",
            )
        )
    return errors

def git_output(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout

def base_artifacts(root: Path, base_ref: str) -> dict[str, tuple[str, str | None]]:
    paths = git_output(root, "ls-tree", "-r", "--name-only", base_ref).splitlines()
    artifacts: dict[str, tuple[str, str | None]] = {}
    for path in paths:
        parts = Path(path).parts
        if path.endswith("/SKILL.md") and parts[0] == "skills" and len(parts) in {3, 4}:
            text = git_output(root, "show", f"{base_ref}:{path}")
            values, metadata, _ = parse_skill_text(text, path)
            name = values.get("name")
            if isinstance(name, str):
                version = metadata.get("version")
                artifacts[f"skill:{name}"] = (
                    str(Path(path).parent),
                    version if isinstance(version, str) else None,
                )
        if path.endswith("/.codex-plugin/plugin.json") and parts[0] == "plugins":
            manifest = json.loads(git_output(root, "show", f"{base_ref}:{path}"))
            name, version = manifest.get("name"), manifest.get("version")
            if isinstance(name, str):
                artifacts[f"plugin:{name}"] = (
                    str(Path(path).parents[1]),
                    version if isinstance(version, str) else None,
                )
    return artifacts

def semver_key(version: str) -> tuple:
    core, _, _build = version.partition("+")
    release, separator, prerelease = core.partition("-")
    pre = (
        (0, tuple((0, int(item)) if item.isdigit() else (1, item) for item in prerelease.split(".")))
        if separator
        else (1,)
    )
    return (*map(int, release.split(".")), pre)

def version_bump_errors(
    current: dict[str, tuple[str, str]],
    previous: dict[str, tuple[str, str | None]],
    changed_paths: set[str],
) -> list[str]:
    errors: list[str] = []
    for identity, (path, version) in current.items():
        if identity not in previous:
            continue
        old_path, old_version = previous[identity]
        changed = any(
            candidate == prefix or candidate.startswith(f"{prefix}/")
            for candidate in changed_paths
            for prefix in {path, old_path}
        )
        if changed and old_version and semver_key(version) <= semver_key(old_version):
            errors.append(
                failure(
                    path,
                    "artifact-version-bump",
                    f"bump {identity} above {old_version}; its distributable files changed",
                )
            )
    return errors

def run_check(root: Path, command: list[str], rule: str, fix: str) -> list[str]:
    result = subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode == 0:
        return []
    detail = result.stdout.strip().splitlines()
    suffix = f" ({detail[-1]})" if detail else ""
    source = Path(command[1]).relative_to(root) if len(command) > 1 else Path(".")
    return [failure(source, rule, f"{fix}{suffix}")]

def tracked_json_errors(root: Path) -> list[str]:
    paths = git_output(
        root, "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.json"
    ).splitlines()
    errors: list[str] = []
    for relative in paths:
        try:
            json.loads((root / relative).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(failure(relative, "json-syntax", f"fix JSON syntax: {exc}"))
    return errors

def validate_repository(root: Path, base_ref: str | None = None) -> list[str]:
    skill_artifacts, errors = validate_skills(root)
    plugin_artifacts, plugin_errors = validate_plugins(
        root, {identity.removeprefix("skill:") for identity in skill_artifacts}
    )
    errors.extend(plugin_errors)
    errors.extend(validate_collection_readmes(root))
    errors.extend(validate_npx_readmes(root))
    plugin_names = {identity.removeprefix("plugin:") for identity in plugin_artifacts}
    errors.extend(
        validate_marketplace(root, ".agents/plugins/marketplace.json", "Codex", plugin_names)
    )
    errors.extend(
        validate_marketplace(root, ".claude-plugin/marketplace.json", "Claude", plugin_names)
    )
    errors.extend(tracked_json_errors(root))
    errors.extend(
        run_check(
            root,
            [sys.executable, str(root / "scripts/render-plugin-directory.py"), "--check"],
            "generated-directory",
            "run `python3 scripts/render-plugin-directory.py`",
        )
    )
    errors.extend(
        run_check(
            root,
            [
                sys.executable,
                str(root / "plugins/codegraph-intelligence/scripts/check_codegraph_mcp.py"),
                "--static",
            ],
            "codegraph-capabilities",
            "align docs and skills with REQUIRED_TOOLS",
        )
    )
    if base_ref:
        changed = set(git_output(root, "diff", "--name-only", base_ref, "--").splitlines())
        errors.extend(
            version_bump_errors(
                {**skill_artifacts, **plugin_artifacts},
                base_artifacts(root, base_ref),
                changed,
            )
        )
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", help="compare artifact versions with this Git ref")
    parser.add_argument("--self-test", action="store_true", help="run negative contract checks")
    args = parser.parse_args()
    try:
        errors = (
            run_self_test(validate_skills, version_bump_errors, validate_plugins)
            if args.self_test
            else validate_repository(ROOT, args.base_ref)
        )
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        errors = [failure(".", "validator-runtime", f"fix validator input or environment: {exc}")]
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if not errors:
        print("Repository validation passed." if not args.self_test else "Validator self-check passed.")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())

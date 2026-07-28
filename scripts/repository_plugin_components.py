"""Plugin manifest component validation shared by repository checks."""

from __future__ import annotations

import json
from pathlib import Path


def failure(path: str | Path, rule: str, fix: str) -> str:
    return f"{Path(path).as_posix()}: [{rule}] {fix}"


def load_json(path: Path, root: Path) -> tuple[dict | None, list[str]]:
    source = path.relative_to(root).as_posix()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [failure(source, "json-present", "add the required JSON file")]
    except json.JSONDecodeError as exc:
        return None, [failure(source, "json-syntax", f"fix JSON syntax: {exc}")]
    if not isinstance(value, dict):
        return None, [failure(source, "json-object", "use a JSON object at the top level")]
    return value, []


def valid_mcp(document: dict) -> bool:
    return bool(document) and all(
        isinstance(server, dict)
        and isinstance(server.get("command"), str)
        and bool(server["command"].strip())
        and isinstance(server.get("args", []), list)
        and all(isinstance(arg, str) for arg in server.get("args", []))
        for server in document.values()
    )


def valid_hook_matcher(matcher: object) -> bool:
    if not isinstance(matcher, dict):
        return False
    hooks = matcher.get("hooks")
    return isinstance(hooks, list) and bool(hooks) and all(
        isinstance(hook, dict)
        and hook.get("type") == "command"
        and isinstance(hook.get("command"), str)
        and bool(hook["command"].strip())
        for hook in hooks
    )


def valid_hooks(document: dict) -> bool:
    events = document.get("hooks")
    return isinstance(events, dict) and bool(events) and all(
        isinstance(matchers, list)
        and bool(matchers)
        and all(valid_hook_matcher(matcher) for matcher in matchers)
        for matchers in events.values()
    )


def validate_component_path(
    root: Path, plugin_dir: Path, manifest_path: Path, field: str, value: object
) -> list[str]:
    if value is None:
        return []
    source = manifest_path.relative_to(root)
    if not isinstance(value, str) or not value:
        return [
            failure(source, "plugin-component-type", f"set `{field}` to one relative path string")
        ]
    target = (plugin_dir / value).resolve()
    if not target.is_relative_to(plugin_dir.resolve()):
        return [
            failure(source, "plugin-component-path", f"keep `{field}` inside {plugin_dir.name}")
        ]
    if field == "skills":
        if not target.is_dir() or not any(target.glob("*/SKILL.md")):
            return [
                failure(
                    source,
                    "plugin-component-path",
                    f"make `{field}: {value}` point to a skill directory",
                )
            ]
        return []
    if not target.is_file() or target.suffix != ".json":
        return [
            failure(
                source,
                "plugin-component-path",
                f"make `{field}: {value}` point to a JSON file",
            )
        ]
    document, errors = load_json(target, root.resolve())
    valid = (
        False
        if document is None
        else valid_mcp(document) if field == "mcpServers" else valid_hooks(document)
    )
    if document is not None and not valid:
        errors.append(
            failure(
                target.relative_to(root.resolve()),
                "plugin-component-content",
                f"add a valid {field} configuration",
            )
        )
    return errors

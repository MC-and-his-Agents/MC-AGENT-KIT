#!/usr/bin/env python3
"""Resolve an explicit ClawHub target and verify its remote ownership."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


HANDLE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NOT_FOUND = "skill not found or unavailable to this account"


class TargetError(ValueError):
    pass


@dataclass(frozen=True)
class Target:
    slug: str
    mode: str


def valid_handle(value: str) -> bool:
    return len(value) <= 64 and bool(HANDLE_PATTERN.fullmatch(value))


def resolve_target(raw_targets: str, path: str, publisher: str, owner: str) -> Target:
    try:
        targets = json.loads(raw_targets)
    except json.JSONDecodeError as exc:
        raise TargetError(f"CLAWHUB_TARGETS_JSON is invalid JSON: {exc}") from exc
    skill_path = PurePosixPath(path)
    if skill_path.is_absolute() or ".." in skill_path.parts:
        raise TargetError(f"invalid Skill path: {path!r}")
    if not isinstance(targets, dict) or not isinstance(targets.get(path), dict):
        raise TargetError(f"add an explicit ClawHub target for {path!r}")
    if not valid_handle(publisher):
        raise TargetError("CLAWHUB_PUBLISHER must be the expected kebab-case owner handle")
    if owner and (not valid_handle(owner) or owner != publisher):
        raise TargetError("CLAWHUB_OWNER must be empty or match CLAWHUB_PUBLISHER")

    entry = targets[path]
    slug, mode = entry.get("slug"), entry.get("mode")
    if not isinstance(slug, str) or not valid_handle(slug):
        raise TargetError(f"{path}: configure a valid kebab-case ClawHub slug")
    if mode not in {"new", "update"}:
        raise TargetError(f"{path}: ClawHub mode must be 'new' or 'update'")
    return Target(slug, mode)


def inspect_owner(payload: object) -> str:
    if not isinstance(payload, dict) or not isinstance(payload.get("owner"), dict):
        raise TargetError("ClawHub inspect returned no owner")
    handle = payload["owner"].get("handle")
    if not isinstance(handle, str) or not valid_handle(handle):
        raise TargetError("ClawHub inspect returned an invalid owner handle")
    return handle


def validate_inspection(
    target: Target,
    publisher: str,
    status: int,
    payload: object | None,
    error: str,
) -> None:
    if status == 0:
        remote_owner = inspect_owner(payload)
        if target.mode == "new":
            raise TargetError(
                f"ClawHub slug {target.slug!r} already belongs to {remote_owner!r}; "
                "choose another slug or explicitly configure mode 'update'"
            )
        if remote_owner != publisher:
            raise TargetError(
                f"ClawHub slug {target.slug!r} belongs to {remote_owner!r}, "
                f"not configured publisher {publisher!r}; choose another slug"
            )
        return
    detail = error.strip() or f"inspect exited with status {status}"
    if target.mode == "new" and NOT_FOUND in detail.casefold():
        return
    raise TargetError(f"cannot verify ownership of ClawHub slug {target.slug!r}: {detail}")


def write_outputs(path: Path, target: Target) -> None:
    with path.open("a", encoding="utf-8") as output:
        output.write(f"slug={target.slug}\n")
        output.write(f"mode={target.mode}\n")


def assert_error(callable_, text: str) -> None:
    try:
        callable_()
    except TargetError as exc:
        assert text in str(exc), exc
        return
    raise AssertionError(f"expected error containing {text!r}")


def run_self_test() -> None:
    raw = json.dumps({"skills/my-skill": {"slug": "my-skill-mc", "mode": "new"}})
    target = resolve_target(raw, "skills/my-skill", "my-owner", "")
    assert target == Target("my-skill-mc", "new")
    assert resolve_target(raw, "skills/my-skill", "my-owner", "my-owner") == target
    assert_error(lambda: resolve_target("{}", "skills/my-skill", "my-owner", ""), "explicit")
    assert_error(lambda: resolve_target(raw, "skills/my-skill", "my-owner", "other"), "match")
    validate_inspection(target, "my-owner", 1, None, "Skill not found or unavailable to this account")
    assert_error(
        lambda: validate_inspection(target, "my-owner", 0, {"owner": {"handle": "other"}}, ""),
        "already belongs",
    )
    update = Target("my-skill-mc", "update")
    validate_inspection(update, "my-owner", 0, {"owner": {"handle": "my-owner"}}, "")
    assert_error(
        lambda: validate_inspection(update, "my-owner", 0, {"owner": {"handle": "other"}}, ""),
        "not configured publisher",
    )
    assert_error(lambda: validate_inspection(update, "my-owner", 1, None, "not found"), "cannot verify")
    assert_error(lambda: validate_inspection(target, "my-owner", 1, None, "timeout"), "cannot verify")
    print("ClawHub target self-test passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-json")
    parser.add_argument("--path")
    parser.add_argument("--publisher")
    parser.add_argument("--owner", default="")
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--inspect-json", type=Path)
    parser.add_argument("--inspect-error", type=Path)
    parser.add_argument("--inspect-status", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            run_self_test()
            return 0
        if None in {args.targets_json, args.path, args.publisher}:
            parser.error("--targets-json, --path and --publisher are required")
        target = resolve_target(args.targets_json, args.path, args.publisher, args.owner)
        if args.github_output:
            write_outputs(args.github_output, target)
        if args.inspect_status is not None:
            if not args.inspect_json or not args.inspect_error:
                parser.error("--inspect-json and --inspect-error are required with --inspect-status")
            payload = json.loads(args.inspect_json.read_text()) if args.inspect_status == 0 else None
            error = args.inspect_error.read_text() if args.inspect_error else ""
            validate_inspection(target, args.publisher, args.inspect_status, payload, error)
        print(json.dumps({"slug": target.slug, "mode": target.mode}))
        return 0
    except (TargetError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

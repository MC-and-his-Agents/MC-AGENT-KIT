"""Shared discovery and validation for skill collections."""

from __future__ import annotations

from pathlib import Path


REPOSITORY = "MC-and-his-Agents/MC-SKILLS"


def discovered_collections(root: Path) -> list[str]:
    skills_root = root / "skills"
    return sorted(
        {
            path.relative_to(skills_root).parts[0]
            for path in skills_root.glob("*/*/SKILL.md")
        }
    )


def collection_readmes(root: Path) -> dict[str, Path]:
    return {
        path.parent.name: path
        for path in sorted((root / "skills").glob("*/README.md"))
    }


def error(path: Path, rule: str, fix: str) -> str:
    return f"{path.as_posix()}: [{rule}] {fix}"


def validate_collection_readmes(root: Path) -> list[str]:
    expected = set(discovered_collections(root))
    readmes = collection_readmes(root)
    actual = set(readmes)
    errors: list[str] = []
    for name in sorted(expected - actual):
        errors.append(
            error(
                Path("skills") / name / "README.md",
                "collection-readme",
                "add the collection README and generated member block",
            )
        )
    for name in sorted(actual - expected):
        errors.append(
            error(
                readmes[name].relative_to(root),
                "collection-orphan",
                "remove this README or add at least one nested skill",
            )
        )
    for name in sorted(expected & actual):
        text = readmes[name].read_text(encoding="utf-8")
        source = readmes[name].relative_to(root)
        markers = ("<!-- COLLECTION_MEMBERS_START -->", "<!-- COLLECTION_MEMBERS_END -->")
        if any(text.count(marker) != 1 for marker in markers):
            errors.append(
                error(source, "collection-members", "add exactly one generated member block")
            )
        members = sorted(
            path.parent.name for path in (root / "skills" / name).glob("*/SKILL.md")
        )
        for member in members:
            if f"[{member}](./{member}/SKILL.md)" not in text:
                errors.append(
                    error(source, "collection-members", f"regenerate the `{member}` member row")
                )
        skill_args = " ".join(f"--skill {member}" for member in members)
        command = f"npx skills add {REPOSITORY} {skill_args}"
        if command not in text:
            errors.append(
                error(source, "collection-command", "regenerate the batch install command")
            )
    return errors

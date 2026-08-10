"""Strict schema shared by the Tasks Owner trajectory replay."""

from __future__ import annotations

from datetime import datetime
from typing import Any


SCHEMA_VERSION = "tasks-owner-trajectory.v1"
ROOT_KEYS = set("schema_version id source_kind mode initial events expected evidence".split())
EVENT_KEYS = set("seq turn actor kind locator unit_id generation tool args facts".split())
EXPECTED_KEYS = {"verdict", "rule_id"}
MODES = {"app_thread", "direct", "convergence", "cleanup", "heartbeat"}
RULES = {"canonical_delivery", "writer_quiescence", "cleanup_terminal_consumed", "direct_wake", "heartbeat_backoff"}
MODE_RULES = {"app_thread": "canonical_delivery", "direct": "direct_wake", "convergence": "writer_quiescence", "cleanup": "cleanup_terminal_consumed", "heartbeat": "heartbeat_backoff"}
ACTORS = {"owner", "task", "app_task", "native_subagent", "reviewer", "cleanup_subagent", "external", "user"}
KINDS = set("unit_state delivery owner_wait completion completion_consumed successor head_readback fresh_review closeout handoff publish cleanup_spawn cleanup_readback heartbeat automation_update automation_readback external_event owner_final wake_verified".split())
TOOLS = set("spawn_agent wait_agent native_completion native_status list_agents codex_app__create_thread codex_app__send_message_to_thread codex_app__read_thread codex_app__automation_update git_readback reviewer_result gh_readback handoff_readback git_stage git_commit git_push gh_pr_create gh_pr_merge final native_completion_wake user_message github_event automation_wake".split())
EXECUTION_KINDS = {"app_task", "native_subagent", "cleanup_subagent"}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_iso(value: Any) -> bool:
    if not nonempty(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def writer_publishable(unit: dict[str, Any]) -> bool:
    if unit.get("host_status") == "terminal" and unit.get("write_authority") in {"revoked", "none"}:
        return True
    return (
        unit.get("execution_kind") == "app_task"
        and unit.get("host_status") == "quiesced"
        and unit.get("write_authority") == "revoked"
        and unit.get("host_quiesce_capability") == "verified"
        and nonempty(unit.get("quiesce_ack_locator"))
        and nonempty(unit.get("revocation_evidence_locator"))
        and nonempty(unit.get("observed_at"))
    )


def policy_matches(policy: Any, state: Any) -> bool:
    return (policy == "delete" and state in {"removed", "already_absent"}) or (policy == "preserve" and state == "preserved")


def schema_errors(case: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(case, dict):
        return ["case must be an object"]
    if set(case) != ROOT_KEYS:
        return ["root keys must match schema"]
    if case.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    if not nonempty(case.get("id")):
        errors.append("id must be non-empty")
    if case.get("source_kind") not in {"recorded_fixture", "live_readback"}:
        errors.append("invalid source_kind")
    if case.get("mode") not in MODES:
        errors.append("invalid mode")
    initial = case.get("initial")
    if not isinstance(initial, dict):
        errors.append("initial must be an object")
    elif case.get("mode") == "heartbeat":
        intervals = (initial.get("base_interval_seconds"), initial.get("current_interval_seconds"))
        if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in intervals):
            errors.append("heartbeat initial requires positive integer intervals")
        if initial.get("goal_status") not in {"complete", "incomplete"} or initial.get("cadence_override") not in {"none", "fixed_interval", "no_backoff"}:
            errors.append("heartbeat initial has invalid goal/cadence")
        if not nonempty(initial.get("automation_id")) or not nonempty(initial.get("owner_thread_id")) or not isinstance(initial.get("cadence_revision"), int) or isinstance(initial.get("cadence_revision"), bool):
            errors.append("heartbeat initial requires automation/owner/revision identity")
    elif case.get("mode") == "app_thread":
        runtime = initial.get("owner_runtime")
        if not nonempty(initial.get("owner_thread_id")) or not isinstance(runtime, dict) or any(not nonempty(runtime.get(key)) for key in ("model", "reasoning_effort")):
            errors.append("app_thread initial requires owner thread/runtime")
    expected = case.get("expected")
    if not isinstance(expected, dict) or set(expected) != EXPECTED_KEYS:
        errors.append("expected must contain verdict and rule_id")
    elif expected.get("verdict") not in {"pass", "fail"} or expected.get("rule_id") not in RULES:
        errors.append("invalid expected verdict/rule_id")
    elif expected.get("rule_id") != MODE_RULES.get(case.get("mode")):
        errors.append("mode and rule_id must match")
    evidence = case.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence must be an object")
    elif case.get("source_kind") == "recorded_fixture" and not nonempty(evidence.get("fixture_id")):
        errors.append("recorded_fixture requires fixture_id")
    elif case.get("source_kind") == "live_readback":
        required = {"host_id", "observed_at", "owner_turn_locator", "runtime_locator", "tool_readback_locator"}
        if any(not nonempty(evidence.get(key)) for key in required):
            errors.append("live_readback requires host/turn/runtime/time/tool evidence")
    events = case.get("events")
    if not isinstance(events, list) or not events:
        return errors + ["events must be a non-empty array"]
    locators: set[str] = set()
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or set(event) != EVENT_KEYS:
            errors.append(f"event {index} keys must match schema")
            continue
        seq = event.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq != index:
            errors.append(f"event {index} seq must be contiguous and ordered")
        if not nonempty(event.get("turn")) or event.get("actor") not in ACTORS or event.get("kind") not in KINDS:
            errors.append(f"event {index} has invalid turn/actor/kind")
        locator = event.get("locator")
        if not nonempty(locator) or locator in locators:
            errors.append(f"event {index} locator must be non-empty and unique")
        elif isinstance(locator, str):
            locators.add(locator)
        if event.get("tool") not in TOOLS:
            errors.append(f"event {index} has unknown tool")
        if event.get("unit_id") is not None and not nonempty(event.get("unit_id")):
            errors.append(f"event {index} has invalid unit_id")
        if event.get("generation") is not None and not nonempty(event.get("generation")):
            errors.append(f"event {index} has invalid generation")
        if not isinstance(event.get("args"), dict) or not isinstance(event.get("facts"), dict):
            errors.append(f"event {index} args/facts must be objects")
    return errors

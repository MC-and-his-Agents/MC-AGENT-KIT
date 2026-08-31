"""Replay Tasks Owner lifecycle facts and return violated rule ids."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tasks_owner_trajectory_schema import (
    nonempty as _nonempty,
    policy_matches as _policy_matches,
    real_locator as _real_locator,
    repair_budget_errors as _repair_budget_errors,
    schema_errors as _schema_errors,
    user_decision_errors as _user_decision_errors,
    valid_iso as _valid_iso,
    writer_publishable as _writer_publishable,
)

CANONICAL_EVENTS = {
    "DELIVERY_ROUTE_ACK", "contract_ack", "execution_release_ack", "STARTED", "BOOTSTRAP_READBACK",
    "FINAL_BATCH_READINESS", "PLANNING_READINESS", "CONVERGENCE_REQUEST", "SCOPE_DELTA", "BLOCKED",
    "NEEDS_OWNER", "PR_READY", "COMPLETED",
}
DELIVERY_ORDER = {"local_recorded": 0, "pending": 1, "delivered": 2, "owner_verified": 3, "consumed": 4}
UNIT_TRANSITIONS = {
    None: {"created", "running", "terminal"},
    "created": {"running", "terminal"},
    "running": {"quiescing", "terminal"},
    "quiescing": {"quiesced", "terminal"},
    "quiesced": {"terminal"},
    "terminal": set(),
}
PUBLISH_TOOLS = {"stage": "git_stage", "commit": "git_commit", "push": "git_push", "pr": "gh_pr_create", "merge": "gh_pr_merge"}
VERIFICATION_AUTHORITY_ORDER = ("user", "issue", "repository", "skill_default")


def _verification_errors(facts: dict[str, Any], exact_head: Any, tree_digest: Any) -> list[str]:
    errors: list[str] = []
    authority = facts.get("verification_authority")
    if not isinstance(authority, dict):
        return ["merge requires verification authority"]
    inputs = authority.get("authority_inputs")
    if not isinstance(inputs, dict) or set(inputs) != set(VERIFICATION_AUTHORITY_ORDER):
        return ["verification authority inputs are incomplete"]
    effective_source = next((source for source in VERIFICATION_AUTHORITY_ORDER if _real_locator(inputs.get(source))), None)
    if effective_source is None or authority.get("effective_source") != effective_source or authority.get("effective_locator") != inputs.get(effective_source):
        errors.append("verification authority priority is inverted")
    effective_required = authority.get("effective_required_checks")
    branch = authority.get("branch_protection")
    security = authority.get("security_contract")
    required: list[str] = []
    if not isinstance(effective_required, list) or any(not _real_locator(name) for name in effective_required) or len(effective_required) != len(set(effective_required)):
        errors.append("effective verification authority checks are invalid")
    else:
        required.extend(effective_required)
    for label, source in (("branch protection", branch), ("security contract", security)):
        if not isinstance(source, dict) or set(source) != {"locator", "required_checks"}:
            errors.append(f"{label} check authority is incomplete")
            continue
        checks = source.get("required_checks")
        locator = source.get("locator")
        if not isinstance(checks, list) or any(not _real_locator(name) for name in checks) or len(checks) != len(set(checks)) or (checks and not _real_locator(locator)):
            errors.append(f"{label} required checks are invalid")
            continue
        required.extend(checks)
    required = list(dict.fromkeys(required))
    results = facts.get("check_results")
    by_name: dict[str, dict[str, Any]] = {}
    if not isinstance(results, list):
        errors.append("merge check results are missing")
    else:
        for result in results:
            if (
                not isinstance(result, dict)
                or set(result) != {"name", "status", "locator", "head"}
                or not _real_locator(result.get("name"))
                or result.get("status") not in {"success", "failed", "pending"}
                or not _real_locator(result.get("locator"))
                or not _real_locator(result.get("head"))
                or result["name"] in by_name
            ):
                errors.append("merge check result is invalid")
                continue
            by_name[result["name"]] = result
    for name in required:
        result = by_name.get(name)
        if not result or result.get("status") != "success" or result.get("head") != exact_head:
            errors.append(f"required merge check is not successful on exact head: {name}")
    for field in ("acceptance_evidence_locator", "product_evidence_locator"):
        if not _real_locator(facts.get(field)):
            errors.append(f"merge requires {field}")
    pr_metadata = facts.get("pr_metadata")
    if (
        not isinstance(pr_metadata, dict)
        or set(pr_metadata) != {"locator", "head"}
        or not _real_locator(pr_metadata.get("locator"))
        or pr_metadata.get("head") != exact_head
    ):
        errors.append("merge requires exact-head PR metadata")
    if facts.get("product_readiness") != "ready":
        errors.append("merge requires independently proven product readiness")
    unrelated = facts.get("unrelated_check_failures", [])
    failed_extras = {name for name, result in by_name.items() if name not in required and result.get("status") == "failed"}
    if not isinstance(unrelated, list) or len(unrelated) != len(failed_extras):
        errors.append("unrelated check failures need explicit non-blocking disposition")
    else:
        dispositions = set()
        for item in unrelated:
            if (
                not isinstance(item, dict)
                or set(item) != {"name", "locator", "carrier_locator", "disposition", "native_dependency_created"}
                or item.get("name") not in failed_extras
                or not _real_locator(item.get("locator"))
                or not _real_locator(item.get("carrier_locator"))
                or item.get("disposition") != "backlog"
                or item.get("native_dependency_created") is not False
            ):
                errors.append("unrelated check failure incorrectly blocks current product readiness")
                continue
            dispositions.add(item["name"])
        if dispositions != failed_extras:
            errors.append("unrelated check failure disposition is incomplete")
    reuse = facts.get("verification_reuse")
    if reuse is not None:
        fields = {
            "current_tree_digest", "evidence_tree_digest", "current_acceptance_digest",
            "evidence_acceptance_digest", "current_environment_class",
            "evidence_environment_class", "evidence_locator",
        }
        if (
            not isinstance(reuse, dict)
            or set(reuse) != fields
            or any(not _real_locator(reuse.get(field)) for field in fields)
            or reuse.get("current_tree_digest") != reuse.get("evidence_tree_digest")
            or reuse.get("current_tree_digest") != tree_digest
            or reuse.get("current_acceptance_digest") != reuse.get("evidence_acceptance_digest")
            or reuse.get("current_environment_class") != reuse.get("evidence_environment_class")
        ):
            errors.append("verification evidence reuse key does not match")
    return errors


class Replay:
    def __init__(self, case: dict[str, Any]) -> None:
        self.case = case
        self.initial = case["initial"]
        self.violations: set[str] = set()
        self.units: dict[tuple[str, str], dict[str, Any]] = {}
        self.last_unit_change = 0
        self.completion_consumed: set[tuple[str, str]] = set()
        self.delivery_state: dict[str, tuple[int, str]] = {}
        self.delivery_locator: dict[str, str] = {}
        self.head_readbacks: list[dict[str, Any]] = []
        self.reviews: list[dict[str, Any]] = []
        self.closeout_seq = 0
        self.handoff_seq = 0
        self.cleanup_spawn_seq = 0
        self.cleanup_unit: tuple[str, str] | None = None
        self.cleanup_contract: dict[str, Any] | None = None
        self.direct_waits: dict[tuple[str, str], tuple[str, int]] = {}
        self.direct_completions: dict[tuple[str, str], tuple[str, int]] = {}
        self.direct_consumptions: dict[tuple[str, str], tuple[str, int]] = {}
        self.direct_successors: dict[tuple[str, str], tuple[str, int]] = {}
        self.completion_locators: dict[tuple[str, str], str] = {}
        self.verified_wakes: set[tuple[str, str]] = set()
        self.final_seq = 0
        self.final_turn = ""
        self.eligible_heartbeats: list[dict[str, Any]] = []
        self.current_interval = self.initial.get("current_interval_seconds")
        self.base_interval = self.initial.get("base_interval_seconds")
        self.cadence_revision = self.initial.get("cadence_revision")
        self.last_trigger_seq = 0
        self.pending_update: tuple[str, int, int, int] | None = None

    @staticmethod
    def unit_key(event: dict[str, Any]) -> tuple[str, str] | None:
        if event["unit_id"] and event["generation"]:
            return event["unit_id"], event["generation"]
        return None

    def unit_state(self, event: dict[str, Any]) -> None:
        key, facts, args = self.unit_key(event), event["facts"], event["args"]
        if key is None:
            self.violations.add("writer_quiescence")
            return
        previous = self.units.get(key, {}).get("host_status")
        status = facts.get("host_status")
        required = {"role", "is_writer", "execution_kind", "host_status", "write_authority", "observed_at"}
        execution_kind = facts.get("execution_kind")
        values_ok = (
            facts.get("role") in {"writer", "reviewer", "task", "cleanup"}
            and isinstance(facts.get("is_writer"), bool)
            and execution_kind in {"app_task", "native_subagent", "cleanup_subagent"}
            and status in {"created", "running", "quiescing", "quiesced", "terminal"}
            and facts.get("write_authority") in {"active", "revoked", "none", "unknown"}
            and _valid_iso(facts.get("observed_at"))
        )
        source_ok = (
            execution_kind in {"native_subagent", "cleanup_subagent"}
            and event["actor"] in {"owner", "native_subagent", "cleanup_subagent"}
            and event["tool"] in {"spawn_agent", "native_status"}
        ) or (
            execution_kind == "app_task"
            and event["actor"] in {"owner", "app_task"}
            and event["tool"] in {"codex_app__create_thread", "codex_app__read_thread"}
        )
        if not source_ok or not values_ok:
            self.violations.add("writer_quiescence")
        if execution_kind == "cleanup_subagent" and (facts.get("role"), facts.get("is_writer")) != ("cleanup", False):
            self.violations.add("writer_quiescence")
        if previous is not None:
            old = self.units[key]
            if any(old.get(field) != facts.get(field) for field in ("role", "is_writer", "execution_kind")):
                self.violations.add("writer_quiescence")
        if status != previous and status not in UNIT_TRANSITIONS.get(previous, set()):
            self.violations.add("writer_quiescence")
        if any(field not in facts for field in required):
            self.violations.add("writer_quiescence")
        if (facts.get("role") == "writer") != (facts.get("is_writer") is True):
            self.violations.add("writer_quiescence")
        if facts.get("execution_kind") == "native_subagent" and status == "quiesced":
            self.violations.add("writer_quiescence")
        if facts.get("execution_kind") == "native_subagent" and previous is None and event["tool"] == "spawn_agent":
            if event["actor"] != "owner":
                self.violations.add("direct_wake")
            runtime = (event["tool"], args.get("model"), args.get("reasoning_effort"), args.get("fork_turns"))
            if runtime != ("spawn_agent", "gpt-5.6-luna", "max", "none"):
                self.violations.add("direct_wake")
        if facts.get("execution_kind") == "native_subagent" and previous is None and event["tool"] == "native_status":
            runtime = (facts.get("runtime_model"), facts.get("runtime_reasoning_effort"), _nonempty(facts.get("runtime_locator")))
            if runtime != ("gpt-5.6-luna", "max", True):
                self.violations.add("writer_quiescence")
        if self.case["mode"] == "direct" and facts.get("execution_kind") == "native_subagent" and previous is None and event["tool"] != "spawn_agent":
            self.violations.add("direct_wake")
        if facts.get("execution_kind") == "app_task" and previous is None and event["tool"] == "codex_app__create_thread":
            if (args.get("model"), args.get("thinking")) != ("gpt-5.6-luna", "max"):
                self.violations.add("writer_quiescence")
        if facts.get("execution_kind") == "app_task" and previous is None and event["tool"] == "codex_app__read_thread":
            if (facts.get("runtime_model"), facts.get("runtime_reasoning_effort"), _nonempty(facts.get("runtime_locator"))) != ("gpt-5.6-luna", "max", True):
                self.violations.add("writer_quiescence")
        self.units[key] = {**facts, "seq": event["seq"], "evidence_locator": event["locator"]}
        if sum(1 for unit in self.units.values() if unit.get("is_writer")) > 1:
            self.violations.add("writer_quiescence")
        self.last_unit_change = event["seq"]

    def delivery(self, event: dict[str, Any]) -> None:
        facts, args = event["facts"], event["args"]
        canonical, key, state = facts.get("event"), facts.get("event_key"), facts.get("delivery_state")
        if canonical not in CANONICAL_EVENTS or not _nonempty(key) or state not in DELIVERY_ORDER:
            self.violations.add("canonical_delivery")
            return
        previous = self.delivery_state.get(key)
        order = DELIVERY_ORDER[state]
        if previous and (order <= previous[0] or canonical != previous[1]):
            self.violations.add("canonical_delivery")
        self.delivery_state[key] = order, canonical
        if state == "local_recorded":
            if (
                event["actor"] not in {"task", "app_task"}
                or event["tool"] != "final"
                or facts.get("route_status") != f"{canonical}_LOCAL_RECORDED"
                or not _valid_iso(facts.get("recorded_at"))
                or _real_locator(facts.get("message_locator"))
            ):
                self.violations.add("canonical_delivery")
            return
        if state == "pending":
            if event["actor"] not in {"task", "app_task"} or event["tool"] != "codex_app__send_message_to_thread":
                self.violations.add("canonical_delivery")
            if facts.get("route_status") != f"{canonical}_PENDING_DELIVERY" or not facts.get("failure_code"):
                self.violations.add("canonical_delivery")
            if facts.get("message_locator") not in {None, "missing"}:
                self.violations.add("canonical_delivery")
            return
        if state == "delivered":
            runtime = self.initial.get("owner_runtime", {})
            target = (args.get("threadId"), args.get("model"), args.get("thinking"))
            expected = (self.initial.get("owner_thread_id"), runtime.get("model"), runtime.get("reasoning_effort"))
            locator = facts.get("message_locator")
            if event["actor"] not in {"task", "app_task"} or event["tool"] != "codex_app__send_message_to_thread" or target != expected:
                self.violations.add("canonical_delivery")
            evidence_ok = _real_locator(facts.get("tool_result_locator")) and _real_locator(facts.get("target_readback_locator"))
            if facts.get("route_status") != "armed" or not _valid_iso(facts.get("received_at")) or not _real_locator(locator) or not evidence_ok or self._retains_failure(facts):
                self.violations.add("canonical_delivery")
            elif isinstance(locator, str):
                self.delivery_locator[key] = locator
            return
        if event["actor"] != "owner" or event["tool"] != "codex_app__read_thread" or facts.get("message_locator") != self.delivery_locator.get(key):
            self.violations.add("canonical_delivery")
        if self._retains_failure(facts):
            self.violations.add("canonical_delivery")
        required_previous = "delivered" if state == "owner_verified" else "owner_verified"
        time_field = "verified_at" if state == "owner_verified" else "consumed_at"
        if not _valid_iso(facts.get(time_field)):
            self.violations.add("canonical_delivery")
        if not previous or previous[0] != DELIVERY_ORDER[required_previous]:
            self.violations.add("canonical_delivery")

    @staticmethod
    def _retains_failure(facts: dict[str, Any]) -> bool:
        stale = ("failure_code", "failure_event", "missing_locator", "error_locator", "pending_locator", "host_evidence_locator", "evidence_locator", "pending_delivery")
        return any(field in facts for field in stale) or str(facts.get("route_status", "")).endswith("_PENDING_DELIVERY")

    def direct_event(self, event: dict[str, Any]) -> None:
        kind, key, facts = event["kind"], self.unit_key(event), event["facts"]
        if kind == "owner_final":
            if event["actor"] != "owner" or event["tool"] != "final":
                self.violations.add("direct_wake")
            self.final_seq = event["seq"]
            self.final_turn = event["turn"]
            for unit_key, unit in self.units.items():
                if unit.get("execution_kind") == "native_subagent" and unit.get("host_status") != "terminal" and unit_key not in self.verified_wakes:
                    self.violations.add("direct_wake")
            return
        if key is None:
            return
        value = event["turn"], event["seq"]
        if kind == "owner_wait":
            timeout = event["args"].get("timeout_ms")
            if event["actor"] != "owner" or event["tool"] != "wait_agent" or not isinstance(timeout, int) or isinstance(timeout, bool) or not 10_000 <= timeout <= 60_000:
                self.violations.add("direct_wake")
            else:
                self.direct_waits[key] = value
        elif kind == "completion":
            locator = facts.get("completion_locator")
            unit_kind = self.units.get(key, {}).get("execution_kind")
            source_ok = (
                unit_kind == "app_task" and event["actor"] == "app_task" and event["tool"] == "codex_app__send_message_to_thread"
            ) or (
                unit_kind in {"native_subagent", "cleanup_subagent"}
                and event["actor"] in {"native_subagent", "cleanup_subagent"}
                and event["tool"] == "native_completion"
            )
            if not source_ok or not _real_locator(locator):
                self.violations.add("direct_wake" if self.case["mode"] == "direct" else "cleanup_terminal_consumed")
            else:
                self.completion_locators[key] = locator
            self.direct_completions[key] = value
        elif kind == "completion_consumed":
            locator = facts.get("completion_locator")
            valid_actor = event["actor"] == "owner" and event["tool"] in {"native_completion", "native_status", "codex_app__read_thread"}
            if not valid_actor or not _real_locator(locator) or key not in self.completion_locators or locator != self.completion_locators[key] or facts.get("owner_consumption") != "consumed":
                self.violations.add("direct_wake" if self.case["mode"] == "direct" else "cleanup_terminal_consumed")
            else:
                self.direct_consumptions[key] = value
                self.completion_consumed.add(key)
        elif kind == "successor":
            if event["actor"] != "owner" or event["tool"] not in {"spawn_agent", "codex_app__send_message_to_thread"} or facts.get("successor_dispatched") is not True:
                self.violations.add("direct_wake")
            if event["tool"] == "spawn_agent" and (event["args"].get("model"), event["args"].get("reasoning_effort"), event["args"].get("fork_turns")) != ("gpt-5.6-luna", "max", "none"):
                self.violations.add("direct_wake")
            if event["tool"] == "codex_app__send_message_to_thread" and (event["args"].get("model"), event["args"].get("thinking")) != ("gpt-5.6-luna", "max"):
                self.violations.add("direct_wake")
            self.direct_successors[key] = value
        elif kind == "wake_verified" and self.case["source_kind"] == "live_readback":
            valid = event["actor"] == "owner" and event["tool"] == "native_completion_wake"
            valid = valid and facts.get("native_completion_wake") == "verified"
            valid = valid and all(_real_locator(facts.get(field)) for field in ("wake_locator", "host_id", "tool_result_locator"))
            valid = valid and _valid_iso(facts.get("observed_at"))
            if valid:
                self.verified_wakes.add(key)
            else:
                self.violations.add("direct_wake")

    def publication_event(self, event: dict[str, Any]) -> None:
        kind, facts, seq = event["kind"], event["facts"], event["seq"]
        if kind == "head_readback":
            if event["actor"] == "owner" and event["tool"] == "git_readback" and all(_real_locator(facts.get(field)) for field in ("diff_locator", "file_hashes_locator", "tree_digest", "exact_head")):
                self.head_readbacks.append({"seq": seq, "head": facts["exact_head"], "diff": facts["diff_locator"], "tree": facts["tree_digest"]})
            else:
                self.violations.add("writer_quiescence")
            return
        if kind == "fresh_review":
            fields_ok = facts.get("verdict") == "ship" and facts.get("writer_quiescence") == "verified"
            fields_ok = fields_ok and _real_locator(facts.get("reviewed_head")) and _real_locator(facts.get("writer_evidence_locator"))
            fields_ok = fields_ok and event["actor"] == "reviewer" and event["tool"] == "reviewer_result"
            readback = self.head_readbacks[-1] if self.head_readbacks else None
            fields_ok = fields_ok and isinstance(facts.get("reviewed_files"), list) and bool(facts.get("reviewed_files"))
            fields_ok = fields_ok and facts.get("review_write_scope") == "empty" and facts.get("semantic_scope_status") == "aligned"
            fields_ok = fields_ok and bool(readback) and facts.get("diff_locator") == readback["diff"]
            writer_locators = sorted(unit.get("evidence_locator") for unit in self.units.values() if unit.get("is_writer"))
            supplied_writer_locators = facts.get("writer_evidence_locators", [])
            fields_ok = fields_ok and isinstance(supplied_writer_locators, list)
            fields_ok = fields_ok and all(_real_locator(locator) for locator in supplied_writer_locators)
            fields_ok = fields_ok and sorted(supplied_writer_locators) == writer_locators
            fields_ok = fields_ok and facts.get("writer_evidence_locator") in writer_locators
            if fields_ok:
                self.reviews.append({"seq": seq, "head": facts["reviewed_head"]})
            else:
                self.violations.add("writer_quiescence")
            return
        action, exact_head = facts.get("action"), facts.get("exact_head")
        writers = [unit for unit in self.units.values() if unit.get("is_writer")]
        if not writers or any(not _writer_publishable(unit) for unit in writers):
            self.violations.add("writer_quiescence")
        writer_keys = [key for key, unit in self.units.items() if unit.get("is_writer")]
        if any(key not in self.completion_consumed for key in writer_keys):
            self.violations.add("writer_quiescence")
        readback = next((item for item in reversed(self.head_readbacks) if item["seq"] > self.last_unit_change and item["head"] == exact_head), None)
        review = next((item for item in reversed(self.reviews) if readback and item["seq"] > readback["seq"] and item["head"] == exact_head), None)
        if event["actor"] != "owner" or action not in PUBLISH_TOOLS or event["tool"] != PUBLISH_TOOLS.get(action) or not readback or not review:
            self.violations.add("writer_quiescence")
        if action == "merge" and _verification_errors(facts, exact_head, readback.get("tree") if readback else None):
            self.violations.add("writer_quiescence")

    def cleanup_event(self, event: dict[str, Any]) -> None:
        kind, facts, args, seq = event["kind"], event["facts"], event["args"], event["seq"]
        if kind == "closeout":
            if event["actor"] != "owner" or event["tool"] != "gh_readback":
                self.violations.add("cleanup_terminal_consumed")
            merged = all(_real_locator(facts.get(field)) for field in ("merge_commit", "target_head", "issue_state_locator"))
            no_pr = _real_locator(facts.get("no_pr_justification")) and _real_locator(facts.get("no_pr_evidence_locator"))
            if facts.get("closeout_verified") is True and (merged ^ no_pr):
                self.closeout_seq = seq
            else:
                self.violations.add("cleanup_terminal_consumed")
            return
        if kind == "handoff":
            if event["actor"] == "owner" and event["tool"] == "handoff_readback" and sorted(facts.get("active_locators", [])) == sorted(key[0] for key in self.units):
                self.handoff_seq = seq
            return
        if kind == "cleanup_readback":
            valid = self.cleanup_spawn_seq and seq > self.cleanup_spawn_seq and event["actor"] == "owner" and event["tool"] == "git_readback"
            cleanup = self.units.get(self.cleanup_unit or ("", ""), {})
            valid = valid and cleanup.get("host_status") == "terminal" and self.cleanup_unit in self.completion_consumed
            valid = valid and cleanup.get("execution_kind") == "cleanup_subagent" and cleanup.get("role") == "cleanup" and cleanup.get("is_writer") is False
            worktree_policy = facts.get("worktree_policy")
            worktree_ok = facts.get("worktree_absent") is True if worktree_policy == "delete" else facts.get("worktree_state") == "preserved"
            valid = valid and worktree_policy in {"delete", "preserve"} and worktree_ok
            valid = valid and all(facts.get(field) is True for field in ("target_unchanged", "cleanup_verified"))
            ref_states = {"removed", "preserved", "already_absent"}
            valid = valid and facts.get("local_ref_state") in ref_states and facts.get("remote_ref_state") in ref_states
            valid = valid and _policy_matches(facts.get("local_branch_policy"), facts.get("local_ref_state"))
            valid = valid and _policy_matches(facts.get("remote_branch_policy"), facts.get("remote_ref_state"))
            contract = self.cleanup_contract or {}
            valid = valid and all(facts.get(field) == contract.get(field) for field in (
                "target_repository", "target_worktree", "target_ref", "target_oid",
                "cleanup_action", "worktree_policy", "local_branch_policy", "remote_branch_policy",
            ))
            valid = valid and facts.get("predelete_oid_verified") is True
            valid = valid and _real_locator(facts.get("identity_readback_locator"))
            if not valid:
                self.violations.add("cleanup_terminal_consumed")
            return
        self.cleanup_spawn_seq = seq
        self.cleanup_unit = self.unit_key(event)
        units = list(self.units.items())
        lifecycle_ok = bool(units) and all(unit.get("host_status") == "terminal" for _, unit in units)
        lifecycle_ok = lifecycle_ok and all(not unit.get("is_writer") or unit.get("write_authority") in {"revoked", "none"} for _, unit in units)
        lifecycle_ok = lifecycle_ok and all(key in self.completion_consumed for key, _ in units)
        lifecycle_ok = lifecycle_ok and bool(self.closeout_seq and self.handoff_seq and self.closeout_seq < seq and self.handoff_seq < seq)
        if not lifecycle_ok:
            self.violations.add("cleanup_terminal_consumed")
        runtime = (event["actor"], event["tool"], args.get("model"), args.get("reasoning_effort"), args.get("fork_turns"))
        if runtime != ("owner", "spawn_agent", "gpt-5.6-luna", "max", "none"):
            self.violations.add("cleanup_terminal_consumed")
        cwd, target = args.get("cwd"), args.get("target_worktree")
        path_ok = _nonempty(cwd) and _nonempty(target) and Path(cwd).is_absolute() and Path(target).is_absolute()
        if path_ok:
            cwd_path, target_path = Path(cwd).resolve(), Path(target).resolve()
            path_ok = cwd_path != target_path and not target_path.is_relative_to(cwd_path) and not cwd_path.is_relative_to(target_path)
        contract_fields = (
            "target_repository", "target_worktree", "target_ref", "target_oid", "cleanup_action",
            "worktree_policy", "local_branch_policy", "remote_branch_policy", "identity_locator",
        )
        contract = facts if all(_real_locator(facts.get(field)) for field in contract_fields) else None
        path_ok = path_ok and bool(contract) and facts.get("target_worktree") == str(Path(target).resolve())
        if not path_ok:
            self.violations.add("cleanup_terminal_consumed")
        else:
            self.cleanup_contract = {field: facts[field] for field in contract_fields}

    def heartbeat_event(self, event: dict[str, Any]) -> None:
        kind, facts, args, seq = event["kind"], event["facts"], event["args"], event["seq"]
        if kind == "heartbeat":
            if event["actor"] != "owner" or event["tool"] != "automation_wake":
                self.violations.add("heartbeat_backoff")
            identity = (facts.get("automation_id"), facts.get("owner_thread_id"), facts.get("cadence_revision"))
            expected_identity = (self.initial.get("automation_id"), self.initial.get("owner_thread_id"), self.cadence_revision)
            if identity != expected_identity:
                self.violations.add("heartbeat_backoff")
            eligible = self._heartbeat_eligible(facts)
            if eligible:
                signature = (facts["state_digest"], facts.get("user_feedback_revision"), facts.get("external_fact_revision"))
                previous = self.eligible_heartbeats[-1]["signature"] if self.eligible_heartbeats else None
                self.eligible_heartbeats = self.eligible_heartbeats + [{"seq": seq, "signature": signature}] if signature == previous or previous is None else [{"seq": seq, "signature": signature}]
            else:
                self.eligible_heartbeats = []
            return
        if kind == "external_event":
            if event["actor"] not in {"external", "user", "task", "app_task"} or event["tool"] not in {"github_event", "user_message", "codex_app__send_message_to_thread"}:
                self.violations.add("heartbeat_backoff")
            self.last_trigger_seq = seq
            self.eligible_heartbeats = []
            if self.pending_update:
                self.violations.add("heartbeat_backoff")
            return
        if kind == "automation_readback":
            valid = self.pending_update and seq > self.pending_update[2] and event["actor"] == "owner" and event["tool"] == "codex_app__automation_update"
            valid = valid and facts.get("current_interval_seconds") == self.pending_update[1] and _real_locator(facts.get("automation_locator"))
            valid = valid and (facts.get("automation_id"), facts.get("owner_thread_id"), facts.get("cadence_revision")) == (self.initial.get("automation_id"), self.initial.get("owner_thread_id"), self.pending_update[3])
            if not valid:
                self.violations.add("heartbeat_backoff")
            else:
                self.current_interval = self.pending_update[1]
                self.cadence_revision = self.pending_update[3]
                self.pending_update = None
                self.eligible_heartbeats = []
            return
        if self.pending_update:
            self.violations.add("heartbeat_backoff")
        target, reason = args.get("interval_seconds"), facts.get("reason")
        next_revision = self.cadence_revision + 1
        identity_ok = (args.get("automation_id"), args.get("targetThreadId"), facts.get("cadence_revision")) == (self.initial.get("automation_id"), self.initial.get("owner_thread_id"), next_revision)
        if not identity_ok:
            self.violations.add("heartbeat_backoff")
        if reason == "backoff":
            expected = min(int(self.current_interval or 0) * 2, 24 * 60 * 60)
            adjacent = bool(self.eligible_heartbeats and self.eligible_heartbeats[-1]["seq"] + 1 == seq)
            if len(self.eligible_heartbeats) < 3 or not adjacent or target != expected or self.initial.get("cadence_override") != "none":
                self.violations.add("heartbeat_backoff")
        elif reason == "restore":
            if not self.last_trigger_seq or self.last_trigger_seq >= seq or target != self.base_interval:
                self.violations.add("heartbeat_backoff")
        else:
            self.violations.add("heartbeat_backoff")
        if event["actor"] != "owner" or event["tool"] != "codex_app__automation_update" or not isinstance(target, int) or isinstance(target, bool):
            self.violations.add("heartbeat_backoff")
        self.pending_update = (reason, target, seq, next_revision) if isinstance(target, int) and not isinstance(target, bool) else None

    def _heartbeat_eligible(self, facts: dict[str, Any]) -> bool:
        return (
            self.initial.get("goal_status") == "incomplete"
            and self.initial.get("cadence_override") == "none"
            and facts.get("goal_status") == "incomplete"
            and facts.get("cadence_override") == "none"
            and facts.get("wait_kind") in {"waiting_user", "waiting_external"}
            and _real_locator(facts.get("state_digest"))
            and _real_locator(facts.get("user_feedback_revision"))
            and _real_locator(facts.get("external_fact_revision"))
            and all(isinstance(facts.get(field), int) and not isinstance(facts.get(field), bool) and facts.get(field) == 0 for field in ("active_units", "active_writers"))
            and all(facts.get(field) is False for field in ("late_completion", "pending_delivery", "unconsumed_owner_event", "owner_action", "ready_successor", "admission_pending"))
        )

    def handle(self, event: dict[str, Any]) -> None:
        kind = event["kind"]
        if self.cleanup_spawn_seq and kind != "cleanup_readback":
            key = self.unit_key(event)
            allowed = kind in {"unit_state", "completion", "completion_consumed"} and key == self.cleanup_unit
            if not allowed:
                self.violations.add("cleanup_terminal_consumed")
        if kind == "unit_state":
            self.unit_state(event)
        elif kind == "delivery":
            self.delivery(event)
        elif kind in {"owner_wait", "completion", "completion_consumed", "successor", "wake_verified", "owner_final"}:
            self.direct_event(event)
        elif kind in {"head_readback", "fresh_review", "publish"}:
            self.publication_event(event)
        elif kind in {"closeout", "handoff", "cleanup_spawn", "cleanup_readback"}:
            self.cleanup_event(event)
        elif kind in {"heartbeat", "automation_update", "automation_readback", "external_event"}:
            self.heartbeat_event(event)

    def finish(self) -> set[str]:
        if self.pending_update:
            self.violations.add("heartbeat_backoff")
        if self.case["mode"] == "direct":
            native = [key for key, unit in self.units.items() if unit.get("execution_kind") == "native_subagent" and unit.get("is_writer")]
            if not native:
                self.violations.add("direct_wake")
            for key in native:
                wait, completion = self.direct_waits.get(key), self.direct_completions.get(key)
                consumed, successor = self.direct_consumptions.get(key), self.direct_successors.get(key)
                if not wait or not completion or not consumed:
                    self.violations.add("direct_wake")
                    continue
                if not (wait[0] == completion[0] == consumed[0] and wait[1] < completion[1] < consumed[1]):
                    self.violations.add("direct_wake")
                if self.final_turn != wait[0]:
                    self.violations.add("direct_wake")
                if self.initial.get("goal_status") == "incomplete" and (not successor or successor[0] != consumed[0] or successor[1] <= consumed[1]):
                    self.violations.add("direct_wake")
                last_required = successor[1] if self.initial.get("goal_status") == "incomplete" and successor else consumed[1]
                if not self.final_seq or self.final_seq <= last_required:
                    self.violations.add("direct_wake")
        if self.case["mode"] == "cleanup" and self.cleanup_spawn_seq and not any(event["kind"] == "cleanup_readback" for event in self.case["events"]):
            self.violations.add("cleanup_terminal_consumed")
        return self.violations


class ReviewReplay:
    """Replay review finding admission and the convergence-chain fix budget.

    This is intentionally a small state machine: review evidence remains exact-head and
    writer-quiescence evidence, while only a proven semantic chain change can reset the
    budget. Owner, reviewer, task, branch, file, head, and generation are observations.
    """

    DISPOSITIONS = {"fix_now", "defer", "reject", "shrink", "split", "reassign", "user_decision"}
    SEVERITIES = {"P0", "P1", "P2", "P3"}
    BOUNDARIES = {"none", "production_subsystem", "permission_or_runtime"}
    SCOPE_CHANGES = {"shrink", "split", "reassign"}

    def __init__(self, case: dict[str, Any]) -> None:
        initial = case["initial"]
        self.case = case
        self.violations: set[str] = set()
        self.task_key = initial["task_key"]
        self.scope_revision = initial["scope_revision"]
        self.decision_boundary_locator = initial.get("decision_boundary_locator")
        budget = initial["repair_budget"]
        self.convergence_chain_locator = budget["convergence_chain_locator"]
        self.round_count = budget["finding_write_consumed"]
        self.first_review_seen = False
        self.current_review: dict[str, Any] | None = None
        self.dispositions: dict[str, dict[str, Any]] = {}
        self.pending_fix: set[str] = set()
        self.pending_scope_change: set[str] = set()
        self.awaiting_fresh_review = False
        self.last_write_head: str | None = None
        self.last_review_head: str | None = None

    @staticmethod
    def _required(facts: dict[str, Any], fields: tuple[str, ...]) -> bool:
        return all(_nonempty(facts.get(field)) for field in fields)

    def _scope_matches(self, facts: dict[str, Any]) -> bool:
        return facts.get("task_key") == self.task_key and facts.get("scope_revision") == self.scope_revision

    def _review_common_valid(self, event: dict[str, Any], facts: dict[str, Any]) -> bool:
        return (
            event["actor"] == "reviewer"
            and event["tool"] == "reviewer_result"
            and facts.get("verdict") in {"fix-first", "ship", "rethink", "blocked"}
            and self._scope_matches(facts)
            and all(_real_locator(facts.get(field)) for field in ("reviewer_locator", "reviewed_head", "diff_locator", "execution_generation"))
            and isinstance(facts.get("reviewed_files"), list)
            and bool(facts.get("reviewed_files"))
            and facts.get("review_write_scope") == "empty"
            and facts.get("writer_quiescence") == "verified"
            and facts.get("semantic_scope_status") == "aligned"
        )

    def fresh_review(self, event: dict[str, Any]) -> None:
        facts = event["facts"]
        if not self._review_common_valid(event, facts):
            self.violations.add("review_disposition")
            return
        if self.current_review is not None:
            prior_findings = set(self.current_review.get("finding_locators", []))
            if not prior_findings.issubset(self.dispositions):
                self.violations.add("review_disposition")
        verdict = facts["verdict"]
        findings = facts.get("finding_locators", [])
        if not isinstance(findings, list) or any(not _real_locator(value) for value in findings) or len(set(findings)) != len(findings):
            self.violations.add("review_disposition")
            return
        if verdict == "fix-first" and not findings:
            self.violations.add("review_disposition")
        if verdict == "ship" and not set(findings).issubset(self.dispositions):
            self.violations.add("review_disposition")
        if self.last_review_head is not None and not self.awaiting_fresh_review and facts["reviewed_head"] != self.last_review_head:
            self.violations.add("review_disposition")
        if self.awaiting_fresh_review and facts["reviewed_head"] != self.last_write_head:
            self.violations.add("review_disposition")
        if verdict == "ship" and self.pending_fix:
            self.violations.add("review_disposition")
        if self.pending_scope_change:
            self.violations.add("review_disposition")
        self.first_review_seen = True
        self.current_review = {**facts, "finding_locators": findings, "seq": event["seq"]}
        self.dispositions = {}
        self.pending_fix = set()
        self.awaiting_fresh_review = False
        self.last_review_head = facts["reviewed_head"]

    def finding_disposition(self, event: dict[str, Any]) -> None:
        facts = event["facts"]
        required = (
            "finding_locator", "severity", "acceptance_or_invariant_locator",
            "unsafe_evidence_locator", "disposition", "carrier_locator",
            "rejection_basis", "boundary_expansion", "task_key", "scope_revision",
            "reviewed_head", "reviewer_locator", "execution_generation", "blocker_class",
        )
        valid = event["actor"] == "owner" and event["tool"] == "reviewer_result" and self._required(facts, required)
        valid = valid and self.current_review is not None and self._scope_matches(facts)
        valid = valid and facts.get("finding_locator") in self.current_review.get("finding_locators", [])
        valid = valid and facts.get("reviewed_head") == self.current_review.get("reviewed_head")
        valid = valid and facts.get("reviewer_locator") == self.current_review.get("reviewer_locator")
        valid = valid and facts.get("severity") in self.SEVERITIES
        valid = valid and facts.get("disposition") in self.DISPOSITIONS
        valid = valid and isinstance(facts.get("current_outcome_unsafe_without_fix"), bool)
        valid = valid and facts.get("boundary_expansion") in self.BOUNDARIES
        valid = valid and all(_real_locator(facts.get(field)) for field in (
            "finding_locator", "reviewed_head", "reviewer_locator", "execution_generation", "blocker_class",
        ))
        valid = valid and (
            facts.get("acceptance_or_invariant_locator") == "none"
            or _real_locator(facts.get("acceptance_or_invariant_locator"))
        )
        valid = valid and (
            facts.get("unsafe_evidence_locator") == "none"
            or _real_locator(facts.get("unsafe_evidence_locator"))
        )
        if not valid or facts.get("finding_locator") in self.dispositions:
            self.violations.add("review_disposition")
            return
        disposition = facts["disposition"]
        mapped = _real_locator(facts["acceptance_or_invariant_locator"])
        high_risk = facts["severity"] in {"P0", "P1"}
        must_resolve = facts["current_outcome_unsafe_without_fix"] and (mapped or high_risk)
        if must_resolve and not _real_locator(facts.get("unsafe_evidence_locator")):
            self.violations.add("review_disposition")
        if must_resolve and disposition in {"defer", "reject"}:
            self.violations.add("review_disposition")
        if must_resolve and disposition in self.SCOPE_CHANGES:
            self.pending_scope_change.add(facts["finding_locator"])
        if disposition in {"defer", "shrink", "split", "reassign"} and not _real_locator(facts.get("carrier_locator")):
            self.violations.add("review_disposition")
        if disposition == "reject" and (not _nonempty(facts.get("rejection_basis")) or facts.get("rejection_basis") == "none"):
            self.violations.add("review_disposition")
        if disposition == "user_decision" and (
            not _real_locator(facts.get("user_decision_locator"))
            or _user_decision_errors(facts, self.decision_boundary_locator)
        ):
            self.violations.add("review_disposition")
        if disposition == "fix_now":
            valid_fix = (
                (mapped or high_risk)
                and facts["current_outcome_unsafe_without_fix"]
                and facts["boundary_expansion"] == "none"
                and _real_locator(facts["unsafe_evidence_locator"])
            )
            if not valid_fix:
                self.violations.add("review_disposition")
            else:
                self.pending_fix.add(facts["finding_locator"])
        self.dispositions[facts["finding_locator"]] = facts

    def review_write(self, event: dict[str, Any]) -> None:
        facts = event["facts"]
        required = (
            "task_key", "scope_revision", "execution_generation", "base_reviewed_head",
            "new_head", "writer_evidence_locator", "writer_quiescence", "boundary_expansion",
        )
        valid = (
            event["actor"] in {"owner", "task"}
            and event["tool"] == "git_commit"
            and self.first_review_seen
            and self.current_review is not None
            and self.current_review.get("verdict") == "fix-first"
            and self._required(facts, required)
            and self._scope_matches(facts)
            and facts.get("base_reviewed_head") == self.current_review.get("reviewed_head")
            and facts.get("new_head") != facts.get("base_reviewed_head")
            and facts.get("writer_quiescence") == "verified"
            and facts.get("boundary_expansion") == "none"
            and isinstance(facts.get("finding_locators"), list)
            and bool(facts.get("finding_locators"))
            and set(facts.get("finding_locators", [])) == self.pending_fix
        )
        if event["actor"] == "reviewer":
            valid = False
        if self.round_count >= 1:
            valid = False
        if not valid:
            self.violations.add("review_disposition")
            return
        self.round_count += 1
        self.last_write_head = facts["new_head"]
        self.pending_fix = set()
        self.awaiting_fresh_review = True

    def scope_change(self, event: dict[str, Any]) -> None:
        facts = event["facts"]
        if self.current_review is not None:
            prior_findings = set(self.current_review.get("finding_locators", []))
            if not prior_findings.issubset(self.dispositions):
                self.violations.add("review_disposition")
        status = facts.get("status")
        trigger = facts.get("trigger_finding_locator")
        matching_disposition = (
            _real_locator(trigger)
            and self.dispositions.get(trigger, {}).get("disposition") == status
        )
        to_budget = facts.get("to_repair_budget")
        valid = (
            event["actor"] == "owner"
            and event["tool"] in {"git_readback", "gh_readback"}
            and status in self.SCOPE_CHANGES
            and self.current_review is not None
            and matching_disposition
            and not self.awaiting_fresh_review
            and isinstance(facts.get("narrower"), bool)
            and self._required(facts, (
                "from_task_key", "from_scope_revision", "to_task_key", "to_scope_revision",
                "from_convergence_chain_locator", "to_convergence_chain_locator",
                "semantic_change", "evidence_locator", "trigger_finding_locator",
            ))
            and facts.get("from_task_key") == self.task_key
            and facts.get("from_scope_revision") == self.scope_revision
            and facts.get("from_convergence_chain_locator") == self.convergence_chain_locator
            and facts.get("to_convergence_chain_locator") != self.convergence_chain_locator
            and facts.get("semantic_change") in {"product_exit_change", "acceptance_change", "scope_change", "ownership_change"}
            and facts.get("to_task_key") != self.task_key
            and facts.get("to_scope_revision") != self.scope_revision
            and all(_real_locator(facts.get(field)) for field in (
                "from_task_key", "from_scope_revision", "to_task_key", "to_scope_revision",
                "from_convergence_chain_locator", "to_convergence_chain_locator", "evidence_locator",
            ))
            and not _repair_budget_errors(to_budget, facts.get("to_convergence_chain_locator"))
            and to_budget.get("finding_write_consumed") == 0
        )
        if facts.get("status") in {"shrink", "split"} and facts.get("narrower") is not True:
            valid = False
        if facts.get("status") == "reassign" and (
            facts.get("semantic_change") != "ownership_change"
            or facts.get("mismatch_kind") not in {"capability", "ownership"}
            or not _real_locator(facts.get("mismatch_locator"))
        ):
            valid = False
        if not valid:
            self.violations.add("review_disposition")
            return
        self.task_key = facts["to_task_key"]
        self.scope_revision = facts["to_scope_revision"]
        self.convergence_chain_locator = facts["to_convergence_chain_locator"]
        self.round_count = to_budget["finding_write_consumed"]
        self.first_review_seen = False
        self.current_review = None
        self.dispositions = {}
        self.pending_fix = set()
        self.pending_scope_change = set()
        self.awaiting_fresh_review = False
        self.last_write_head = None
        self.last_review_head = None

    def handle(self, event: dict[str, Any]) -> None:
        kind = event["kind"]
        if kind == "fresh_review":
            self.fresh_review(event)
        elif kind == "finding_disposition":
            self.finding_disposition(event)
        elif kind == "review_write":
            self.review_write(event)
        elif kind == "scope_change":
            self.scope_change(event)
        else:
            self.violations.add("review_disposition")

    def finish(self) -> set[str]:
        if not self.first_review_seen or self.awaiting_fresh_review or self.pending_fix or self.pending_scope_change:
            self.violations.add("review_disposition")
        return self.violations


def evaluate(case: dict[str, Any]) -> set[str]:
    if _schema_errors(case):
        return {"schema"}
    if case["mode"] == "review":
        replay = ReviewReplay(case)
        for event in case["events"]:
            replay.handle(event)
        return replay.finish()
    replay = Replay(case)
    for event in case["events"]:
        replay.handle(event)
    return replay.finish()

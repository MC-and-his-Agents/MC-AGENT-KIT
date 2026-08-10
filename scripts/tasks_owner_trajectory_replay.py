"""Replay Tasks Owner lifecycle facts and return violated rule ids."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tasks_owner_trajectory_schema import nonempty as _nonempty, policy_matches as _policy_matches, schema_errors as _schema_errors, valid_iso as _valid_iso, writer_publishable as _writer_publishable

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
            evidence_ok = _nonempty(facts.get("tool_result_locator")) and _nonempty(facts.get("target_readback_locator"))
            if facts.get("route_status") != "armed" or not _nonempty(facts.get("received_at")) or not _nonempty(locator) or not evidence_ok or self._retains_failure(facts):
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
        if not _nonempty(facts.get(time_field)):
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
            if not source_ok or not _nonempty(locator):
                self.violations.add("direct_wake" if self.case["mode"] == "direct" else "cleanup_terminal_consumed")
            else:
                self.completion_locators[key] = locator
            self.direct_completions[key] = value
        elif kind == "completion_consumed":
            locator = facts.get("completion_locator")
            valid_actor = event["actor"] == "owner" and event["tool"] in {"native_completion", "native_status", "codex_app__read_thread"}
            if not valid_actor or not _nonempty(locator) or key not in self.completion_locators or locator != self.completion_locators[key] or facts.get("owner_consumption") != "consumed":
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
        elif kind == "wake_verified" and self.case["source_kind"] == "live_readback" and event["actor"] == "owner" and event["tool"] == "native_completion_wake" and facts.get("native_completion_wake") == "verified" and all(_nonempty(facts.get(field)) for field in ("wake_locator", "host_id", "observed_at", "tool_result_locator")):
            self.verified_wakes.add(key)

    def publication_event(self, event: dict[str, Any]) -> None:
        kind, facts, seq = event["kind"], event["facts"], event["seq"]
        if kind == "head_readback":
            if event["actor"] == "owner" and event["tool"] == "git_readback" and all(_nonempty(facts.get(field)) for field in ("diff_locator", "file_hashes_locator", "exact_head")):
                self.head_readbacks.append({"seq": seq, "head": facts["exact_head"], "diff": facts["diff_locator"]})
            else:
                self.violations.add("writer_quiescence")
            return
        if kind == "fresh_review":
            fields_ok = facts.get("verdict") == "ship" and facts.get("writer_quiescence") == "verified"
            fields_ok = fields_ok and _nonempty(facts.get("reviewed_head")) and _nonempty(facts.get("writer_evidence_locator"))
            fields_ok = fields_ok and event["actor"] == "reviewer" and event["tool"] == "reviewer_result"
            readback = self.head_readbacks[-1] if self.head_readbacks else None
            fields_ok = fields_ok and isinstance(facts.get("reviewed_files"), list) and bool(facts.get("reviewed_files"))
            fields_ok = fields_ok and facts.get("review_write_scope") == "empty" and facts.get("semantic_scope_status") == "aligned"
            fields_ok = fields_ok and bool(readback) and facts.get("diff_locator") == readback["diff"]
            writer_locators = sorted(unit.get("evidence_locator") for unit in self.units.values() if unit.get("is_writer"))
            fields_ok = fields_ok and sorted(facts.get("writer_evidence_locators", [])) == writer_locators
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

    def cleanup_event(self, event: dict[str, Any]) -> None:
        kind, facts, args, seq = event["kind"], event["facts"], event["args"], event["seq"]
        if kind == "closeout":
            if event["actor"] != "owner" or event["tool"] != "gh_readback":
                self.violations.add("cleanup_terminal_consumed")
            merged = all(_nonempty(facts.get(field)) for field in ("merge_commit", "target_head", "issue_state_locator"))
            no_pr = _nonempty(facts.get("no_pr_justification")) and _nonempty(facts.get("no_pr_evidence_locator"))
            if facts.get("closeout_verified") is True and (merged or no_pr):
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
        path_ok = path_ok and Path(cwd) != Path(target) and Path(target) not in Path(cwd).parents
        if not path_ok:
            self.violations.add("cleanup_terminal_consumed")

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
            valid = valid and facts.get("current_interval_seconds") == self.pending_update[1] and _nonempty(facts.get("automation_locator"))
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
            and _nonempty(facts.get("state_digest"))
            and _nonempty(facts.get("user_feedback_revision"))
            and _nonempty(facts.get("external_fact_revision"))
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


def evaluate(case: dict[str, Any]) -> set[str]:
    if _schema_errors(case):
        return {"schema"}
    replay = Replay(case)
    for event in case["events"]:
        replay.handle(event)
    return replay.finish()

"""重放可观察的授权、写入、审查与续接；不执行任务、不实现运行时锁。

recorded_fixture 只证明给定事实的一致性。live_readback 必须另传工具记录并逐事件
绑定；这仍不认证记录的宿主来源，真实证据须由收集者独立核对。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from tasks_owner_trajectory_schema import (
    EVIDENCE_KEY_FIELDS, EXECUTION_KINDS, real_locator, schema_errors, user_decision_errors, writer_publishable,
)

VERIFICATION_SOURCES = {"user", "issue", "repository", "skill_default", "branch_protection", "security_contract", "release_contract"}
PROTECTED_SOURCES = {"branch_protection", "security_contract"}


def _locators(values: Any) -> bool:
    return isinstance(values, list) and all(real_locator(x) for x in values) and len(set(values)) == len(values)


def _overlap(left: list[str], right: list[str]) -> bool:
    return any(a == b or a.startswith(b.rstrip("/") + "/") or b.startswith(a.rstrip("/") + "/") for a in left for b in right)


def _within(carriers: list[str], allowed: list[str]) -> bool:
    return all(any(c == a or c.startswith(a.rstrip("/") + "/") for a in allowed) and ".." not in c.split("/") for c in carriers)


def readback_digest(readback: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(readback, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def evidence_errors(case: dict[str, Any], readback: dict[str, Any] | None) -> list[str]:
    if case["source_kind"] == "recorded_fixture":
        return []
    if not isinstance(readback, dict) or set(readback) != {"host_id", "source_locator", "events"}:
        return ["live_readback needs independently supplied tool records"]
    evidence = case["evidence"]
    if any(readback.get(k) != evidence.get(k) for k in ("host_id", "source_locator")) or readback_digest(readback) != evidence["readback_sha256"]:
        return ["tool readback identity or content digest does not match"]
    if readback["events"] != case["events"]:
        return ["projected event identity, tool, arguments or facts do not match tool readback"]
    return []


def _verification_errors(facts: dict[str, Any], exact_head: Any, evidence_key: dict[str, str], *, require_pr: bool) -> list[str]:
    authority = facts.get("verification_authority")
    if not isinstance(authority, dict) or set(authority) != {"sources", "overrides"}:
        return ["verification needs applicable sources and explicit check overrides"]
    sources, overrides = authority["sources"], authority["overrides"]
    if not isinstance(sources, dict) or set(sources) != VERIFICATION_SOURCES or not isinstance(overrides, list):
        return ["verification sources are incomplete"]
    required: set[tuple[str, str]] = set()
    errors: list[str] = []
    for name, source in sources.items():
        if not isinstance(source, dict) or set(source) != {"locator", "required_checks"} or not _locators(source.get("required_checks")):
            errors.append(f"invalid verification source: {name}")
            continue
        if source["required_checks"] and not real_locator(source["locator"]):
            errors.append(f"required checks have no source: {name}")
        if name != "release_contract" or facts.get("action") == "release":
            required.update((name, check) for check in source["required_checks"])
    removed: set[tuple[str, str]] = set()
    user = sources.get("user")
    user_locator = user.get("locator") if isinstance(user, dict) else None
    for override in overrides:
        if not isinstance(override, dict) or set(override) != {"source", "check", "authority_locator"}:
            errors.append("override must name one source, one check and its user authority")
            continue
        pair = override["source"], override["check"]
        if (
            pair not in required or pair in removed or override["source"] in PROTECTED_SOURCES | {"user"}
            or not real_locator(user_locator) or override["authority_locator"] != user_locator
        ):
            errors.append("unproven, duplicate or protected check override")
        else:
            removed.add(pair)
    results = facts.get("check_results")
    if not isinstance(results, list):
        return errors + ["verification results are missing"]
    by_name: dict[str, dict[str, Any]] = {}
    for result in results:
        if not isinstance(result, dict) or set(result) != {"name", "status", "locator", "head", "evidence_key"} or not real_locator(result.get("name")) or result.get("name") in by_name:
            errors.append("invalid or duplicate check result")
            continue
        if not real_locator(result.get("locator")) or result.get("status") not in {"success", "failed", "pending"}:
            errors.append("check result has no observed status or evidence")
        by_name[result["name"]] = result
    for check in {check for _, check in required - removed}:
        result = by_name.get(check, {})
        if result.get("status") != "success" or result.get("head") != exact_head or result.get("evidence_key") != evidence_key:
            errors.append(f"required check has not passed on current head: {check}")
    for field in ("acceptance_evidence_locator", "product_evidence_locator"):
        if not real_locator(facts.get(field)):
            errors.append(f"publication needs {field}")
    metadata = facts.get("pr_metadata")
    if require_pr or metadata is not None:
        if not isinstance(metadata, dict) or metadata.get("head") != exact_head or not real_locator(metadata.get("locator")):
            errors.append("PR publication needs current PR metadata")
    return errors


class Replay:
    def __init__(self, case: dict[str, Any]) -> None:
        self.initial = case["initial"]
        self.authority = self.initial["authority"]
        self.batches = {
            b["locator"]: {**b, "preflight": None, "review": None, "findings": {},
                           "pending_fixes": set(), "repaired_evidence": {},
                           "rethink_pending": False, "closeout_verified": False}
            for b in self.initial["batches"]
        }
        self.units: dict[str, dict[str, Any]] = {}
        self.gaps = {gap["locator"]: dict(gap) for gap in self.initial["gaps"]}
        self.completions: dict[str, dict[str, Any]] = {}
        self.consumed: dict[str, int] = {}
        self.source_revisions = dict(self.initial.get("source_revisions", {}))
        self.cached = dict(self.initial.get("cached_evidence", {}))
        self.readings: dict[str, dict[str, Any]] = {}
        self.user_decisions: dict[str, dict[str, Any]] = {}
        self.changed_sources: set[str] = set()
        self.final_turn: str | None = None
        self.violations: set[str] = set()

    def batch(self, event: dict[str, Any]) -> dict[str, Any] | None:
        locator = event["facts"].get("batch_locator")
        if locator is None:
            locator = self.units.get(event["unit_id"], {}).get("batch_locator")
        batch = self.batches.get(locator) if real_locator(locator) else None
        if batch is None:
            self.violations.add("planning")
        return batch

    @staticmethod
    def evidence_key(batch: dict[str, Any]) -> dict[str, str]:
        return {key: batch[key] for key in EVIDENCE_KEY_FIELDS}

    @staticmethod
    def invalidate(batch: dict[str, Any]) -> None:
        batch["preflight"] = batch["review"] = None
        batch["closeout_verified"] = False

    def authorized(self, action: str, locator: Any, carriers: Any = None) -> bool:
        return locator == self.authority["locator"] and action in self.authority["actions"] and (
            carriers is None or _locators(carriers) and _within(carriers, self.authority["carriers"])
        )

    def active_writers(self, batch: dict[str, Any] | None = None) -> list[tuple[str, dict[str, Any]]]:
        return [(key, unit) for key, unit in self.units.items()
                if unit["role"] == "writer" and not writer_publishable(unit)
                and (batch is None or unit["batch_locator"] == batch["locator"]
                     or _overlap(unit["carriers"], batch["carriers"]))]

    def review_ready(self, batch: dict[str, Any]) -> bool:
        preflight, review = batch["preflight"], batch["review"]
        key = self.evidence_key(batch)
        return bool(preflight and preflight["head"] == batch["head"] and preflight["evidence_key"] == key
                    and not batch["pending_fixes"] and not batch["rethink_pending"]
                    and (not review and not self.initial["review_required"] or review and review["verdict"] == "ship"
                         and review["head"] == batch["head"] and review["evidence_key"] == key))

    def admission(self, event: dict[str, Any]) -> None:
        facts, key = event["facts"], event["unit_id"]
        carriers, kind, role = facts.get("carriers"), facts.get("execution_kind"), facts.get("role")
        if event["actor"] != "owner" or not real_locator(key) or kind not in EXECUTION_KINDS or role not in {"writer", "reader", "reviewer"} or not _locators(carriers):
            self.violations.add("planning")
            return
        if (facts.get("scope_locator") != self.initial["scope_locator"]
            or facts.get("convergence_chain_locator") != self.initial["convergence_chain_locator"]
            or not self.authorized("write" if role == "writer" else "read", facts.get("authority_locator"), carriers)
            or kind != "local" and not self.authorized("delegate", facts.get("authority_locator"))
            or kind == "local" and key != self.initial["owner_thread_id"]):
            self.violations.add("authorization")
            return
        required, observed = facts.get("required_capabilities"), facts.get("observed_capabilities")
        if not real_locator(facts.get("capability_locator")) or not isinstance(required, dict) or not isinstance(observed, dict) or any(not real_locator(value) or observed.get(name) != value for name, value in required.items()):
            self.violations.add("planning")
            return
        if role == "writer" and (not carriers or any(key == other or _overlap(carriers, unit["carriers"]) for other, unit in self.active_writers())):
            self.violations.add("writer_safety")
            return
        batch = self.batch(event)
        if batch is None:
            return
        if not _within(carriers, batch["carriers"]):
            self.violations.add("authorization")
            return
        # 同一可变 head 载体不能以不同文件路径伪装为独立 writer。
        if role == "writer" and any(unit["batch_locator"] == batch["locator"] for _, unit in self.active_writers()):
            self.violations.add("writer_safety")
            return
        if key in self.units and (event["generation"] < self.units[key]["generation"] or self.units[key]["batch_locator"] != batch["locator"]):
            self.violations.add("event_recovery")
            return
        plan = facts.get("validation_plan")
        if role == "writer" and (not _locators(plan) or not set(self.initial["required_surfaces"]) <= set(plan)):
            self.violations.add("planning")
            return
        selection = facts.get("execution_mode_selection")
        if selection is not None:
            if not isinstance(selection, dict) or set(selection) != {"mode", "independently_admissible_subunits", "write_carrier_overlap", "acceptance_and_rollback_independence", "critical_path_benefit"}:
                self.violations.add("planning")
                return
            if selection["mode"] not in {"direct", "flat", "hierarchical"} or selection["mode"] == "hierarchical" and (
                not _locators(selection["independently_admissible_subunits"]) or len(selection["independently_admissible_subunits"]) < 2
                or selection["write_carrier_overlap"] != "none" or not real_locator(selection["acceptance_and_rollback_independence"])
                or not real_locator(selection["critical_path_benefit"])):
                self.violations.add("planning")
                return
        gap_locator = facts.get("gap_locator")
        if event["kind"] == "successor" or gap_locator is not None:
            gap = self.gaps.get(gap_locator)
            if not gap or gap["status"] != "ready" or any(dep not in self.consumed or self.consumed[dep] != self.completions.get(dep, {}).get("revision") for dep in gap["dependencies"]):
                self.violations.add("event_recovery")
                return
            gap.update(status="active", unit_id=key, batch_locator=batch["locator"])
        previous = self.completions.get(key)
        if previous and (self.consumed.get(key) != previous["revision"] or event["generation"] <= self.units[key]["generation"]):
            self.violations.add("event_recovery")
            return
        self.consumed.pop(key, None)
        self.completions.pop(key, None)
        self.units[key] = {**facts, "generation": event["generation"], "host_status": "running", "write_authority": "active" if role == "writer" else "none"}

    def unit_state(self, event: dict[str, Any]) -> None:
        unit, facts = self.units.get(event["unit_id"]), event["facts"]
        if not unit or event["generation"] != unit["generation"] or not real_locator(facts.get("readback_locator")):
            self.violations.add("writer_safety")
            return
        status = facts.get("host_status")
        if status not in {"running", "terminal", "quiesced"} or facts.get("write_authority") not in {"active", "revoked", "none"}:
            self.violations.add("writer_safety")
            return
        if status != "running" and not writer_publishable(facts) or writer_publishable(unit) and status == "running":
            self.violations.add("writer_safety")
            return
        unit.update(facts)

    def write(self, event: dict[str, Any]) -> None:
        facts, unit = event["facts"], self.units.get(event["unit_id"])
        if not self.authorized("write", facts.get("authority_locator"), facts.get("carriers")) or facts.get("scope_locator") != self.initial["scope_locator"]:
            self.violations.add("authorization")
            return
        if not unit or unit["role"] != "writer" or unit["generation"] != event["generation"] or unit["write_authority"] != "active" or unit["host_status"] != "running" or not _within(facts["carriers"], unit["carriers"]):
            self.violations.add("writer_safety")
            return
        batch = self.batches[unit["batch_locator"]]
        if facts.get("base_head") != batch["head"] or not real_locator(facts.get("new_head")) or facts["new_head"] == batch["head"] or not real_locator(facts.get("tree_digest")):
            self.violations.add("review_integrity")
            return
        fixes = facts.get("finding_locators", [])
        unresolved = batch["review"] and any(f not in batch["findings"] for f in batch["review"]["finding_locators"])
        if not _locators(fixes) or set(fixes) != batch["pending_fixes"] or batch["rethink_pending"] or unresolved:
            self.violations.add("review_integrity")
            return
        for finding in fixes:
            disposition = batch["findings"][finding]
            batch["repaired_evidence"].setdefault(disposition["root_cause_key"], set()).add(disposition["evidence_digest"])
        batch["pending_fixes"].clear()
        batch.update(head=facts["new_head"], tree_digest=facts["tree_digest"])
        self.invalidate(batch)

    def preflight_event(self, event: dict[str, Any]) -> None:
        batch = self.batch(event)
        if batch is None:
            return
        facts = event["facts"]
        checks, surfaces, sibling = facts.get("check_results"), facts.get("covered_surfaces"), facts.get("sibling_scan")
        if self.active_writers(batch) or facts.get("head") != batch["head"]:
            self.violations.add("writer_safety")
            return
        evidence_key = self.evidence_key(batch)
        if facts.get("evidence_key") != evidence_key:
            self.violations.add("review_integrity")
            return
        if not _locators(surfaces) or not set(self.initial["required_surfaces"]) <= set(surfaces) or not isinstance(checks, list) or not checks or any(
            not isinstance(check, dict) or check.get("status") != "success" or check.get("head") != batch["head"] or check.get("evidence_key") != evidence_key or not real_locator(check.get("locator")) for check in checks
        ) or not isinstance(sibling, dict) or sibling.get("status") not in {"ready", "not_applicable"} or not real_locator(sibling.get("locator")):
            self.violations.add("planning")
            return
        batch["preflight"] = facts

    def fresh_review(self, event: dict[str, Any]) -> None:
        batch = self.batch(event)
        if batch is None:
            return
        facts = event["facts"]
        if self.active_writers(batch) or not batch["preflight"] or facts.get("head") != batch["head"] or facts.get("evidence_key") != self.evidence_key(batch) or event["actor"] != "reviewer" or event["unit_id"] in {key for key, unit in self.units.items() if unit["role"] == "writer" and unit["batch_locator"] == batch["locator"]}:
            self.violations.add("review_integrity")
            return
        findings = facts.get("finding_locators")
        if facts.get("verdict") not in {"ship", "fix-first", "rethink", "blocked"} or not _locators(findings) or any(not real_locator(facts.get(key)) for key in ("reviewer_locator", "diff_locator")):
            self.violations.add("review_integrity")
            return
        if batch["review"] and any(key not in batch["findings"] for key in batch["review"]["finding_locators"]):
            self.violations.add("review_integrity")
        if facts["verdict"] == "ship" and (findings or batch["pending_fixes"] or batch["rethink_pending"]):
            self.violations.add("review_integrity")
        if facts["verdict"] == "fix-first" and not findings:
            self.violations.add("review_integrity")
        batch["review"], batch["findings"] = facts, {}
        batch["closeout_verified"] = False

    def finding_disposition(self, event: dict[str, Any]) -> None:
        batch = self.batch(event)
        if batch is None:
            return
        facts, key = event["facts"], event["facts"].get("finding_locator")
        if not batch["review"] or key not in batch["review"]["finding_locators"] or key in batch["findings"]:
            self.violations.add("review_integrity")
            return
        action = facts.get("disposition")
        if action not in {"fix_now", "defer", "reject", "rethink", "user_decision"} or type(facts.get("blocks_current_exit")) is not bool:
            self.violations.add("review_integrity")
            return
        if action in {"defer", "reject"} and facts["blocks_current_exit"]:
            self.violations.add("review_integrity")
        if action == "defer" and not real_locator(facts.get("carrier_locator")) or action == "reject" and not real_locator(facts.get("rejection_basis")):
            self.violations.add("review_integrity")
        if action == "fix_now":
            cause, evidence = facts.get("root_cause_key"), facts.get("evidence_digest")
            if not facts["blocks_current_exit"] or not real_locator(facts.get("acceptance_or_invariant_locator")) or facts.get("boundary_expansion") != "none" or not real_locator(cause) or not real_locator(facts.get("evidence_locator")) or not real_locator(evidence) or evidence in batch["repaired_evidence"].get(cause, set()):
                self.violations.add("review_integrity")
            else:
                batch["pending_fixes"].add(key)
        elif action in {"rethink", "user_decision"}:
            batch["rethink_pending"] = True
            if not real_locator(facts.get("evidence_locator")):
                self.violations.add("review_integrity")
            if action == "user_decision" and user_decision_errors(facts, self.initial.get("decision_boundary_locator")):
                self.violations.add("authorization")
        batch["findings"][key] = {**facts, "observed_seq": event["seq"]}

    def publish(self, event: dict[str, Any]) -> None:
        batch = self.batch(event)
        if batch is None:
            return
        facts = event["facts"]
        if facts.get("action") not in {"merge", "release"} or not self.authorized(facts.get("action"), self.authority["locator"]):
            self.violations.add("authorization")
        if self.active_writers(batch) or facts.get("exact_head") != batch["head"]:
            self.violations.add("writer_safety")
        if not self.review_ready(batch) or facts.get("tree_digest") != batch["tree_digest"] or _verification_errors(facts, batch["head"], self.evidence_key(batch), require_pr=facts.get("action") == "merge"):
            self.violations.add("review_integrity")

    def completion(self, event: dict[str, Any]) -> None:
        facts, key = event["facts"], event["unit_id"]
        unit = self.units.get(key)
        revision = facts.get("revision")
        if event["tool"] in {"final", "commentary", "assistant_summary"}:
            self.violations.add("event_recovery")
            return
        if not unit or type(revision) is not int or revision < 1 or not real_locator(facts.get("event_key")) or not real_locator(facts.get("source_locator")) or facts.get("outcome") not in {"completed", "blocked", "cancelled"} or facts.get("host_status") != "terminal" or not real_locator(facts.get("head")):
            self.violations.add("event_recovery")
            return
        previous = self.completions.get(key)
        if event["generation"] < unit["generation"] or previous and revision < previous["revision"]:
            return
        if previous and revision == previous["revision"]:
            if any(facts[name] != previous[name] for name in ("event_key", "outcome", "head")):
                self.violations.add("event_recovery")
            return
        if event["generation"] != unit["generation"] or facts["head"] != self.batches[unit["batch_locator"]]["head"]:
            self.violations.add("event_recovery")
            return
        self.completions[key] = dict(facts)
        unit.update(host_status="terminal", write_authority="revoked")

    def completion_consumed(self, event: dict[str, Any]) -> None:
        key, facts = event["unit_id"], event["facts"]
        current = self.completions.get(key)
        if not current or event["generation"] != self.units[key]["generation"] or facts.get("revision") != current["revision"] or facts.get("event_key") != current["event_key"] or event["actor"] != "owner":
            self.violations.add("event_recovery")
            return
        if self.consumed.get(key) == current["revision"]:
            return
        self.consumed[key] = current["revision"]
        if current["outcome"] == "completed":
            for gap in self.gaps.values():
                if gap.get("unit_id") == key:
                    gap["status"] = "complete"
                if gap["status"] == "blocked" and gap["dependencies"] and all(dep in self.consumed and self.completions[dep]["outcome"] == "completed" for dep in gap["dependencies"]):
                    gap["status"] = "ready"

    def source_readback(self, event: dict[str, Any]) -> None:
        facts = event["facts"]
        if any(not real_locator(facts.get(k)) for k in ("source", "revision", "evidence_locator")):
            self.violations.add("incremental_progress")
            return
        source, revision = facts["source"], facts["revision"]
        if source in EVIDENCE_KEY_FIELDS | {"head"}:
            batch = self.batch(event)
            if batch is None:
                return
            if batch[source] != revision:
                batch[source] = revision
                self.invalidate(batch)
                self.changed_sources.add(batch["locator"] + ":" + source)
            return
        if self.source_revisions.get(source) != revision:
            self.changed_sources.add(source)
            self.source_revisions[source] = revision

    def read_evidence(self, event: dict[str, Any]) -> None:
        facts = event["facts"]
        if any(not real_locator(facts.get(k)) for k in ("subject", "revision", "source")) or self.source_revisions.get(facts["source"]) != facts["revision"]:
            self.violations.add("incremental_progress")
        elif self.cached.get(facts["subject"]) == facts["revision"]:
            self.violations.add("incremental_progress")
        else:
            self.cached[facts["subject"]] = facts["revision"]
            self.readings[facts["subject"]] = {"revision": facts["revision"], "locator": event["locator"], "observed_seq": event["seq"]}

    def user_decision(self, event: dict[str, Any]) -> None:
        facts = event["facts"]
        if event["actor"] != "user" or event["tool"] != "user_message" or not real_locator(facts.get("decision_locator")) or facts.get("approved") is not True or facts.get("scope_locator") != self.initial["scope_locator"] or not self.authorized(facts.get("action"), facts.get("authority_locator")):
            self.violations.add("authorization")
        else:
            self.user_decisions[facts["decision_locator"]] = {**facts, "observed_seq": event["seq"]}

    def reassessment(self, event: dict[str, Any]) -> None:
        batch = self.batch(event)
        if batch is None:
            return
        facts = event["facts"]
        pending = [f for f in batch["findings"].values() if f["disposition"] in {"rethink", "user_decision"}]
        reading = self.readings.get(facts.get("evidence_subject"), {})
        if not batch["rethink_pending"] or not pending or reading.get("revision") != facts.get("evidence_revision") or reading.get("locator") != facts.get("evidence_locator") or not real_locator(facts.get("evidence_revision")) or any(facts["evidence_revision"] == f.get("evidence_digest") or reading.get("observed_seq", 0) <= f["observed_seq"] for f in pending):
            self.violations.add("review_integrity")
            return
        if facts.get("scope_locator") != self.initial["scope_locator"] or not self.authorized("write", facts.get("authority_locator")):
            self.violations.add("authorization")
            return
        decision = self.user_decisions.get(facts.get("user_decision_locator"), {})
        if any(f["disposition"] == "user_decision" and (decision.get("action") != "write" or decision.get("observed_seq", 0) <= f["observed_seq"]) for f in pending):
            self.violations.add("authorization")
            return
        batch["rethink_pending"] = False
        for finding in pending:
            del batch["findings"][finding["finding_locator"]]

    def recompute_frontier(self, event: dict[str, Any]) -> None:
        sources = event["facts"].get("sources")
        if not _locators(sources) or not sources or not set(sources) <= self.changed_sources:
            self.violations.add("incremental_progress")
        else:
            self.changed_sources.difference_update(sources)

    def closeout(self, event: dict[str, Any]) -> None:
        batch = self.batch(event)
        if batch is None:
            return
        facts = event["facts"]
        merged, local = real_locator(facts.get("merge_locator")), real_locator(facts.get("no_pr_evidence_locator"))
        action = facts.get("action")
        if action not in {"local_delivery", "merge", "release"} or action == "local_delivery" and merged or action == "merge" and not merged or not self.authorized("write" if action == "local_delivery" else action, self.authority["locator"]):
            self.violations.add("authorization")
        # 无 publish 事件、本地无 PR 交付也必须满足同一来源并集。
        if not self.review_ready(batch) or facts.get("tree_digest") != batch["tree_digest"] or _verification_errors(facts, batch["head"], self.evidence_key(batch), require_pr=merged):
            self.violations.add("review_integrity")
            return
        if self.active_writers(batch) or facts.get("exact_head") != batch["head"] or not real_locator(facts.get("issue_state_locator")) or not (merged ^ local):
            self.violations.add("cleanup_safety")
        else:
            batch["closeout_verified"] = True

    def cleanup(self, event: dict[str, Any]) -> None:
        batch = self.batch(event)
        if batch is None:
            return
        facts = event["facts"]
        target = {name: facts.get(name) for name in ("batch_locator", "target_worktree", "target_ref", "target_oid")}
        if not self.authorized("cleanup", facts.get("authority_locator")):
            self.violations.add("authorization")
        if not batch["closeout_verified"] or self.active_writers(batch) or target not in self.initial.get("cleanup_targets", []) or any(not real_locator(value) for value in target.values()) or not real_locator(facts.get("identity_readback_locator")) or facts.get("outcome") not in {"removed", "preserved"}:
            self.violations.add("cleanup_safety")

    def owner_final(self, event: dict[str, Any]) -> None:
        facts, status = event["facts"], event["facts"].get("status")
        self.final_turn = event["turn"]
        if any(self.consumed.get(key) != completion["revision"] for key, completion in self.completions.items()):
            self.violations.add("event_recovery")
        if any(gap["status"] == "ready" or gap["status"] == "blocked" and (not gap["dependencies"] or any(dep not in self.units or self.units[dep]["host_status"] != "running" or not real_locator(self.units[dep].get("monitor_locator")) for dep in gap["dependencies"])) for gap in self.gaps.values()) or self.changed_sources:
            self.violations.add("incremental_progress")
        if status == "completed":
            affected = {unit["batch_locator"] for unit in self.units.values() if unit["role"] == "writer"}
            if self.active_writers() or any(gap["status"] != "complete" for gap in self.gaps.values()) or not affected or any(not self.batches[b]["closeout_verified"] for b in affected) or not real_locator(facts.get("product_acceptance_locator")):
                self.violations.add("incremental_progress")
        elif status == "waiting_task":
            if not self.units or not any(unit["host_status"] == "running" for unit in self.units.values()) or any(not real_locator(unit.get("monitor_locator")) for unit in self.units.values() if unit["host_status"] == "running"):
                self.violations.add("event_recovery")
        elif status in {"waiting_external", "waiting_user", "progressed"}:
            if self.active_writers():
                self.violations.add("event_recovery")
            for gap in self.gaps.values():
                if gap["status"] not in {"complete", "waiting_external", "waiting_user"} or gap["status"] != "complete" and any(not real_locator(gap.get(k)) for k in ("evidence_locator", "wake_condition")):
                    self.violations.add("incremental_progress")
                if gap["status"] == "waiting_user" and user_decision_errors(gap.get("decision"), self.initial.get("decision_boundary_locator")):
                    self.violations.add("authorization")
        elif status != "rethink" or not any(b["rethink_pending"] for b in self.batches.values()):
            self.violations.add("incremental_progress")

    def handle(self, event: dict[str, Any]) -> None:
        kind = event["kind"]
        if kind in {"admission", "successor", "completion_consumed", "publish", "cleanup", "closeout", "owner_final", "finding_disposition", "reassessment"} and event["actor"] != "owner":
            self.violations.add("authorization")
            return
        if self.final_turn == event["turn"]:
            self.violations.add("incremental_progress")
        else:
            self.final_turn = None
        method = {"successor": self.admission, "preflight": self.preflight_event}.get(kind)
        (method or getattr(self, kind))(event)

    def finish(self) -> set[str]:
        if any(batch["pending_fixes"] for batch in self.batches.values()) and self.final_turn is None:
            self.violations.add("review_integrity")
        return self.violations


def evaluate(case: dict[str, Any], readback: dict[str, Any] | None = None) -> set[str]:
    if schema_errors(case):
        return {"schema"}
    if evidence_errors(case, readback):
        return {"evidence_binding"}
    replay = Replay(case)
    for event in case["events"]:
        replay.handle(event)
    return replay.finish()

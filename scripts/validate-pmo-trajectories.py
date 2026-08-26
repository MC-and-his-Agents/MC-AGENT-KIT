#!/usr/bin/env python3
"""Validate PMO trajectories from structured facts and cross-field invariants.

The evaluator deliberately ignores case ids, expected prose, and ``must`` /
``must_not`` text.  A verdict is derived from the facts, then compared with the
declared result so a copied answer cannot make a trajectory pass.
"""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "skills/dev/pmo/evals/trajectory_cases.jsonl"
SCHEMA_VERSION = "pmo-trajectory.v1"
ROOT_KEYS = {"schema_version", "id", "facts", "expected"}
EXPECTED_KEYS = {"verdict", "must", "must_not"}
VERDICTS = {
    "KEEP_CURRENT",
    "ROUTE_INFO",
    "SHAPE_WORK_ITEMS",
    "CREATE_OR_WAKE_OWNER",
    "CORRECT_DRIFT",
    "ESCALATE_USER",
    "CLOSEOUT_AND_RECOMPUTE",
}
INCIDENT_FAMILIES = {
    "desktop-asar-pnpm",
    "release-acceptance-gating",
    "activity-without-product-progress",
    "heartbeat-recovery",
    "human-communication",
    "autonomous-closeout",
}
MATRIX_PATHS = {"advance", "wait", "defer", "escalate"}
PROOF_FIELDS = (
    "subject",
    "generation",
    "target_head",
    "revision",
    "evidence_digest",
    "responsible_party",
    "next_actor",
    "next_action",
    "wake_condition",
    "invalidation",
    "observed_at",
    "expires_at",
    "sentinel_source",
    "sentinel_due_at",
)
AUDIT_PATHS = {"Fast", "Affected-slice", "Deep Audit"}
FULL_AUDIT_MARKERS = {"full_dag", "full_handoff", "all_owner_runtime", "repository_wide"}
FAST_CHANGE_VECTOR_FIELDS = frozenset(
    {
        "new_events",
        "source_revision_changed",
        "generation_changed",
        "pending_receipts",
        "due_sentinel",
        "semantic_delta",
        "truth_invalidated",
        "runtime_invalidated",
        "skill_invalidated",
        "evidence_expired",
        "cursor_gap",
    }
)
FAST_ACTIONS = {"cursor_check", "cache_reuse", "cas_read", "proof_reuse", "dedupe_event"}
LOCATOR_SENTINELS = {"", "none", "null", "missing", "unknown", "n/a", "na", "tbd"}
AUTHORITY_REQUIRED = {
    "contract_locator",
    "digest",
    "revision",
    "user_source_locator",
    "repo_locator",
    "target_ref",
    "permission_scope",
    "freshness",
    "observed_at",
    "expiry",
    "invalidation",
}
AUTHORITY_PERMISSION_KEYS = {
    "planning_write",
    "dependency_relation_write",
    "owner_create_recover",
    "finding_adjudication",
    "merge_closeout",
    "automation",
}
AUTHORITY_REPO_LOCATOR = "github:MC-and-his-Agents/MC-AGENT-KIT"
MACHINE_FIELDS = {
    "event_key",
    "semantic_revision",
    "execution_generation",
    "receipt",
    "generation",
    "digest",
    "checkpoint",
    "runtime",
    "tool",
    "prompt",
}
TASKS_OWNER_CAPABILITIES = {
    "pmo_admission",
    "owner_sparse_delta",
    "single_scope_owner_execution",
    "bounded_finding_fix",
    "delivery_closeout",
}
TASKS_OWNER_DEPENDENCY_FIELDS = {
    "status",
    "execution_required",
    "mode",
    "user_decision",
    "install_attempted",
    "install_source",
    "install_target",
    "prompt_count",
    "prior_user_decision",
    "compatibility_evidence",
    "observed_version",
    "capabilities",
    "rechecked_after_install",
}
TASKS_OWNER_INSTALL_SOURCE = "github:MC-and-his-Agents/MC-AGENT-KIT@main:skills/dev/tasks-owner"
TASKS_OWNER_INSTALL_TARGET = "codex-skill-home:tasks-owner"
KNOWN_FACT_KEYS = frozenset(
    """
    active_owner_count admission_pending affected_scope aggregation_state audit_actions audit_path
    authority authorization authorized_repo authorized_scope authority_contract authority_contract_summary candidate_safe_slice canonical_fact
    canonical_fact_id capability_domain capability_status capacity chain change_entity change_vector
    checkpoint_cas checkpoint_identity ci clean_vm clean_vm_verification closed_children closure
    closure_status consumed_at consumer_owner consumer_scope_owns_upstream_seam critical_path_stable_cycles
    critical_path_width current_fix current_generation current_path_evidence current_semantic_revision
    current_skill_digest current_unit current_wave_work_items cursor_advanced cycle decision decision_owner
    deep_reason default_consequence deferred_carrier deferred_detail delivery_attempt delivery_attempts
    delivery_result delivery_unit delivery_unit_complete dependency_relation_writes dependency_repo
    desired_runtime discovered_risk dmg_build downstream_first_slice early_return enabling_progress
    engineering_activity event event_key events evidence evidence_cache evidence_template exact_main
    exact_smoke_steps execution_generation existing_core expected_title external_gate fixtures_allow_safe_start
    fr_acceptance github_issue_state goal handoff_claims_unit_ready heartbeat heartbeat_status host_owner_state
    human_default human_projection human_summary impact implementation_admitted_inflight incident_family
    incident_improvement independent_acceptance_and_rollback internal_contract internal_successor invalidation
    machine_projection main_head matrix_path mature_standard_or_oss merge_gate merged_prs mode_requested
    native_blocked_by new_closure_digest new_truth_digest newer_checkpoint next_actor next_audit_path
    next_change_vector next_unlock_facts next_unlock_readiness non_blocking_hardening non_blocking_work
    notification observed_at observed_runtime observed_title occurred_at orchestrator_runtime owner
    owner_a_desired owner_a_event_receipt owner_a_observed owner_a_runtime owner_b_event owner_b_runtime
    owner_events owner_status parent_acceptance parent_user_outcome payload_event_key pending_owner_events
    pinned planning_writes post_gates pre_increment presentation_capability previous_skill_digest
    prior_semantic_revision product_effect product_goal product_outcome product_progress projection_sources
    protocol_fields real_provider_evidence received_at recovery_evidence remaining_executable_surface repo_short_name
    remaining_gaps remaining_surface repair replay_generation repo_b_owner_requested reproduced_failure
    requested_change retry_same_event_key review risk runtime_recovery safe_path security_risk semantic_revision semantic_revisions
    sentinel_query shared_carrier shared_carriers shared_product_effect shortest_product_validation
    skill_locator skill_status source_cursor source_locator stale_handoff_claims_ready_unit target_head receipt finding
    tasks_owner_dependency technical_sources terminal_reason theoretical_pnpm_edge title trigger truth_status unaffected_scope
    uncommitted_work urgent_risk user_approval user_challenge user_requested_detail verified_at waiting_proof
    wake_condition width_health writer_started writers_needed
    """.split()
)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def real_locator(value: Any) -> bool:
    return nonempty(value) and value.strip().lower() not in LOCATOR_SENTINELS


def normalized_identity(value: Any) -> str:
    return value.strip().rstrip("/").casefold() if nonempty(value) else ""


def real_evidence(value: Any) -> bool:
    if isinstance(value, dict):
        return any(real_evidence(item) for item in value.values())
    if isinstance(value, list):
        return bool(value) and all(real_evidence(item) for item in value)
    return real_locator(value)


def contains_cjk(value: Any) -> bool:
    return isinstance(value, str) and any("\u4e00" <= char <= "\u9fff" for char in value)


def is_iso(value: Any) -> bool:
    if not nonempty(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value in {"future", "fresh", "valid", "current", "past", "expired", "due", "stale"}
    return True


def freshness(value: Any) -> str:
    if value in {"past", "expired", "due", "stale"}:
        return "expired"
    if value in {"future", "fresh", "valid", "current"}:
        return "fresh"
    if not nonempty(value):
        return "unknown"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    now = datetime.now(parsed.tzinfo)
    return "fresh" if parsed > now else "expired"


def scalar_or_list_nonempty(value: Any) -> bool:
    if nonempty(value):
        return True
    return isinstance(value, list) and bool(value) and all(nonempty(item) for item in value)


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: case must be an object")
        value["_line"] = line_number
        cases.append(value)
    return cases


def _decision_fields(facts: dict[str, Any]) -> bool:
    decision = facts.get("decision")
    if isinstance(decision, dict):
        if not isinstance(decision.get("options"), list) or len(decision["options"]) < 2:
            return False
        return all(nonempty(decision.get(key)) for key in ("recommendation", "impact", "default_consequence"))
    return (
        facts.get("decision_owner") == "user"
        and any(nonempty(facts.get(key)) for key in ("requested_change", "risk", "discovered_risk"))
        and all(nonempty(facts.get(key)) for key in ("impact", "default_consequence"))
    )


def _surface_open(facts: dict[str, Any]) -> bool:
    for key in ("remaining_executable_surface", "safe_path", "internal_successor"):
        value = facts.get(key)
        if value not in (None, False, 0, "", "none", "zero", "无", [], {}):
            return True
    for key in ("remaining_executable_surface",):
        nested = facts.get(key)
        if isinstance(nested, dict) and nested.get("status") not in {None, "none", "zero", "empty"}:
            return True
    return False


def waiting_proof_errors(proof: Any, *, require_fresh: bool = True) -> list[str]:
    if not isinstance(proof, dict):
        return ["waiting_proof must be an object"]
    errors = [f"waiting_proof missing {field}" for field in PROOF_FIELDS if field not in proof]
    for field in PROOF_FIELDS:
        if field not in proof:
            continue
        value = proof[field]
        if field in {"invalidation"}:
            if not scalar_or_list_nonempty(value):
                errors.append(f"waiting_proof {field} must be non-empty")
        elif field in {"generation", "revision"}:
            if not isinstance(value, (int, str)) or isinstance(value, bool) or (isinstance(value, str) and not value.strip()):
                errors.append(f"waiting_proof {field} must identify a revision")
        elif field == "observed_at":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (AttributeError, TypeError, ValueError):
                errors.append("waiting_proof observed_at must be an ISO-8601 timestamp")
        elif field.endswith("_at"):
            if not is_iso(value):
                errors.append(f"waiting_proof {field} must be an observation or validity timestamp")
        elif not nonempty(value):
            errors.append(f"waiting_proof {field} must be non-empty")
    if require_fresh and freshness(proof.get("expires_at")) != "fresh":
        errors.append("waiting_proof expires_at is not fresh")
    if require_fresh and freshness(proof.get("sentinel_due_at")) == "expired":
        errors.append("waiting_proof sentinel_due_at is already due")
    return errors


def _incident_improvement_errors(facts: dict[str, Any]) -> list[str]:
    improvement = facts.get("incident_improvement")
    if not isinstance(improvement, dict):
        return ["incident cases require incident_improvement"]
    required = {"status", "trigger_source", "occurrence_count", "stable_locator", "real_impact", "reporting"}
    errors = [f"incident_improvement missing {key}" for key in sorted(required - set(improvement))]
    status = improvement.get("status")
    trigger = improvement.get("trigger_source")
    count = improvement.get("occurrence_count")
    if status not in {"bounded_revision", "not_triggered"}:
        errors.append("incident_improvement status is invalid")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        errors.append("incident_improvement occurrence_count must be positive")
    if not real_locator(improvement.get("stable_locator")) or not real_locator(improvement.get("real_impact")):
        errors.append("incident_improvement needs a stable locator and real impact")
    if improvement.get("reporting") != "none":
        errors.append("incident improvement must not create a report")
    if status == "bounded_revision":
        required_bounded = ("root_cause_revision", "behavior_trajectory", "independent_verification")
        if trigger != "repeat_incident" or not isinstance(count, int) or count < 2:
            errors.append("bounded incident improvement requires repeated incidents")
        for key in required_bounded:
            if not real_locator(improvement.get(key)):
                errors.append(f"bounded incident improvement missing {key}")
        if improvement.get("heartbeat_triggered") is not False:
            errors.append("bounded incident improvement requires heartbeat_triggered=false")
    elif status == "not_triggered":
        if trigger not in {"single_incident", "heartbeat", "ordinary_event"} or count != 1:
            errors.append("not-triggered incident improvement must remain single and low-frequency")
        for key in ("root_cause_revision", "behavior_trajectory", "independent_verification"):
            if improvement.get(key) not in {None, "none"}:
                errors.append(f"not-triggered incident improvement must not fill {key}")
    return errors


def _tasks_owner_dependency_errors(facts: dict[str, Any]) -> list[str]:
    dependency = facts.get("tasks_owner_dependency")
    if dependency is None:
        return []
    if not isinstance(dependency, dict):
        return ["tasks_owner_dependency must be an object"]
    errors: list[str] = []
    missing = sorted(TASKS_OWNER_DEPENDENCY_FIELDS - set(dependency))
    extra = sorted(set(dependency) - TASKS_OWNER_DEPENDENCY_FIELDS)
    if missing or extra:
        errors.append(f"tasks_owner_dependency fields mismatch (missing={missing}, extra={extra})")
        return errors

    status = dependency.get("status")
    mode = dependency.get("mode")
    decision = dependency.get("user_decision")
    prior_decision = dependency.get("prior_user_decision")
    execution_required = dependency.get("execution_required")
    attempted = dependency.get("install_attempted")
    prompt_count = dependency.get("prompt_count")
    capabilities = dependency.get("capabilities")
    rechecked = dependency.get("rechecked_after_install")

    if status not in {"compatible", "missing", "incompatible"}:
        errors.append("tasks_owner_dependency status is invalid")
    if mode not in {"full", "analysis_only", "install_pending"}:
        errors.append("tasks_owner_dependency mode is invalid")
    if decision not in {"not_needed", "not_asked", "pending", "accepted", "declined"}:
        errors.append("tasks_owner_dependency user_decision is invalid")
    if prior_decision not in {"none", "accepted", "declined"}:
        errors.append("tasks_owner_dependency prior_user_decision is invalid")
    if not isinstance(execution_required, bool) or not isinstance(attempted, bool) or not isinstance(rechecked, bool):
        errors.append("tasks_owner_dependency boolean fields are invalid")
    if not isinstance(prompt_count, int) or isinstance(prompt_count, bool) or prompt_count not in {0, 1}:
        errors.append("tasks_owner_dependency prompt_count must be zero or one")
    if not isinstance(capabilities, list) or not all(nonempty(item) for item in capabilities):
        errors.append("tasks_owner_dependency capabilities must be a string array")
        capabilities = []
    if not real_locator(dependency.get("compatibility_evidence")):
        errors.append("tasks_owner_dependency needs compatibility evidence")

    if decision in {"pending", "accepted", "declined"}:
        if dependency.get("install_source") != TASKS_OWNER_INSTALL_SOURCE:
            errors.append("tasks_owner_dependency install source must be the verified PMO release source")
        if dependency.get("install_target") != TASKS_OWNER_INSTALL_TARGET:
            errors.append("tasks_owner_dependency install target must be the tasks-owner Skill directory")
    elif dependency.get("install_source") != "none" or dependency.get("install_target") != "none":
        errors.append("tasks_owner_dependency must not invent an install prompt")
    if attempted and decision != "accepted":
        errors.append("tasks_owner_dependency install requires explicit user consent")
    if execution_required is False:
        if attempted or prompt_count != 0 or decision not in {"not_needed", "not_asked"}:
            errors.append("analysis-only work must not ask for or install tasks-owner")
    elif decision == "pending" and (prior_decision != "none" or prompt_count != 1):
        errors.append("tasks_owner_dependency first install question must occur once")
    elif decision == "accepted" and (prior_decision != "accepted" or prompt_count != 0):
        errors.append("accepted tasks-owner install must reuse prior consent without prompting again")
    elif decision == "declined" and (prior_decision != "declined" or prompt_count != 0):
        errors.append("declined tasks-owner install must not prompt again")
    elif decision in {"not_needed", "not_asked"} and (prior_decision != "none" or prompt_count != 0):
        errors.append("tasks_owner_dependency must not invent prior consent")

    has_capabilities = TASKS_OWNER_CAPABILITIES <= set(capabilities)
    if status == "compatible":
        if mode != "full" or not has_capabilities:
            errors.append("compatible tasks-owner must enable full mode with required capabilities")
        if decision == "accepted" and (not attempted or not rechecked):
            errors.append("accepted tasks-owner installation must be attempted and rechecked")
        if decision not in {"not_needed", "accepted"}:
            errors.append("compatible tasks-owner has an invalid user decision")
    else:
        if mode == "full" or has_capabilities:
            errors.append("missing or incompatible tasks-owner cannot enable full mode")
        if not execution_required:
            if mode != "analysis_only" or decision != "not_asked":
                errors.append("analysis-only work must not ask to install tasks-owner")
        elif decision == "pending" and (mode != "install_pending" or attempted):
            errors.append("pending tasks-owner install must wait for consent")
        elif decision == "declined" and (mode != "analysis_only" or attempted):
            errors.append("declined tasks-owner install must remain analysis-only")
        elif decision == "accepted" and mode != "install_pending":
            errors.append("unverified tasks-owner install cannot leave pending mode")
        elif decision not in {"pending", "declined", "accepted"}:
            errors.append("execution work without tasks-owner must ask once or remain declined")
    return errors


def _audit_errors(facts: dict[str, Any]) -> list[str]:
    change_vector = facts.get("change_vector")
    if not isinstance(change_vector, dict):
        return []
    path = facts.get("audit_path")
    if path not in AUDIT_PATHS:
        return ["change_vector cases require audit_path"]
    actions = facts.get("audit_actions", [])
    if not isinstance(actions, list) or not actions or not all(nonempty(item) for item in actions):
        return ["audit_actions must be a non-empty list of action names"]
    errors: list[str] = []
    if path == "Fast":
        if set(change_vector) != FAST_CHANGE_VECTOR_FIELDS:
            missing = sorted(FAST_CHANGE_VECTOR_FIELDS - set(change_vector))
            extra = sorted(set(change_vector) - FAST_CHANGE_VECTOR_FIELDS)
            errors.append(f"Fast change_vector must be complete (missing={missing}, extra={extra})")
        if any(item not in FAST_ACTIONS for item in actions):
            errors.append("Fast audit_actions must stay within the light-action allowlist")
        cache = facts.get("evidence_cache")
        cache_fresh = cache == "fresh" or (isinstance(cache, dict) and cache.get("status") == "fresh")
        if not cache_fresh:
            errors.append("Fast requires a fresh evidence cache")
        if facts.get("checkpoint_identity") != "verified":
            errors.append("Fast requires a verified checkpoint identity")
    empty = all(value in (False, 0, None, "", "none") for value in change_vector.values())
    if empty:
        if path != "Fast":
            errors.append("empty change vector must select Fast")
        if facts.get("early_return") is not True:
            errors.append("Fast must return before full audit")
        if any(item in FULL_AUDIT_MARKERS or any(marker in item for marker in ("full", "all_owner", "repository")) for item in actions):
            errors.append("Fast cannot enter a full audit loop")
    elif change_vector.get("closure_status") in {"unknown", "incomplete"} or facts.get("deep_reason") or facts.get("checkpoint_cas") == "conflict":
        if path != "Deep Audit":
            errors.append("unknown closure or CAS conflict must select Deep Audit")
        if not any(item in {"replay_cursor", "recover_truth", "rebuild_closure"} for item in actions):
            errors.append("Deep Audit must recover the affected truth")
    else:
        if path != "Affected-slice":
            errors.append("finite change vector must select Affected-slice")
        if "full_dag" in actions or "full_handoff" in actions:
            errors.append("Affected-slice cannot run a full audit")
        closure = facts.get("closure")
        if closure is not None:
            if not isinstance(closure, list) or not closure:
                errors.append("Affected-slice closure must be a non-empty list")
            elif facts.get("change_entity") and facts.get("change_entity") not in closure:
                errors.append("Affected-slice closure must include the changed entity")
            elif any(item in {"whole-repository", "repository-wide", "all-owners"} for item in closure):
                errors.append("Affected-slice closure cannot expand to the whole repository")
    if facts.get("next_audit_path") is not None and facts.get("next_audit_path") not in AUDIT_PATHS:
        errors.append("next_audit_path is invalid")
    return errors


def _width_errors(facts: dict[str, Any]) -> list[str]:
    if facts.get("critical_path_width") != 1:
        return []
    health = facts.get("width_health")
    if not isinstance(health, dict):
        return ["width=1 requires width_health evidence"]
    required = {"product_progress", "enabling_progress", "parallel_proof", "audit_decision", "audit_count"}
    errors = [f"width_health missing {key}" for key in sorted(required - set(health))]
    if not isinstance(health.get("audit_count"), int) or isinstance(health.get("audit_count"), bool) or health.get("audit_count") < 0:
        errors.append("width_health audit_count must be non-negative")
    if health.get("parallel_proof") == "fresh" and health.get("audit_count", 0) > 0:
        errors.append("fresh width=1 proof must be reused, not repeatedly audited")
    if health.get("audit_decision") == "audit" and not (
        health.get("product_progress") == "none"
        and health.get("enabling_progress") == "none"
        or health.get("parallel_proof") in {"invalidated", "new-fact", "ttl-expired", "sentinel-expired"}
    ):
        errors.append("width=1 audit requires no progress or invalidated parallel proof")
    return errors


def _authority_contract_errors(facts: dict[str, Any]) -> list[str]:
    contract = facts.get("authority_contract")
    if contract is None:
        return []
    if not isinstance(contract, dict):
        return ["authority_contract must be an object"]
    errors = [f"authority_contract missing {key}" for key in sorted(AUTHORITY_REQUIRED - set(contract))]
    for key in ("contract_locator", "digest", "user_source_locator", "repo_locator", "target_ref", "invalidation"):
        if key in contract and not real_locator(contract.get(key)):
            errors.append(f"authority_contract {key} must be a real locator or statement")
    revision = contract.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        errors.append("authority_contract revision must be positive")
    if contract.get("repo_locator") and normalized_identity(contract["repo_locator"]) != normalized_identity(AUTHORITY_REPO_LOCATOR):
        errors.append("authority_contract repo_locator crosses repository boundary")
    target = contract.get("target_ref")
    target_ref, separator, target_head = target.partition("@") if nonempty(target) else ("", "", "")
    if target and (target_ref not in {"origin/main", "main"} or separator != "@" or not real_locator(target_head)):
        errors.append("authority_contract target_ref must identify this repository main target")
    if contract.get("user_source_locator") and not (
        contract["user_source_locator"].startswith("github:") or contract["user_source_locator"].startswith("issue:")
    ):
        errors.append("authority_contract user_source_locator must identify the user source")
    scope = contract.get("permission_scope")
    if not isinstance(scope, dict):
        errors.append("authority_contract permission_scope must be an object")
    else:
        missing = sorted(AUTHORITY_PERMISSION_KEYS - set(scope))
        if missing:
            errors.append(f"authority_contract permission_scope missing {missing}")
        if any(not real_locator(value) for value in scope.values()):
            errors.append("authority_contract permission_scope entries must be explicit")
    if contract.get("freshness") != "fresh":
        errors.append("authority_contract freshness must be fresh")
    if not is_iso(contract.get("observed_at")):
        errors.append("authority_contract observed_at must be ISO-8601")
    if freshness(contract.get("expiry")) != "fresh":
        errors.append("authority_contract expiry is not fresh")
    summary = facts.get("authority_contract_summary")
    if not isinstance(summary, dict):
        errors.append("authority_contract summary is missing")
    else:
        for key in ("contract_locator", "digest", "revision"):
            if summary.get(key) != contract.get(key):
                errors.append(f"authority_contract summary conflicts on {key}")
    return errors


def _require_incident_fields(facts: dict[str, Any], keys: tuple[str, ...], errors: list[str]) -> None:
    for key in keys:
        if not real_evidence(facts.get(key)):
            errors.append(f"incident {facts.get('incident_family')}/{facts.get('matrix_path')} missing fact {key}")


def _incident_fact_errors(facts: dict[str, Any]) -> list[str]:
    family = facts.get("incident_family")
    path = facts.get("matrix_path")
    if family not in INCIDENT_FAMILIES or path not in MATRIX_PATHS:
        return []
    errors: list[str] = []
    _require_incident_fields(facts, ("product_goal",), errors)
    if path == "advance":
        if family == "desktop-asar-pnpm":
            _require_incident_fields(facts, ("reproduced_failure", "current_fix", "evidence"), errors)
            if facts.get("dmg_build") != "ready" or facts.get("clean_vm") != "ready" or not real_evidence(facts.get("authority")):
                errors.append("Desktop closeout requires ready DMG, Clean VM and authority facts")
        elif family == "release-acceptance-gating":
            pre = facts.get("pre_increment")
            if not isinstance(pre, dict) or pre.get("safe_to_start") is not True or not real_evidence(pre.get("contract")):
                errors.append("release advance requires a safe, contracted pre-increment")
            if facts.get("shared_carrier") != "available" or facts.get("authority") != "authorized":
                errors.append("release advance requires shared carrier and authority")
        elif family == "activity-without-product-progress":
            if not isinstance(facts.get("engineering_activity"), dict) or not real_evidence(facts.get("shortest_product_validation")):
                errors.append("activity advance requires observed activity and shortest product validation")
        elif family == "heartbeat-recovery":
            if not isinstance(facts.get("change_vector"), dict) or not real_evidence(facts.get("affected_scope")) or not real_evidence(facts.get("recovery_evidence")):
                errors.append("Heartbeat advance requires changed scope and recovery evidence")
        elif family == "human-communication":
            canonical = facts.get("canonical_fact")
            if not isinstance(canonical, dict) or not real_locator(canonical.get("event_key")) or not real_locator(canonical.get("evidence_locator")):
                errors.append("human advance requires canonical event and evidence")
            if facts.get("human_projection") != "required" or not real_evidence(facts.get("human_summary")):
                errors.append("human advance requires a product summary projection")
        elif family == "autonomous-closeout":
            _require_incident_fields(facts, ("review", "target_head", "evidence"), errors)
            if facts.get("authorization") != "confirmed" or facts.get("ci") != "passed" or facts.get("merge_gate") != "satisfied":
                errors.append("autonomous closeout requires authorization, CI and merge gate facts")
    elif path == "wait":
        if family == "desktop-asar-pnpm":
            if not real_evidence(facts.get("current_path_evidence")) or not isinstance(facts.get("clean_vm_verification"), dict) or facts.get("dmg_build") != "ready":
                errors.append("Desktop wait requires current-path and Clean VM evidence")
        elif family == "release-acceptance-gating":
            pre = facts.get("pre_increment")
            if not isinstance(pre, dict) or pre.get("safe_to_start") is not False or not real_evidence(pre.get("evidence")):
                errors.append("release wait requires a blocked pre-increment with evidence")
        elif family == "activity-without-product-progress":
            if not isinstance(facts.get("engineering_activity"), dict) or not isinstance(facts.get("external_gate"), dict) or facts.get("internal_successor") != "none":
                errors.append("activity wait requires external gate and no internal successor")
        elif family == "heartbeat-recovery":
            if not isinstance(facts.get("change_vector"), dict) or facts.get("safe_path") != "none":
                errors.append("Heartbeat wait requires an empty change vector and no safe path")
        elif family == "human-communication":
            if not isinstance(facts.get("canonical_fact"), dict) or facts.get("human_projection") != "not_required" or facts.get("notification") != "none":
                errors.append("human wait requires canonical fact and silent notification")
        elif family == "autonomous-closeout":
            _require_incident_fields(facts, ("review", "target_head"), errors)
            if facts.get("ci") != "failed" or facts.get("merge_gate") != "blocked":
                errors.append("autonomous wait requires failed CI and blocked merge gate")
    elif path == "defer":
        if family == "desktop-asar-pnpm" and not real_evidence(facts.get("deferred_carrier")):
            errors.append("Desktop defer requires a deferred carrier")
        elif family == "release-acceptance-gating":
            pre = facts.get("pre_increment")
            if not isinstance(pre, dict) or pre.get("safe_to_start") is not True or not real_evidence(facts.get("deferred_carrier")):
                errors.append("release defer requires a safe pre-increment and carrier")
        elif family == "activity-without-product-progress":
            if not isinstance(facts.get("engineering_activity"), dict) or not real_evidence(facts.get("deferred_carrier")):
                errors.append("activity defer requires observed activity and carrier")
        elif family == "heartbeat-recovery":
            vector = facts.get("change_vector")
            if not isinstance(vector, dict) or facts.get("receipt") != "already-consumed" or vector.get("retry") is not True or vector.get("semantic_delta") is not False:
                errors.append("Heartbeat defer requires consumed receipt and a no-delta retry")
        elif family == "human-communication":
            if not isinstance(facts.get("canonical_fact"), dict) or facts.get("human_projection") != "machine-only" or not real_evidence(facts.get("deferred_detail")):
                errors.append("human defer requires canonical machine-only detail")
        elif family == "autonomous-closeout":
            if not isinstance(facts.get("finding"), dict) or not real_evidence(facts.get("review")) or not real_evidence(facts.get("target_head")):
                errors.append("autonomous defer requires review, target and finding facts")
    elif path == "escalate":
        if not _decision_fields(facts):
            errors.append("incident escalation requires a structured user decision")
        if family == "human-communication" and (not isinstance(facts.get("canonical_fact"), dict) or facts.get("human_projection") != "immediate"):
            errors.append("human escalation requires canonical immediate projection")
        if family == "autonomous-closeout" and not all(real_evidence(facts.get(key)) for key in ("review", "target_head")):
            errors.append("autonomous escalation requires review and target facts")
        if family == "heartbeat-recovery" and (not isinstance(facts.get("change_vector"), dict) or not real_evidence(facts.get("affected_scope"))):
            errors.append("Heartbeat escalation requires affected scope and change vector")
    return errors


def _projection_errors(facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    canonical = facts.get("canonical_fact")
    if canonical is not None:
        if not isinstance(canonical, dict):
            errors.append("canonical_fact must be an object")
        elif not nonempty(canonical.get("event_key")) or not nonempty(canonical.get("evidence_locator")):
            errors.append("canonical_fact needs event_key and evidence_locator")
    if "projection_sources" in facts:
        sources = facts.get("projection_sources")
        source = facts.get("source_locator")
        if not isinstance(sources, list) or not sources or not all(nonempty(item) for item in sources):
            errors.append("projection_sources must be non-empty locators")
        elif source and sources != [source]:
            errors.append("human and machine projections must share one source locator")
    human_projection = facts.get("human_projection")
    if human_projection in {"machine-only", "not_required"} and facts.get("human_summary"):
        errors.append("silent or machine-only facts must not create a placeholder human summary")
    if human_projection in {"required", "present", "immediate"}:
        summary = facts.get("human_summary") or facts.get("human_default")
        if not nonempty(summary) or not contains_cjk(summary):
            errors.append("human projection requires a plain Chinese summary")
        elif any(field in summary for field in MACHINE_FIELDS):
            errors.append("default human projection leaks machine payload")
        if "canonical_fact_id" in facts and not real_locator(facts.get("canonical_fact_id")):
            errors.append("canonical_fact_id must be a real locator")
        canonical_identity = real_locator(facts.get("canonical_fact_id")) or (
            isinstance(canonical, dict) and real_locator(canonical.get("event_key"))
        )
        canonical_evidence = canonical.get("evidence_locator") if isinstance(canonical, dict) else None
        source = facts.get("source_locator") or canonical_evidence
        effect = facts.get("product_effect") or (canonical.get("product_effect") if isinstance(canonical, dict) else None)
        if not canonical_identity or not real_locator(source):
            errors.append("human projection must attach to a canonical event/fact and evidence locator")
        if not real_evidence(effect) or str(effect).strip().lower() in {"unchanged", "no_change", "none"}:
            errors.append("human projection requires a product semantic change")
    if human_projection == "same canonical source" and not isinstance(canonical, dict):
        errors.append("machine projection must point to the canonical fact")
    if facts.get("human_default"):
        if not contains_cjk(facts["human_default"]):
            errors.append("human_default must use plain Chinese")
        if human_projection not in {"required", "present", "immediate"}:
            errors.append("human_default must be attached to a canonical human projection")
    if facts.get("user_requested_detail") is False and isinstance(facts.get("technical_sources"), list) and facts.get("human_default"):
        if any(field in facts["human_default"] for field in {"checkpoint", "DAG", "Skill", "receipt"}):
            errors.append("technical machine sources must stay out of the default summary")
    return errors


def _derive_incident(facts: dict[str, Any]) -> str | None:
    family = facts.get("incident_family")
    path = facts.get("matrix_path")
    if family not in INCIDENT_FAMILIES or path not in MATRIX_PATHS:
        return None
    if path == "escalate":
        return "ESCALATE_USER" if _decision_fields(facts) else None
    if path == "wait":
        proof = facts.get("waiting_proof")
        if waiting_proof_errors(proof) or _surface_open(facts):
            return None
        if family == "human-communication" and facts.get("notification") != "none":
            return None
        if family == "autonomous-closeout" and facts.get("merge_gate") != "blocked":
            return None
        return "KEEP_CURRENT"
    if path == "defer":
        if family in {"heartbeat-recovery", "human-communication"}:
            if family == "heartbeat-recovery":
                vector = facts.get("change_vector", {})
                return "KEEP_CURRENT" if facts.get("receipt") == "already-consumed" and facts.get("invalidation") == "none" and vector.get("retry") is True and vector.get("semantic_delta") is False else None
            return "KEEP_CURRENT" if facts.get("human_projection") == "machine-only" and nonempty(facts.get("deferred_detail")) else None
        if family == "autonomous-closeout":
            finding = facts.get("finding", {})
            return "CORRECT_DRIFT" if finding.get("treatment") == "defer" and finding.get("exit_impact") == "none" and nonempty(finding.get("carrier")) else None
        return "CORRECT_DRIFT" if any(nonempty(facts.get(key)) for key in ("deferred_carrier", "non_blocking_hardening", "shortest_product_validation")) else None
    if family == "desktop-asar-pnpm":
        return "CLOSEOUT_AND_RECOMPUTE" if facts.get("dmg_build") == "ready" and facts.get("clean_vm") == "ready" and facts.get("authority") else None
    if family == "release-acceptance-gating":
        pre = facts.get("pre_increment", {})
        return "CREATE_OR_WAKE_OWNER" if pre.get("safe_to_start") is True and facts.get("shared_carrier") == "available" and facts.get("authority") == "authorized" else None
    if family == "activity-without-product-progress":
        return "CORRECT_DRIFT" if facts.get("product_progress") == "unchanged" and facts.get("enabling_progress") == "unchanged" and nonempty(facts.get("shortest_product_validation")) else None
    if family == "heartbeat-recovery":
        vector = facts.get("change_vector", {})
        return "CORRECT_DRIFT" if vector.get("closure_status") == "unknown" and nonempty(facts.get("recovery_evidence")) else None
    if family == "human-communication":
        canonical = facts.get("canonical_fact", {})
        return "ROUTE_INFO" if nonempty(canonical.get("event_key")) and facts.get("human_projection") == "required" and nonempty(facts.get("human_summary")) else None
    if family == "autonomous-closeout":
        return "CLOSEOUT_AND_RECOMPUTE" if facts.get("authorization") == "confirmed" and facts.get("ci") == "passed" and facts.get("merge_gate") == "satisfied" and facts.get("target_head") == "exact-main" else None
    return None


def derive_verdict(facts: dict[str, Any]) -> str | None:
    """Derive a verdict from facts only; expected prose is intentionally unused."""
    if "incident_family" in facts or "matrix_path" in facts:
        return _derive_incident(facts)
    if isinstance(facts.get("owner_events"), list):
        return "ROUTE_INFO"
    if facts.get("delivery_attempt", {}).get("status") == "failed":
        return "CORRECT_DRIFT"
    if facts.get("owner_a_runtime") == "failed" or facts.get("skill_status") == "unavailable":
        return "CORRECT_DRIFT"
    if facts.get("event") == "PR_MERGED" and "change_entity" in facts:
        return "CLOSEOUT_AND_RECOMPUTE" if facts.get("closure_status") == "complete" and facts.get("checkpoint_cas") == "succeeds" else None
    if facts.get("event") == "PR_MERGED" and facts.get("owner_status") == "active":
        return "CLOSEOUT_AND_RECOMPUTE"
    if facts.get("dependency_repo") and facts.get("dependency_repo") != facts.get("authorized_repo"):
        return "ESCALATE_USER"
    if isinstance(facts.get("cycle"), list) and facts.get("fixtures_allow_safe_start") is True:
        return "CORRECT_DRIFT"
    if facts.get("critical_path_width") == 1 and facts.get("critical_path_stable_cycles", 0) >= 2 and facts.get("candidate_safe_slice") == "verified":
        return "CREATE_OR_WAKE_OWNER"
    if facts.get("affected_scope") and facts.get("owner_a_runtime") == "failed":
        return "CORRECT_DRIFT"
    if facts.get("truth_status") == "partial" and facts.get("github_issue_state") == "unavailable":
        return "ROUTE_INFO"
    if facts.get("fr_acceptance") == "stable" and facts.get("current_wave_work_items") == []:
        return "SHAPE_WORK_ITEMS"
    if facts.get("downstream_first_slice") == "safe with recorded contract":
        return "CORRECT_DRIFT"
    if facts.get("trigger") == "heartbeat" and facts.get("desired_runtime") and facts.get("desired_runtime") != facts.get("observed_runtime"):
        return "CORRECT_DRIFT"
    if facts.get("owner_a_desired") and facts.get("owner_a_desired") != facts.get("owner_a_observed"):
        return "CORRECT_DRIFT"
    if facts.get("previous_skill_digest") != facts.get("current_skill_digest") and nonempty(facts.get("current_skill_digest")):
        return "ROUTE_INFO"
    if facts.get("owner_status") == "initializing" or (facts.get("owner_status") == "active" and facts.get("pinned") is False):
        return "CORRECT_DRIFT"
    if facts.get("terminal_reason") in {"cancelled", "superseded"}:
        return "CLOSEOUT_AND_RECOMPUTE"
    if facts.get("capability_status") == "incompatible" and facts.get("writer_started") is False:
        return "SHAPE_WORK_ITEMS"
    if facts.get("external_gate") and facts.get("internal_successor") == "none":
        return "KEEP_CURRENT"
    if facts.get("parent_user_outcome") and facts.get("real_provider_evidence") == "missing":
        return "KEEP_CURRENT"
    if facts.get("shared_carriers") and facts.get("independent_acceptance_and_rollback") is False:
        return "CREATE_OR_WAKE_OWNER"
    if facts.get("current_unit") == "convergence" and facts.get("next_unlock_readiness") == "ready":
        return "SHAPE_WORK_ITEMS"
    if facts.get("internal_contract") == "missing" and facts.get("mature_standard_or_oss") == "verified":
        return "SHAPE_WORK_ITEMS"
    if any(item.get("classification") == "unclassified" for item in facts.get("remaining_gaps", []) if isinstance(item, dict)):
        return "SHAPE_WORK_ITEMS"
    if real_locator(facts.get("canonical_fact_id")) or isinstance(facts.get("canonical_fact"), dict):
        if facts.get("human_projection") in {"present", "required", "immediate"}:
            return "ROUTE_INFO"
    if facts.get("urgent_risk"):
        return "ESCALATE_USER"
    if facts.get("next_actor") == "user" or isinstance(facts.get("decision"), dict):
        return "ESCALATE_USER"
    if facts.get("event_key") and facts.get("occurred_at") and facts.get("delivery_attempts"):
        return "ROUTE_INFO"
    if facts.get("human_default"):
        return "ROUTE_INFO"
    if isinstance(facts.get("chain"), list) and facts.get("shared_product_effect") and facts.get("urgent_risk") is False:
        return "CLOSEOUT_AND_RECOMPUTE"
    if facts.get("current_generation") and facts.get("current_semantic_revision") and facts.get("events") and facts.get("product_effect") == "unchanged":
        return "KEEP_CURRENT"
    vector = facts.get("change_vector")
    if isinstance(vector, dict):
        if all(value in (False, 0, None, "", "none") for value in vector.values()):
            return "KEEP_CURRENT"
        if facts.get("closure_status") in {"unknown", "incomplete"} or facts.get("checkpoint_cas") == "conflict":
            return "CORRECT_DRIFT"
        return "ROUTE_INFO"
    if facts.get("closure_status") in {"unknown", "incomplete"} or facts.get("checkpoint_cas") == "conflict":
        return "CORRECT_DRIFT"
    if facts.get("replay_generation", 0) < facts.get("current_generation", 0) and facts.get("newer_checkpoint"):
        return "KEEP_CURRENT"
    if facts.get("deep_reason") and facts.get("repair") == "complete":
        return "ROUTE_INFO"
    if facts.get("sentinel_query") == "unchanged" and facts.get("closure_status") == "complete" and facts.get("checkpoint_cas") == "succeeds":
        return "ROUTE_INFO"
    if facts.get("waiting_proof") and facts.get("main_head"):
        return "CORRECT_DRIFT"
    if facts.get("events") and facts.get("product_effect") == "unchanged" and facts.get("cursor_advanced") is True:
        return "KEEP_CURRENT"
    dependency = facts.get("tasks_owner_dependency")
    if isinstance(dependency, dict):
        if (
            dependency.get("status") == "compatible"
            and dependency.get("mode") == "full"
            and dependency.get("execution_required") is True
            and facts.get("owner") == "none"
            and facts.get("delivery_unit") == "execution_ready"
        ):
            return "CREATE_OR_WAKE_OWNER"
        return "ROUTE_INFO"
    return None


def validate_case(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(case) - {"_line"} != ROOT_KEYS:
        errors.append("root keys must match schema")
    if case.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    if not nonempty(case.get("id")):
        errors.append("id must be non-empty")
    facts = case.get("facts")
    if not isinstance(facts, dict) or not facts:
        errors.append("facts must be a non-empty object")
        facts = {}
    expected = case.get("expected")
    if not isinstance(expected, dict) or set(expected) != EXPECTED_KEYS:
        errors.append("expected must contain verdict, must and must_not")
        expected = {}
    verdict = expected.get("verdict")
    if verdict not in VERDICTS:
        errors.append("invalid expected verdict")
    for field in ("must", "must_not"):
        values = expected.get(field)
        if not isinstance(values, list) or not values or not all(nonempty(value) for value in values):
            errors.append(f"expected.{field} must be a non-empty string array")
        elif any(not contains_cjk(value) for value in values):
            errors.append(f"expected.{field} must use Chinese plain language")
    family = facts.get("incident_family")
    path = facts.get("matrix_path")
    if (family is None) != (path is None):
        errors.append("incident_family and matrix_path must appear together")
    if family is not None and family not in INCIDENT_FAMILIES:
        errors.append("unknown incident_family")
    if path is not None and path not in MATRIX_PATHS:
        errors.append("unknown matrix_path")
    if family is not None:
        errors.extend(_incident_improvement_errors(facts))
        errors.extend(_incident_fact_errors(facts))
    if path == "wait" or isinstance(facts.get("waiting_proof"), dict):
        errors.extend(waiting_proof_errors(facts.get("waiting_proof"), require_fresh=path == "wait"))
        if path == "wait" and _surface_open(facts):
            errors.append("wait path cannot have executable surface")
    errors.extend(_audit_errors(facts))
    errors.extend(_width_errors(facts))
    errors.extend(_projection_errors(facts))
    errors.extend(_authority_contract_errors(facts))
    errors.extend(_tasks_owner_dependency_errors(facts))
    derived = derive_verdict(facts)
    if derived is None:
        errors.append("facts do not form a supported policy result")
    elif verdict != derived:
        errors.append(f"expected verdict {verdict!r} does not match facts-derived {derived!r}")
    return errors


def validate_document(cases: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    ids: set[str] = set()
    matrix: set[tuple[str, str]] = set()
    bounded_improvements: dict[str, int] = {}
    authority_locators: list[str] = []
    legacy = 0
    for index, case in enumerate(cases, 1):
        line = case.get("_line", index)
        case_id = case.get("id")
        if case_id in ids:
            failures.append(f"line {line}: duplicate id {case_id}")
        ids.add(case_id)
        facts = case.get("facts", {}) if isinstance(case, dict) else {}
        if isinstance(facts, dict):
            unknown = sorted(set(facts) - KNOWN_FACT_KEYS)
            if unknown:
                failures.append(f"line {line}: facts contain unknown fields {unknown}")
            improvement = facts.get("incident_improvement")
            if facts.get("incident_family") and isinstance(improvement, dict) and improvement.get("status") == "bounded_revision":
                family = facts.get("incident_family")
                bounded_improvements[family] = bounded_improvements.get(family, 0) + 1
            contract = facts.get("authority_contract")
            if isinstance(contract, dict):
                authority_locators.append(contract.get("contract_locator"))
        if isinstance(facts, dict) and facts.get("incident_family"):
            pair = (facts.get("incident_family"), facts.get("matrix_path"))
            if pair in matrix:
                failures.append(f"line {line}: duplicate incident matrix cell {pair}")
            matrix.add(pair)
        else:
            legacy += 1
        failures.extend(f"line {line}: {error}" for error in validate_case(case))
    if legacy != 47:
        failures.append(f"coverage: expected 47 non-incident product cases, found {legacy}")
    expected_matrix = {(family, path) for family in INCIDENT_FAMILIES for path in MATRIX_PATHS}
    missing = sorted(expected_matrix - matrix)
    extra = sorted(matrix - expected_matrix)
    if missing:
        failures.append(f"coverage: missing incident matrix cells {missing}")
    if extra:
        failures.append(f"coverage: invalid incident matrix cells {extra}")
    for family, count in sorted(bounded_improvements.items()):
        if count > 1:
            failures.append(f"incident improvement: {family} has more than one bounded revision")
    if len(authority_locators) != 1:
        failures.append(f"authority contract: expected exactly one contract, found {len(authority_locators)}")
    elif not real_locator(authority_locators[0]):
        failures.append("authority contract: contract_locator must be a real unique locator")
    elif len(set(authority_locators)) != len(authority_locators):
        failures.append("authority contract: contract_locator must be unique")
    return failures


def run(path: Path) -> list[str]:
    return validate_document(load_cases(path))


def _find(cases: list[dict[str, Any]], predicate) -> dict[str, Any]:
    return next(case for case in cases if predicate(case.get("facts", {})))


def self_test(path: Path) -> list[str]:
    cases = load_cases(path)
    failures: list[str] = []

    def rejects(label: str, candidate: list[dict[str, Any]], needle: str | None = None) -> None:
        errors = validate_document(candidate)
        if not errors or (needle and not any(needle in error for error in errors)):
            failures.append(f"self-test mutation was not rejected: {label}")

    def accepts(label: str, candidate: list[dict[str, Any]]) -> None:
        errors = validate_document(candidate)
        if errors:
            failures.append(f"self-test valid combination was rejected: {label}: {errors[0]}")

    duplicate = copy.deepcopy(cases)
    duplicate[1]["id"] = duplicate[0]["id"]
    rejects("duplicate ID", duplicate, "duplicate id")

    illegal = copy.deepcopy(cases)
    illegal[0]["expected"]["verdict"] = "NOT_ALLOWED"
    rejects("illegal verdict", illegal, "invalid expected verdict")

    wait_missing = copy.deepcopy(cases)
    wait_case = _find(wait_missing, lambda facts: facts.get("incident_family") == "heartbeat-recovery" and facts.get("matrix_path") == "wait")
    wait_case["facts"]["waiting_proof"].pop("next_action")
    rejects("missing waiting proof", wait_missing, "waiting_proof missing next_action")

    wait_expired = copy.deepcopy(cases)
    wait_case = _find(wait_expired, lambda facts: facts.get("incident_family") == "heartbeat-recovery" and facts.get("matrix_path") == "wait")
    wait_case["facts"]["waiting_proof"]["expires_at"] = "past"
    rejects("expired waiting proof", wait_expired, "expires_at is not fresh")

    executable_wait = copy.deepcopy(cases)
    wait_case = _find(executable_wait, lambda facts: facts.get("incident_family") == "release-acceptance-gating" and facts.get("matrix_path") == "wait")
    wait_case["facts"]["remaining_executable_surface"] = "ready"
    rejects("executable surface with KEEP_CURRENT", executable_wait, "executable surface")

    gap = copy.deepcopy(cases)
    gap.pop(next(index for index, case in enumerate(gap) if case.get("facts", {}).get("incident_family") == "human-communication" and case.get("facts", {}).get("matrix_path") == "defer"))
    rejects("6x4 matrix gap", gap, "missing incident matrix cells")

    leakage = copy.deepcopy(cases)
    human = _find(leakage, lambda facts: facts.get("incident_family") == "human-communication" and facts.get("matrix_path") == "advance")
    human["facts"]["human_summary"] = "产品更新：" + json.dumps(human["facts"]["canonical_fact"], ensure_ascii=False)
    rejects("default machine payload leakage", leakage, "leaks machine payload")

    fast_loop = copy.deepcopy(cases)
    fast = _find(fast_loop, lambda facts: facts.get("audit_path") == "Fast")
    fast["facts"]["audit_actions"].append("full_dag")
    rejects("Fast enters full loop", fast_loop, "full audit loop")

    width_loop = copy.deepcopy(cases)
    width = _find(width_loop, lambda facts: facts.get("critical_path_width") == 1)
    width["facts"]["width_health"].update(parallel_proof="fresh", audit_count=2)
    rejects("healthy width=1 repeated audit", width_loop, "repeatedly audited")

    detached_summary = copy.deepcopy(cases)
    summary_case = _find(detached_summary, lambda facts: facts.get("human_default"))
    for key in ("canonical_fact_id", "source_locator", "evidence", "product_effect", "human_projection", "human_summary", "projection_sources"):
        summary_case["facts"].pop(key, None)
    rejects("human summary without canonical fact", detached_summary, "human_default must be attached")

    canonical_sentinel = copy.deepcopy(cases)
    summary_case = _find(canonical_sentinel, lambda facts: facts.get("human_default"))
    summary_case["facts"]["canonical_fact_id"] = "none"
    rejects("canonical fact sentinel locator", canonical_sentinel, "canonical_fact_id must be a real locator")

    for key in ("product_goal", "reproduced_failure", "current_fix", "evidence"):
        candidate = copy.deepcopy(cases)
        _find(candidate, lambda facts: facts.get("incident_family") == "desktop-asar-pnpm" and facts.get("matrix_path") == "advance")["facts"].pop(key)
        rejects(f"Desktop closeout missing {key}", candidate, "missing fact")

    for key in ("review", "target_head", "evidence"):
        candidate = copy.deepcopy(cases)
        _find(candidate, lambda facts: facts.get("incident_family") == "autonomous-closeout" and facts.get("matrix_path") == "advance")["facts"].pop(key)
        rejects(f"autonomous closeout missing {key}", candidate, "missing fact")

    for key in sorted(FAST_CHANGE_VECTOR_FIELDS):
        candidate = copy.deepcopy(cases)
        fast_case = _find(candidate, lambda facts: facts.get("audit_path") == "Fast")
        fast_case["facts"]["change_vector"].pop(key)
        rejects(f"Fast missing change vector field {key}", candidate, "Fast change_vector must be complete")
    fast_cache = copy.deepcopy(cases)
    _find(fast_cache, lambda facts: facts.get("audit_path") == "Fast")["facts"]["evidence_cache"] = "stale"
    rejects("Fast stale evidence cache", fast_cache, "fresh evidence cache")
    fast_checkpoint = copy.deepcopy(cases)
    _find(fast_checkpoint, lambda facts: facts.get("audit_path") == "Fast")["facts"]["checkpoint_identity"] = "unverified"
    rejects("Fast unverified checkpoint", fast_checkpoint, "verified checkpoint identity")
    fast_action = copy.deepcopy(cases)
    _find(fast_action, lambda facts: facts.get("audit_path") == "Fast")["facts"]["audit_actions"] = []
    rejects("Fast empty light actions", fast_action, "non-empty list")

    bounded_heartbeat = copy.deepcopy(cases)
    bounded = _find(bounded_heartbeat, lambda facts: isinstance(facts.get("incident_improvement"), dict) and facts["incident_improvement"].get("status") == "bounded_revision")
    bounded["facts"]["incident_improvement"]["heartbeat_triggered"] = None
    rejects("bounded improvement heartbeat trigger", bounded_heartbeat, "heartbeat_triggered=false")
    bounded_locator = copy.deepcopy(cases)
    bounded = _find(bounded_locator, lambda facts: isinstance(facts.get("incident_improvement"), dict) and facts["incident_improvement"].get("status") == "bounded_revision")
    bounded["facts"]["incident_improvement"]["stable_locator"] = "none"
    bounded["facts"]["incident_improvement"]["real_impact"] = "none"
    rejects("bounded improvement sentinel locator", bounded_locator, "stable locator and real impact")

    authority_missing = copy.deepcopy(cases)
    authority_case = _find(authority_missing, lambda facts: isinstance(facts.get("authority_contract"), dict))
    authority_case["facts"]["authority_contract"].pop("digest")
    rejects("authority contract missing digest", authority_missing, "authority_contract missing digest")
    authority_conflict = copy.deepcopy(cases)
    authority_case = _find(authority_conflict, lambda facts: isinstance(facts.get("authority_contract"), dict))
    authority_case["facts"]["authority_contract_summary"]["revision"] = 99
    rejects("authority contract summary conflict", authority_conflict, "summary conflicts on revision")
    authority_repo = copy.deepcopy(cases)
    authority_case = _find(authority_repo, lambda facts: isinstance(facts.get("authority_contract"), dict))
    authority_case["facts"]["authority_contract"]["repo_locator"] = "github:evil/MC-AGENT-KIT-fork"
    rejects("authority contract cross repository", authority_repo, "crosses repository boundary")
    authority_target = copy.deepcopy(cases)
    authority_case = _find(authority_target, lambda facts: isinstance(facts.get("authority_contract"), dict))
    authority_case["facts"]["authority_contract"]["target_ref"] = "github:other/MC-AGENT-KIT@deadbeef"
    rejects("authority contract cross target", authority_target, "target_ref must identify")
    authority_expired = copy.deepcopy(cases)
    authority_case = _find(authority_expired, lambda facts: isinstance(facts.get("authority_contract"), dict))
    authority_case["facts"]["authority_contract"]["expiry"] = "past"
    rejects("authority contract expired", authority_expired, "authority_contract expiry is not fresh")
    authority_duplicate = copy.deepcopy(cases)
    authority_case = _find(authority_duplicate, lambda facts: isinstance(facts.get("authority_contract"), dict))
    authority_duplicate[0]["facts"]["authority_contract"] = copy.deepcopy(authority_case["facts"]["authority_contract"])
    authority_duplicate[0]["facts"]["authority_contract_summary"] = copy.deepcopy(authority_case["facts"]["authority_contract_summary"])
    rejects("duplicate authority contract locator", authority_duplicate, "expected exactly one contract")

    dependency_install_without_consent = copy.deepcopy(cases)
    dependency_case = _find(
        dependency_install_without_consent,
        lambda facts: isinstance(facts.get("tasks_owner_dependency"), dict)
        and facts["tasks_owner_dependency"].get("user_decision") == "pending",
    )
    dependency_case["facts"]["tasks_owner_dependency"]["install_attempted"] = True
    rejects("tasks-owner install without consent", dependency_install_without_consent, "requires explicit user consent")

    dependency_analysis_prompt = copy.deepcopy(cases)
    dependency_case = _find(
        dependency_analysis_prompt,
        lambda facts: isinstance(facts.get("tasks_owner_dependency"), dict)
        and facts["tasks_owner_dependency"].get("execution_required") is False,
    )
    dependency_case["facts"]["tasks_owner_dependency"].update(
        user_decision="pending",
        mode="install_pending",
        prompt_count=1,
        prior_user_decision="none",
        install_source=TASKS_OWNER_INSTALL_SOURCE,
        install_target=TASKS_OWNER_INSTALL_TARGET,
    )
    rejects("tasks-owner prompt during analysis", dependency_analysis_prompt, "analysis-only work must not ask")

    dependency_false_compatibility = copy.deepcopy(cases)
    dependency_case = _find(
        dependency_false_compatibility,
        lambda facts: isinstance(facts.get("tasks_owner_dependency"), dict)
        and facts["tasks_owner_dependency"].get("status") == "compatible",
    )
    dependency_case["facts"]["tasks_owner_dependency"]["capabilities"].remove("delivery_closeout")
    rejects("tasks-owner version-only compatibility", dependency_false_compatibility, "required capabilities")

    dependency_unchecked_install = copy.deepcopy(cases)
    dependency_case = _find(
        dependency_unchecked_install,
        lambda facts: isinstance(facts.get("tasks_owner_dependency"), dict)
        and facts["tasks_owner_dependency"].get("user_decision") == "accepted",
    )
    dependency_case["facts"]["tasks_owner_dependency"]["rechecked_after_install"] = False
    rejects("tasks-owner install without recheck", dependency_unchecked_install, "attempted and rechecked")

    dependency_repeated_prompt = copy.deepcopy(cases)
    dependency_case = _find(
        dependency_repeated_prompt,
        lambda facts: isinstance(facts.get("tasks_owner_dependency"), dict)
        and facts["tasks_owner_dependency"].get("user_decision") == "declined",
    )
    dependency_case["facts"]["tasks_owner_dependency"]["prompt_count"] = 1
    rejects("tasks-owner repeated prompt", dependency_repeated_prompt, "must not prompt again")

    dependency_wrong_target = copy.deepcopy(cases)
    dependency_case = _find(
        dependency_wrong_target,
        lambda facts: isinstance(facts.get("tasks_owner_dependency"), dict)
        and facts["tasks_owner_dependency"].get("user_decision") == "pending",
    )
    dependency_case["facts"]["tasks_owner_dependency"]["install_target"] = "codex-plugin:tasks-owner"
    rejects("tasks-owner plugin target", dependency_wrong_target, "must be the tasks-owner Skill directory")

    dependency_wrong_source = copy.deepcopy(cases)
    dependency_case = _find(
        dependency_wrong_source,
        lambda facts: isinstance(facts.get("tasks_owner_dependency"), dict)
        and facts["tasks_owner_dependency"].get("user_decision") == "pending",
    )
    dependency_case["facts"]["tasks_owner_dependency"]["install_source"] = "github:evil/fork@main:skills/dev/tasks-owner"
    rejects("tasks-owner unverified source", dependency_wrong_source, "verified PMO release source")

    dependency_runtime_failure = copy.deepcopy(cases)
    dependency_case = _find(
        dependency_runtime_failure,
        lambda facts: isinstance(facts.get("tasks_owner_dependency"), dict)
        and facts["tasks_owner_dependency"].get("status") == "compatible",
    )
    dependency_case["facts"]["owner_a_runtime"] = "failed"
    dependency_case["expected"]["verdict"] = "CORRECT_DRIFT"
    accepts("tasks-owner cannot mask runtime failure", dependency_runtime_failure)

    dependency_cross_repo = copy.deepcopy(cases)
    dependency_case = _find(
        dependency_cross_repo,
        lambda facts: isinstance(facts.get("tasks_owner_dependency"), dict)
        and facts["tasks_owner_dependency"].get("status") == "compatible",
    )
    dependency_case["facts"].update(authorized_repo="repo-a", dependency_repo="repo-b")
    dependency_case["expected"]["verdict"] = "ESCALATE_USER"
    accepts("tasks-owner cannot mask repository boundary", dependency_cross_repo)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        failures = self_test(args.path) if args.self_test else run(args.path)
    except (OSError, TypeError, ValueError, StopIteration, json.JSONDecodeError) as exc:
        failures = [str(exc)]
    for failure in failures:
        print(f"error: {failure}")
    if not failures:
        print("PMO trajectory self-test passed." if args.self_test else "PMO trajectory validation passed.")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())

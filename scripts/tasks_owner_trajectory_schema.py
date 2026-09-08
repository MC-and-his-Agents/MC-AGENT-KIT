"""Unit Owner 轨迹的最小结构；字段一致性不等于真实宿主证据。

initial.batches 按已知的发布批次绑定 head、head_carrier 与写入范围。
独立批次可以有相同 base head，但必须有不同的可变 head 载体；同一批次只
重放一条线性的 head 演进，不声称证明多分支集成、冲突解决或产品整体正确。
unit_id 是执行者身份，批次事件由 facts.batch_locator 指定交付对象。
execution_kind 默认为实际采用的 local/native_subagent/app_task；可选的
execution_mode_selection 只解释层级选择，不是另一套必走协议。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


SCHEMA_VERSION = "tasks-owner-trajectory.v2"
ROOT_KEYS = set("schema_version id source_kind mode initial events expected evidence".split())
EVENT_KEYS = set("seq turn actor kind locator unit_id generation tool args facts".split())
MODES = {"local", "delegated", "review", "recovery", "heartbeat", "cleanup"}
RULES = {
    "authorization", "writer_safety", "planning", "review_integrity",
    "event_recovery", "incremental_progress", "cleanup_safety", "evidence_binding",
}
ACTORS = {"owner", "task", "app_task", "native_subagent", "reviewer", "external", "user"}
EXECUTION_KINDS = {"local", "native_subagent", "app_task"}
LOCATOR_SENTINELS = {"", "none", "null", "missing", "unknown", "n/a", "na", "tbd"}
USER_DECISION_FIELDS = {
    "decision_boundary_locator", "decision_authority", "existing_truth_exhausted",
    "bounded_investigation_locator", "bounded_investigation_status",
    "safe_reversible_default_available", "safe_reversible_default_locator",
    "exact_decision_question", "blocked_action", "blocking_scope",
    "unaffected_work_continues", "requires_user_judgment",
}
USER_DECISION_AUTHORITIES = {
    "product_behavior", "scope_or_priority", "material_cost_or_risk",
    "permission_privacy_data", "irreversible_external_result",
}
EVIDENCE_KEY_FIELDS = {"tree_digest", "acceptance_digest", "environment_class"}
ADMISSION_FIELDS = set("batch_locator execution_kind role scope_locator convergence_chain_locator carriers authority_locator capability_locator required_capabilities observed_capabilities monitor_locator validation_plan execution_mode_selection gap_locator".split())
FACT_FIELDS = {
    "admission": ADMISSION_FIELDS,
    "successor": ADMISSION_FIELDS,
    "write": set("scope_locator authority_locator carriers base_head new_head tree_digest finding_locators".split()),
    "unit_state": set("host_status write_authority readback_locator quiescence_locator".split()),
    "preflight": set("batch_locator head evidence_key covered_surfaces check_results sibling_scan".split()),
    "fresh_review": set("batch_locator head evidence_key reviewer_locator verdict finding_locators diff_locator".split()),
    "finding_disposition": set("batch_locator finding_locator acceptance_or_invariant_locator blocks_current_exit disposition carrier_locator rejection_basis boundary_expansion root_cause_key evidence_locator evidence_digest decision_boundary_locator decision_authority existing_truth_exhausted bounded_investigation_locator bounded_investigation_status safe_reversible_default_available safe_reversible_default_locator exact_decision_question blocked_action blocking_scope unaffected_work_continues requires_user_judgment".split()),
    "reassessment": set("batch_locator evidence_subject evidence_revision evidence_locator scope_locator authority_locator user_decision_locator".split()),
    "user_decision": set("decision_locator authority_locator scope_locator action approved".split()),
    "publish": set("batch_locator action exact_head tree_digest acceptance_evidence_locator product_evidence_locator pr_metadata verification_authority check_results".split()),
    "completion": set("event_key revision outcome source_locator host_status head".split()),
    "completion_consumed": {"event_key", "revision"},
    "source_readback": {"source", "revision", "evidence_locator", "batch_locator"},
    "read_evidence": {"subject", "revision", "source"},
    "recompute_frontier": {"sources"},
    "owner_final": {"status", "product_acceptance_locator"},
    "closeout": set("batch_locator action exact_head tree_digest acceptance_evidence_locator product_evidence_locator merge_locator issue_state_locator no_pr_evidence_locator verification_authority check_results pr_metadata".split()),
    "cleanup": set("batch_locator target_worktree target_ref target_oid authority_locator identity_readback_locator outcome".split()),
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def real_locator(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in LOCATOR_SENTINELS


def valid_iso(value: Any) -> bool:
    if not nonempty(value):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def writer_publishable(unit: dict[str, Any]) -> bool:
    return unit.get("write_authority") in {"revoked", "none"} and (
        unit.get("host_status") == "terminal"
        or unit.get("host_status") == "quiesced" and real_locator(unit.get("quiescence_locator"))
    )


def user_decision_errors(value: Any, expected_boundary_locator: Any = None) -> list[str]:
    if not isinstance(value, dict) or not USER_DECISION_FIELDS <= set(value):
        return ["waiting_user requires user-reserved decision evidence"]
    errors: list[str] = []
    for field in USER_DECISION_FIELDS - {
        "existing_truth_exhausted", "safe_reversible_default_available",
        "unaffected_work_continues", "requires_user_judgment",
        "bounded_investigation_status", "safe_reversible_default_locator",
    }:
        if not real_locator(value.get(field)):
            errors.append(f"waiting_user {field} must be locatable")
    if not real_locator(expected_boundary_locator) or value.get("decision_boundary_locator") != expected_boundary_locator:
        errors.append("waiting_user decision boundary must match current admission authority")
    if value.get("decision_authority") not in USER_DECISION_AUTHORITIES:
        errors.append("waiting_user decision is not user-reserved")
    if value.get("existing_truth_exhausted") is not True or not real_locator(value.get("bounded_investigation_locator")):
        errors.append("waiting_user requires bounded investigation of existing truth")
    if value.get("bounded_investigation_status") != "complete":
        errors.append("waiting_user bounded investigation is incomplete")
    if value.get("safe_reversible_default_available") is not False or value.get("safe_reversible_default_locator") != "none":
        errors.append("waiting_user is forbidden when a safe reversible default exists")
    if value.get("unaffected_work_continues") is not True or value.get("requires_user_judgment") is not True:
        errors.append("waiting_user must preserve unaffected work and require user judgment")
    return errors


def schema_errors(case: Any) -> list[str]:
    if not isinstance(case, dict) or set(case) != ROOT_KEYS:
        return ["root keys must match schema"]
    errors: list[str] = []
    if case.get("schema_version") != SCHEMA_VERSION or not real_locator(case.get("id")):
        errors.append("invalid schema version or case id")
    if case.get("source_kind") not in {"recorded_fixture", "live_readback"} or case.get("mode") not in MODES:
        errors.append("invalid evidence kind or mode")
    initial = case.get("initial")
    required = {"owner_thread_id", "scope_locator", "convergence_chain_locator", "authority", "batches", "required_surfaces", "review_required", "review_policy_locator", "gaps"}
    if not isinstance(initial, dict) or not required <= set(initial):
        errors.append("initial delivery scope is incomplete")
    else:
        for field in ("owner_thread_id", "scope_locator", "convergence_chain_locator", "review_policy_locator"):
            if not real_locator(initial.get(field)):
                errors.append(f"initial {field} is missing")
        if not isinstance(initial.get("review_required"), bool):
            errors.append("review requirement must be explicit")
        if not isinstance(initial.get("required_surfaces"), list) or any(not real_locator(x) for x in initial["required_surfaces"]):
            errors.append("required surfaces must be an explicit list")
        authority = initial.get("authority")
        if not isinstance(authority, dict) or set(authority) != {"locator", "actions", "carriers"}:
            errors.append("authority must bind source, actions and carriers")
        elif not real_locator(authority["locator"]) or any(not isinstance(authority[k], list) or any(not real_locator(x) for x in authority[k]) for k in ("actions", "carriers")):
            errors.append("authority source or boundary is invalid")
        batches = initial.get("batches")
        batch_fields = {"locator", "head", "head_carrier", "carriers"} | EVIDENCE_KEY_FIELDS
        if not isinstance(batches, list) or any(
            not isinstance(batch, dict) or set(batch) != batch_fields
            or any(not real_locator(batch.get(k)) for k in batch_fields - {"carriers"})
            or not isinstance(batch.get("carriers"), list) or not batch["carriers"]
            or any(not real_locator(c) for c in batch["carriers"]) for batch in batches
        ):
            errors.append("publication batches must bind head, physical head carrier, scope and evidence key")
        elif len({b["locator"] for b in batches}) != len(batches) or len({b["head_carrier"] for b in batches}) != len(batches):
            errors.append("independent publication batches need distinct identities and mutable head carriers")
        gaps = initial.get("gaps")
        if not isinstance(gaps, list) or any(not isinstance(gap, dict) or not {"locator", "status", "dependencies"} <= set(gap) for gap in gaps):
            errors.append("product gaps must have identity, state and dependencies")
        elif any(
            not real_locator(gap["locator"]) or gap["status"] not in {"ready", "blocked", "active", "complete", "waiting_external", "waiting_user"}
            or not isinstance(gap["dependencies"], list) or any(not real_locator(x) for x in gap["dependencies"]) for gap in gaps
        ):
            errors.append("product gap identity, state or dependencies are invalid")
        elif len({gap["locator"] for gap in gaps}) != len(gaps):
            errors.append("product gap identity must be unique")
    expected = case.get("expected")
    if not isinstance(expected, dict) or set(expected) != {"verdict", "rule_id"} or expected.get("verdict") not in {"pass", "fail"} or expected.get("rule_id") not in RULES:
        errors.append("invalid expected result")
    evidence = case.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence must be an object")
    elif case.get("source_kind") == "recorded_fixture" and not real_locator(evidence.get("fixture_id")):
        errors.append("recorded fixture needs an explicit fixture id")
    elif case.get("source_kind") == "live_readback" and any(not real_locator(evidence.get(k)) for k in ("host_id", "source_locator", "readback_sha256")):
        errors.append("tool trace needs independently supplied readback identity and digest")
    events = case.get("events")
    if not isinstance(events, list) or not events:
        return errors + ["events must be a non-empty array"]
    locators: set[str] = set()
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or set(event) != EVENT_KEYS:
            errors.append(f"event {index} keys must match schema")
            continue
        if type(event.get("seq")) is not int or event["seq"] != index:
            errors.append(f"event {index} sequence is not contiguous")
        if event.get("actor") not in ACTORS or event.get("kind") not in FACT_FIELDS:
            errors.append(f"event {index} has unsupported actor or kind")
        for field in ("turn", "locator", "tool"):
            if not real_locator(event.get(field)):
                errors.append(f"event {index} missing {field}")
        if real_locator(event["locator"]):
            if event["locator"] in locators:
                errors.append(f"event {index} repeats an evidence locator")
            locators.add(event["locator"])
        if event["unit_id"] is not None and not real_locator(event["unit_id"]):
            errors.append(f"event {index} has invalid unit identity")
        if type(event["generation"]) is not int or event["generation"] < 1:
            errors.append(f"event {index} has invalid generation")
        if not isinstance(event.get("args"), dict) or not isinstance(event.get("facts"), dict):
            errors.append(f"event {index} args and facts must be objects")
        elif set(event["facts"]) - FACT_FIELDS.get(event["kind"], set()):
            errors.append(f"event {index} contains unsupported facts")
    return errors

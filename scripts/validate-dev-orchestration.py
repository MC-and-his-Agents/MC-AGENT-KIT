#!/usr/bin/env python3
"""校验 PMO 与 Tasks Owner 的共享合同和关键行为。"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "skills/dev/tasks-owner/references/dev-orchestration-contract.json"
PLATFORM = ROOT / "skills/dev/tasks-owner/references/codex-app.md"
FEEDBACK_FORM = ROOT / ".github/ISSUE_TEMPLATE/skill-feedback.yml"
CYCLES = ROOT / "skills/dev/pmo/evals/cycle_cases.jsonl"
INTEGRATION = ROOT / "skills/dev/tasks-owner/evals/dev_orchestration_cases.jsonl"
OWNER_TRIGGERS = ROOT / "skills/dev/tasks-owner/evals/trigger_cases.json"
PMO_TRIGGERS = ROOT / "skills/dev/pmo/evals/trigger_cases.json"
CAPABILITIES = {
    "pmo_admission", "owner_sparse_delta", "single_scope_owner_execution",
    "bounded_finding_fix", "delivery_closeout", "bounded_execution_retrospective",
    "skill_feedback_candidate", "product_frontier_closure", "native_skill_feedback",
}
PMO_ADMISSION_FIELDS = {
    "contract_id", "schema_version", "authority_origin", "scope_kind", "scope_locator",
    "planning_truth_locator", "product_goal", "expected_contribution", "acceptance_locator",
    "product_exit_locator", "governing_invariant_locator", "convergence_chain_locator",
    "ownership_boundary_locator", "allowed_scope", "excluded_scope", "carrier_locator",
    "target_head_locator", "decision_boundary_locator", "repair_budget",
}
ACTION_ORDER = [
    "closeout_unit", "correct_drift", "recompute_product_frontier", "route_delta", "shape_work_item",
    "create_or_wake_owner", "request_user_decision", "record_evidenced_wait",
    "record_skill_feedback_candidate", "submit_or_update_skill_feedback",
]
FRONTIER_CLASSES = {
    "execution_ready", "admission_pending", "active_execution", "waiting_external",
    "waiting_user", "replan_or_reownership_pending", "closeout_pending",
}
OWNER_ACTIONABLE_CLASSES = {
    "execution_ready", "admission_pending", "replan_or_reownership_pending", "closeout_pending",
}
WAIT_CLASSES = {"active_execution", "waiting_external", "waiting_user"}
GAP_REQUIRED_FIELDS = {
    "gap_locator", "product_exit_locator", "classification", "owner_or_next_actor", "evidence_locator",
    "wake_condition", "invalidation_condition",
}
WAITING_PROOF_FIELDS = {
    "subject", "external_condition", "responsible_party", "evidence_locator",
    "observed_at", "freshness", "wake_condition", "invalidation_condition",
}
RETROSPECTIVE_TRIGGERS = {
    "user_correction", "explicit_skill_correction", "repeated_failure", "post_repair_recurrence",
    "no_product_progress", "scope_dependency_ownership_drift", "source_of_truth_conflict",
    "repeated_platform_assumption_failure", "high_impact_incident",
}
RETROSPECTIVE_CANDIDATE_FIELDS = {
    "affected_skill", "trigger", "observed_behavior", "expected_behavior", "product_impact",
    "current_resolution", "generalizable_reason", "regression_proposal", "source_locator",
    "disclosure_status", "fingerprint_seed",
}
CORE_FEEDBACK_FIELDS = {
    "affected_skill", "retrospective_trigger", "observed_behavior", "expected_behavior",
    "product_impact", "current_resolution", "generalizable_root_cause", "proposed_regression",
    "redacted_evidence", "fingerprint_occurrence",
}
FINGERPRINT_FIELDS = {
    "affected_skill", "incident_root_cause_class", "governing_behavior_category", "platform_contract_major",
}
FEEDBACK_ACTIONS = {"search_issue", "read_issue", "create_issue", "add_comment"}
FEEDBACK_WRITE_ACTIONS = {"create_issue", "add_comment"}
FEEDBACK_FORBIDDEN_ACTIONS = {
    "write_code", "create_branch", "create_pull_request", "merge_pull_request", "create_release",
    "close_issue", "delete_issue", "update_milestone", "update_labels", "update_assignees",
    "change_permissions", "install_skill", "update_skill", "reload_skill",
}
FEEDBACK_PRECONDITIONS = {
    "skill_identity_match", "canonical_repository_match", "github_feedback_capability_available",
    "dedupe_complete", "redaction_safe",
}
FEEDBACK_STATUSES = {"none", "candidate", "deduped", "submitted", "deferred_private"}
FEEDBACK_TARGETS = {"pmo", "tasks-owner", "platform", "none"}
SUBMISSION_FIELDS = {
    "feedback_write_action", "feedback_submission_locator", "feedback_readback_verified", "skill_digest_unchanged",
}
OCCURRENCE_FIELDS = {"source_locator", "product_impact", "current_resolution", "root_cause_delta", "regression_delta"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: 必须是对象")
        value["_line"] = number
        rows.append(value)
    return rows


def real_locator(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in {"", "none", "missing", "unknown"}


def semver(value: Any) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", str(value))
    return tuple(map(int, match.groups())) if match else None


def version_is_compatible(actual: Any, compatibility: dict[str, Any]) -> bool:
    parsed = semver(actual)
    minimum = semver(compatibility.get("minimum_compatible_version"))
    return parsed is not None and minimum is not None and parsed >= minimum and compatibility.get("required_contract_schema_major") == 1


def feedback_fingerprint(facts: dict[str, Any], contract: dict[str, Any]) -> str:
    fields = contract["skill_feedback"]["fingerprint_fields"]
    return json.dumps([facts.get(field) for field in fields], ensure_ascii=False, separators=(",", ":"))


def feedback_api_body(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "affected_skill": candidate.get("affected_skill"),
        "retrospective_trigger": candidate.get("trigger"),
        "observed_behavior": candidate.get("observed_behavior"),
        "expected_behavior": candidate.get("expected_behavior"),
        "product_impact": candidate.get("product_impact"),
        "current_resolution": candidate.get("current_resolution"),
        "generalizable_root_cause": candidate.get("generalizable_reason"),
        "proposed_regression": candidate.get("regression_proposal"),
        "redacted_evidence": candidate.get("source_locator"),
        "fingerprint_occurrence": {
            "fingerprint": candidate.get("fingerprint_seed"),
            "occurrence": "first_occurrence",
        },
    }


def feedback_fact_errors(facts: dict[str, Any]) -> list[str]:
    if not facts.get("retrospective"):
        return []
    root_cause = facts.get("root_cause_target")
    if root_cause not in {"project", "planning", "skill", "platform"}:
        return ["执行复盘 root_cause_target 无效"]
    if root_cause in {"project", "planning"}:
        return []
    if facts.get("current_delivery_action"):
        return []
    if facts.get("product_actions_complete") is not True:
        return ["Skill feedback 必须后于产品恢复与纠偏"]
    candidate = facts.get("feedback_candidate")
    if not isinstance(candidate, dict) or set(candidate) != RETROSPECTIVE_CANDIDATE_FIELDS:
        return ["Skill feedback candidate 字段不完整"]
    if any(not real_locator(candidate.get(field)) for field in RETROSPECTIVE_CANDIDATE_FIELDS - {"fingerprint_seed"}):
        return ["Skill feedback candidate 字段必须可回读"]
    fingerprint = candidate.get("fingerprint_seed")
    if not isinstance(fingerprint, dict) or set(fingerprint) != FINGERPRINT_FIELDS:
        return ["Skill feedback candidate fingerprint 必须只包含稳定字段"]
    affected_skill = candidate.get("affected_skill")
    if (
        fingerprint.get("affected_skill") != affected_skill
        or fingerprint.get("incident_root_cause_class") != root_cause
        or not real_locator(fingerprint.get("governing_behavior_category"))
        or fingerprint.get("platform_contract_major") != 1
    ):
        return ["Skill feedback candidate fingerprint 与复盘事实不一致"]
    if candidate.get("trigger") != facts.get("retrospective"):
        return ["Skill feedback candidate 的 trigger 或 affected_skill 无效"]
    if root_cause == "skill" and affected_skill not in {"pmo", "tasks-owner"}:
        return ["Skill 根因必须定位到 pmo 或 tasks-owner"]
    if root_cause == "platform" and affected_skill != "platform":
        return ["平台根因必须定位到 platform"]
    if facts.get("github_feedback_capability_available") is not True and any(
        facts.get(field) for field in ("feedback_write_succeeded", "feedback_readback_verified")
    ):
        return ["GitHub feedback capability 不可用时不能携带成功或回读事实"]
    if facts.get("feedback_dedupe_complete") is True and not isinstance(facts.get("existing_feedback_issue"), bool):
        return ["Skill feedback dedupe 完成后必须显式记录是否已有 Issue"]
    if facts.get("feedback_write_action") in FEEDBACK_ACTIONS - FEEDBACK_WRITE_ACTIONS:
        return ["Skill feedback 搜索/读取动作不能冒充写入动作"]
    if facts.get("feedback_dedupe_complete") is True and facts.get("feedback_write_action") in FEEDBACK_WRITE_ACTIONS:
        expected_action = "add_comment" if facts.get("existing_feedback_issue") else "create_issue"
        if facts.get("feedback_write_action") != expected_action:
            return ["Skill feedback 写入动作与 dedupe 结果不一致"]
    if facts.get("feedback_write_action") == "create_issue":
        body = facts.get("feedback_api_body")
        if not isinstance(body, dict) or set(body) != CORE_FEEDBACK_FIELDS or body != feedback_api_body(candidate):
            return ["create_issue 必须显式投影完整且等价的 API body"]
    if facts.get("existing_feedback_issue") and facts.get("feedback_dedupe_complete") is True:
        occurrence = facts.get("feedback_occurrence")
        if not isinstance(occurrence, dict) or set(occurrence) != OCCURRENCE_FIELDS or any(
            not real_locator(occurrence.get(field)) for field in OCCURRENCE_FIELDS
        ):
            return ["同 fingerprint occurrence comment 字段不完整"]
    return []


def cycle_fact_errors(facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    exits = facts.get("product_exit_locators")
    gaps = facts.get("gaps")
    if not isinstance(exits, list) or any(not real_locator(item) for item in exits) or len(exits) != len(set(exits)):
        errors.append("product_exit_locators 必须是无重复的真实 locator 列表")
    if facts.get("frontier_closure_status") not in {"complete", "incomplete"}:
        errors.append("frontier_closure_status 无效")
    if not isinstance(gaps, list):
        return errors + ["gaps 必须是列表"]
    locators: set[str] = set()
    linked_exits: set[str] = set()
    for gap in gaps:
        if not isinstance(gap, dict) or not GAP_REQUIRED_FIELDS <= set(gap):
            errors.append("gap 缺少机器合同字段")
            continue
        if any(not real_locator(gap.get(field)) for field in GAP_REQUIRED_FIELDS):
            errors.append("gap 字段必须可定位")
        locator = gap.get("gap_locator")
        if locator in locators:
            errors.append("gap_locator 重复")
        locators.add(locator)
        linked_exits.add(gap.get("product_exit_locator"))
        classification = gap.get("classification")
        if classification not in FRONTIER_CLASSES:
            errors.append("gap classification 无效")
        if classification == "waiting_external":
            proof = gap.get("waiting_proof")
            if not isinstance(proof, dict) or not WAITING_PROOF_FIELDS <= set(proof) or any(
                not real_locator(proof.get(field)) for field in WAITING_PROOF_FIELDS
            ):
                errors.append("waiting_external 缺少完整且当前的 waiting proof")
            elif str(proof["freshness"]).strip().lower() in {"stale", "expired", "invalid"}:
                errors.append("waiting_external 使用了陈旧 waiting proof")
        elif "waiting_proof" in gap:
            errors.append("只有 waiting_external 可以携带 waiting proof")
    if facts.get("product_exit_complete") and (exits or gaps):
        errors.append("产品出口完成时不能仍有出口或差距")
    if not facts.get("product_exit_complete") and not exits:
        errors.append("产品出口未完成时必须枚举出口")
    if facts.get("frontier_closure_status") == "complete" and not facts.get("product_exit_complete") and not gaps:
        errors.append("完整前沿必须枚举剩余差距")
    if (
        facts.get("frontier_closure_status") == "complete"
        and isinstance(exits, list)
        and linked_exits != set(exits)
    ):
        errors.append("完整前沿必须让每个产品出口至少关联一个已分类 gap，且不能引用未知出口")
    return errors


def derive_cycle(facts: dict[str, Any]) -> tuple[str, list[str]]:
    if cycle_fact_errors(facts):
        return "progressed", ["recompute_product_frontier"]
    actions: list[str] = []
    gaps = facts.get("gaps") if isinstance(facts.get("gaps"), list) else []
    classes = {gap.get("classification") for gap in gaps if isinstance(gap, dict)}
    if facts.get("merge_verified"):
        actions.append("closeout_unit")
    elif "closeout_pending" in classes:
        actions.append("closeout_unit")
    if facts.get("drift_detected"):
        actions.append("correct_drift")
    if facts.get("frontier_recomputed") is True or facts.get("frontier_closure_status") == "incomplete":
        actions.append("recompute_product_frontier")
    if facts.get("route_delta_ready"):
        actions.append("route_delta")
    if "replan_or_reownership_pending" in classes:
        actions.append("shape_work_item")
    if classes & {"execution_ready", "admission_pending"}:
        actions.append("create_or_wake_owner")
    if "waiting_user" in classes:
        actions.append("request_user_decision")
    if "waiting_external" in classes:
        actions.append("record_evidenced_wait")
    if facts.get("feedback_candidate"):
        actions.append("record_skill_feedback_candidate")
    if facts.get("feedback_submission_ready") and all(
        facts.get(key) is True
        for key in (
            "product_actions_complete", "skill_identity_match", "canonical_repository_match",
            "github_feedback_capability_available", "feedback_dedupe_complete", "feedback_redaction_safe",
        )
    ):
        actions.append("submit_or_update_skill_feedback")
    product = any(action in ACTION_ORDER[:6] for action in actions)
    blocked = bool(classes & {"waiting_user", "waiting_external", "active_execution"})
    if facts.get("product_exit_complete"):
        status = "completed"
    elif product and blocked:
        status = "partially_blocked"
    elif product:
        status = "progressed"
    elif facts.get("frontier_closure_status") == "complete" and classes <= WAIT_CLASSES:
        status = "waiting"
    else:
        status = "progressed"
    return status, actions


def derive_integration(facts: dict[str, Any]) -> str | None:
    if facts.get("current_delivery_action"):
        return "continue_delivery"
    if facts.get("systemic_invariant"):
        ready = not writer_admission_errors(facts)
        return "start_writer" if ready and facts.get("closure_status") == "complete" and not closure_errors(facts.get("closure")) else "hold_before_writer"
    if facts.get("existing_unit"):
        return "new_unit" if facts.get("scope_change") else "same_unit"
    if facts.get("retrospective"):
        trigger = facts.get("retrospective")
        if trigger not in RETROSPECTIVE_TRIGGERS:
            return "continue_delivery"
        if facts.get("root_cause_target") in {"project", "planning"}:
            return "continue_delivery"
        if facts.get("root_cause_target") not in {"skill", "platform"} or feedback_fact_errors(facts):
            return "continue_delivery"
        if facts.get("feedback_redaction_safe") is not True:
            return "deferred_private"
        if facts.get("skill_identity_match") is not True or facts.get("canonical_repository_match") is not True:
            return "deferred_private"
        if facts.get("feedback_write_action") not in FEEDBACK_ACTIONS | {None}:
            return "deferred_private"
        if facts.get("feedback_dedupe_complete") is not True:
            return "candidate"
        if facts.get("github_feedback_capability_available") is not True:
            return "candidate"
        if facts.get("existing_feedback_issue"):
            if not facts.get("feedback_write_succeeded"):
                return "comment_existing" if facts.get("github_feedback_capability_available") is True else "candidate"
        if facts.get("feedback_write_succeeded"):
            expected_action = "add_comment" if facts.get("existing_feedback_issue") else "create_issue"
            complete = (
                facts.get("feedback_write_action") == expected_action
                and real_locator(facts.get("feedback_submission_locator"))
                and facts.get("feedback_readback_verified") is True
                and facts.get("skill_digest_unchanged") is True
            )
            return "submitted" if complete else "candidate"
        if facts.get("feedback_write_attempted"):
            return "candidate"
        return "create_new_feedback_issue" if facts.get("github_feedback_capability_available") is True else "candidate"
    if facts.get("writer_admission_requested"):
        if facts.get("mandate_complete") and not mandate_errors(facts) and not writer_admission_errors(facts):
            return "admit_unit_writer"
        return None
    if facts.get("mandate_complete") and not mandate_errors(facts):
        return "activate_owner"
    return None


def skill_version(path: Path) -> str | None:
    match = re.search(r"^\s*version:\s*['\"]?([^'\"\s]+)", path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "dev-orchestration" or contract.get("schema_version") != "1.1.0":
        errors.append("共享合同身份或版本错误")
    if contract.get("authority_source") != "tasks-owner":
        errors.append("共享合同权威来源错误")
    if set(contract.get("capabilities", [])) != CAPABILITIES:
        errors.append("共享合同能力集合不完整")
    if set(contract.get("owner_mandate", {}).get("required_fields", [])) != {
        "authority_origin", "scope_kind", "scope_locator", "global_tradeoff_authority"
    }:
        errors.append("Owner 委任字段不完整")
    cannot_reset = set(contract.get("unit_identity", {}).get("cannot_reset_by", []))
    if not {"file", "path", "pull_request", "branch", "head", "reviewer", "execution_generation"} <= cannot_reset:
        errors.append("Unit 身份仍可被实现载体错误重置")
    sparse = contract.get("owner_sparse_delta", {})
    if not {"commit", "test_passed", "review_started", "heartbeat", "thread_active"} <= set(sparse.get("forbidden_kinds", [])):
        errors.append("稀疏增量仍允许日常工程噪声")
    if set(contract.get("pmo_admission", {}).get("required_fields", [])) != PMO_ADMISSION_FIELDS:
        errors.append("PMO 准入字段不完整")
    unit_fields = set(contract.get("unit_identity", {}).get("required_fields", []))
    if set(contract.get("writer_admission", {}).get("required_unit_identity_fields", [])) != unit_fields:
        errors.append("writer 准入没有复用唯一 Unit 身份")
    closure = contract.get("systemic_invariant_closure", {})
    if not {"required_fields", "surface_required_fields", "surface_status", "closure_status"} <= set(closure):
        errors.append("系统性闭包机器 schema 不完整")
    for skill, compatibility in contract.get("compatible_skills", {}).items():
        if set(compatibility) != {"tested_artifact_version", "minimum_compatible_version", "required_contract_schema_major"}:
            errors.append(f"{skill} 的发布版本与兼容版本语义混淆")
            continue
        tested = semver(compatibility["tested_artifact_version"])
        minimum = semver(compatibility["minimum_compatible_version"])
        if tested is None or minimum is None or not version_is_compatible(compatibility["tested_artifact_version"], compatibility):
            errors.append(f"{skill} 的最低兼容版本无效")
        if compatibility["required_contract_schema_major"] != 1:
            errors.append(f"{skill} 的合同主版本不兼容")
    frontier = contract.get("product_frontier", {})
    if (
        set(frontier.get("required_fields", [])) != {"product_exit_locators", "gaps", "frontier_closure_status"}
        or
        set(frontier.get("classifications", [])) != FRONTIER_CLASSES
        or set(frontier.get("owner_actionable_classifications", [])) != OWNER_ACTIONABLE_CLASSES
        or set(frontier.get("gap_required_fields", [])) != GAP_REQUIRED_FIELDS
        or set(frontier.get("waiting_proof_required_fields", [])) != WAITING_PROOF_FIELDS
        or set(frontier.get("whole_cycle_wait_allowed_classifications", [])) != WAIT_CLASSES
        or set(frontier.get("closure_status", [])) != {"complete", "incomplete"}
        or set(frontier.get("recompute_triggers", [])) != {
            "user_correction", "unit_merge_or_closeout", "dependency_resolution", "owner_terminal",
            "waiting_proof_invalidation", "long_lived_single_writer_with_unfinished_exit", "deep_audit",
        }
    ):
        errors.append("产品前沿闭包合同不完整")
    retrospective = contract.get("execution_retrospective", {})
    if (
        set(retrospective.get("triggers", [])) != RETROSPECTIVE_TRIGGERS
        or set(retrospective.get("root_cause_targets", [])) != {"project", "planning", "skill", "platform"}
        or set(retrospective.get("candidate_required_fields", [])) != RETROSPECTIVE_CANDIDATE_FIELDS
        or retrospective.get("ordering") != [
            "current_product_recovery", "frontier_or_owner_correction", "retrospective",
            "root_cause_classification", "feedback_candidate",
        ]
        or retrospective.get("explicit_skill_correction_requires_repetition") is not False
        or retrospective.get("heartbeat_is_recovery_only") is not True
    ):
        errors.append("自主执行复盘合同不完整")
    feedback = contract.get("skill_feedback", {})
    required_feedback = {
        "canonical_repositories", "canonical_issue_form", "allowed_actions", "forbidden_actions",
        "write_actions",
        "submission_preconditions", "core_semantic_fields", "fingerprint_fields", "fingerprint_forbidden_fields",
        "fingerprint_occurrence_required_fields", "new_issue_occurrence",
        "occurrence_comment_fields", "checkpoint_fields", "submission_required_fields", "legacy_authority_input",
        "failure_status",
        "api_body_must_be_explicit", "issue_is_only_long_term_retrospective_body",
        "does_not_change_product_semantic_revision", "does_not_change_current_skill_digest",
    }
    if not required_feedback <= set(feedback):
        errors.append("Skill 反馈合同不完整")
    elif set(feedback.get("allowed_actions", [])) != FEEDBACK_ACTIONS:
        errors.append("Skill 反馈动作 allowlist 错误")
    elif set(feedback.get("write_actions", [])) != FEEDBACK_WRITE_ACTIONS:
        errors.append("Skill 反馈写入动作集合错误")
    elif feedback.get("canonical_repositories") != {
        "pmo": "MC-and-his-Agents/MC-AGENT-KIT", "tasks-owner": "MC-and-his-Agents/MC-AGENT-KIT",
    }:
        errors.append("Skill 反馈 canonical repository 错误")
    elif set(feedback.get("forbidden_actions", [])) != FEEDBACK_FORBIDDEN_ACTIONS:
        errors.append("Skill 反馈 forbidden actions 不完整")
    elif set(feedback.get("submission_preconditions", [])) != FEEDBACK_PRECONDITIONS:
        errors.append("Skill 反馈提交前置条件漂移或重新引入逐次授权")
    elif set(feedback.get("core_semantic_fields", [])) != CORE_FEEDBACK_FIELDS:
        errors.append("Skill 反馈核心语义字段错误")
    elif set(feedback.get("fingerprint_fields", [])) != FINGERPRINT_FIELDS:
        errors.append("Skill 反馈稳定 fingerprint 字段错误")
    elif set(feedback.get("fingerprint_occurrence_required_fields", [])) != {"fingerprint", "occurrence"} or feedback.get("new_issue_occurrence") != "first_occurrence":
        errors.append("Skill 反馈首次 occurrence 合同错误")
    elif not {"branch", "pull_request", "head", "owner", "unit", "execution_generation", "heartbeat"} <= set(feedback.get("fingerprint_forbidden_fields", [])):
        errors.append("Skill 反馈 fingerprint 会受易变执行身份污染")
    elif set(feedback.get("occurrence_comment_fields", [])) != {"source_locator", "product_impact", "current_resolution", "root_cause_delta", "regression_delta"}:
        errors.append("Skill 反馈 occurrence 字段错误")
    elif set(feedback.get("checkpoint_fields", [])) != {"feedback_fingerprint", "feedback_issue_locator", "last_occurrence_locator", "feedback_status", "next_action"}:
        errors.append("Skill 反馈 checkpoint 复制了长期正文")
    elif set(feedback.get("feedback_status", [])) != FEEDBACK_STATUSES or set(feedback.get("feedback_target", [])) != FEEDBACK_TARGETS:
        errors.append("Skill 反馈状态或目标枚举不完整")
    elif set(feedback.get("submission_required_fields", [])) != SUBMISSION_FIELDS:
        errors.append("Skill 反馈 submitted readback 门不完整")
    elif feedback.get("failure_status") != {
        "candidate": ["dedupe_incomplete", "tool_unavailable", "write_failed", "readback_unavailable"],
        "deferred_private": ["redaction_unsafe", "canonical_repository_mismatch", "skill_identity_mismatch", "action_not_allowed"],
    }:
        errors.append("Skill 反馈失败状态未 fail closed 或误把暂时失败归为隐私延期")
    elif feedback.get("legacy_authority_input") != "ignored_for_canonical_repository; non-canonical writes use ordinary user authorization":
        errors.append("旧反馈授权输入的兼容语义错误")
    elif not all(feedback.get(field) is True for field in (
        "api_body_must_be_explicit", "issue_is_only_long_term_retrospective_body",
        "does_not_change_product_semantic_revision", "does_not_change_current_skill_digest",
    )):
        errors.append("Skill 反馈错误地改变产品或运行版本")
    return errors


def feedback_form_errors(contract: dict[str, Any], text: str) -> list[str]:
    feedback = contract["skill_feedback"]
    body = re.search(r"(?m)^body:\s*$", text)
    if not body:
        return ["Skill feedback Form 缺少 body"]
    body_text = text[body.end():]
    if re.search(r"(?m)^[a-zA-Z_][a-zA-Z0-9_-]*:\s*", body_text):
        return ["Skill feedback Form 控件逃逸到 body 之外"]
    blocks = re.split(r"(?m)(?=^  - type:)", body_text)
    controls: dict[str, str] = {}
    for block in blocks:
        kind = re.search(r"(?m)^  - type:\s*([a-z0-9_-]+)\s*$", block)
        if not kind or kind.group(1) == "markdown":
            continue
        identifier = re.search(r"(?m)^ {4}id:\s*([a-z0-9_-]+)\s*$", block)
        if not identifier or identifier.group(1) in controls:
            return ["Skill feedback Form 控件缺少唯一直接 id"]
        controls[identifier.group(1)] = block
    form_ids = list(controls)
    if len(form_ids) != len(set(form_ids)):
        return ["Skill feedback Form 存在重复字段"]
    if set(form_ids) != set(feedback["core_semantic_fields"]):
        return ["Skill feedback Form 与机器 schema 的核心语义字段漂移"]
    if any(not re.search(r"(?m)^ {4}validations:\s*\n {6}required:\s*true\s*$", block) for block in controls.values()):
        return ["Skill feedback Form 的核心语义字段必须全部必填"]
    trigger_options = set(re.findall(r"(?m)^ {8}-\s*(.+?)\s*$", controls.get("retrospective_trigger", "")))
    if trigger_options != set(contract["execution_retrospective"]["triggers"]):
        return ["Skill feedback Form 的 retrospective trigger 投影不完整"]
    affected_options = set(re.findall(r"(?m)^ {8}-\s*(.+?)\s*$", controls.get("affected_skill", "")))
    if affected_options != {"pmo", "tasks-owner", "platform / host"}:
        return ["Skill feedback Form 的 affected skill 投影不完整"]
    if feedback["canonical_issue_form"] != str(FEEDBACK_FORM.relative_to(ROOT)):
        return ["Skill feedback Form locator 与机器合同不一致"]
    if "dev-orchestration-contract.json" not in text:
        return ["Skill feedback Form 未声明机器 schema 权威"]
    return []


def validate_files(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for skill in ("pmo", "tasks-owner"):
        skill_dir = ROOT / f"skills/dev/{skill}"
        manifest = json.loads((skill_dir / "manifest.json").read_text(encoding="utf-8"))
        expected = contract["compatible_skills"][skill]["tested_artifact_version"]
        if manifest.get("version") != expected or skill_version(skill_dir / "SKILL.md") != expected:
            errors.append(f"{skill} 的入口、manifest 与本次发布候选版本不一致")
    combined = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in (
        "skills/dev/pmo/SKILL.md", "skills/dev/tasks-owner/SKILL.md",
        "skills/dev/tasks-owner/references/governance.md",
    ))
    for locator in ("dev-orchestration-contract.json", "codex-app.md"):
        if locator not in combined:
            errors.append(f"入口无法发现 {locator}")
    if len(list((ROOT / "skills/dev").glob("*/references/dev-orchestration-contract.json"))) != 1:
        errors.append("跨 Skill 合同必须只有一个权威文件")
    if len(list((ROOT / "skills/dev").glob("*/references/codex-app.md"))) != 1:
        errors.append("Codex App 平台事实必须只有一个权威文件")
    forbidden = re.compile(r"gpt-5\.6|codex_app__|wait_agent|10_000|60_000|24 小时|\d+\s*分钟")
    for skill in ("pmo", "tasks-owner"):
        for path in (ROOT / f"skills/dev/{skill}").rglob("*.md"):
            if path == PLATFORM or any(part in {"evals", "reports"} for part in path.parts):
                continue
            if forbidden.search(path.read_text(encoding="utf-8")):
                errors.append(f"平台参数必须只出现在 codex-app.md：{path.relative_to(ROOT)}")
    return errors


def closure_errors(closure: Any) -> list[str]:
    if not isinstance(closure, dict):
        return ["系统性闭包必须是对象"]
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))["systemic_invariant_closure"]
    required = set(schema["required_fields"])
    if not required <= set(closure):
        return ["系统性闭包缺少范围、顺序、失败规则、适用面或摘要"]
    if any(not isinstance(closure.get(key), str) or not closure[key].strip() for key in required - {"surfaces"}):
        return ["系统性闭包的说明或摘要不能为空"]
    if closure.get("status") != "ready":
        return ["用于 writer 准入的系统性闭包必须 ready"]
    surfaces = closure.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        return ["系统性闭包没有适用面"]
    surface_fields = set(schema["surface_required_fields"])
    for surface in surfaces:
        if not isinstance(surface, dict) or not surface_fields <= set(surface):
            return ["系统性闭包的适用面证据不完整"]
        if surface.get("status") not in schema["surface_status"]:
            return ["系统性闭包的适用面状态无效"]
        for field in surface_fields:
            if not real_locator(surface.get(field)):
                return ["系统性闭包的适用面证据不完整"]
    return []


def mandate_errors(facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if facts.get("authority_origin") not in {"user", "pmo"}:
        errors.append("Owner 授权来源无效")
    if facts.get("scope_kind") not in {"project_scope", "work_item"}:
        errors.append("Owner 范围类型无效")
    if not isinstance(facts.get("scope_locator"), str) or not facts["scope_locator"].strip():
        errors.append("Owner 缺少范围定位")
    if "global_tradeoff_authority" not in facts or not isinstance(facts.get("global_tradeoff_authority"), str) or not facts["global_tradeoff_authority"].strip():
        errors.append("Owner 缺少全局取舍授权边界")
    if facts.get("authority_origin") == "pmo":
        admission = facts.get("pmo_admission")
        if not isinstance(admission, dict) or not PMO_ADMISSION_FIELDS <= set(admission):
            errors.append("PMO 准入 envelope 不完整")
        else:
            if admission.get("contract_id") != "dev-orchestration" or admission.get("schema_version") != "1.1.0":
                errors.append("PMO 准入 envelope 使用了不兼容的共享合同")
            for field in PMO_ADMISSION_FIELDS:
                value = admission.get(field)
                if field == "repair_budget":
                    if not isinstance(value, dict) or not value:
                        errors.append("PMO 准入缺少修复预算")
                elif field in {"allowed_scope", "excluded_scope"}:
                    if not isinstance(value, list) or not value:
                        errors.append(f"PMO 准入 {field} 不能为空")
                elif not isinstance(value, str) or not value.strip():
                    errors.append(f"PMO 准入 {field} 不能为空")
    return errors


def writer_admission_errors(facts: dict[str, Any]) -> list[str]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    fields = set(contract["writer_admission"]["required_unit_identity_fields"])
    identity = facts.get("unit_identity")
    if facts.get("authority_origin") == "pmo" and isinstance(facts.get("pmo_admission"), dict):
        identity = facts["pmo_admission"]
    if not isinstance(identity, dict):
        return ["writer 准入缺少 Unit 身份"]
    return [f"writer 准入缺少 {field}" for field in fields if not real_locator(identity.get(field))]


def validate_cycles(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for row in rows:
        line = row.pop("_line", "?")
        if set(row) != {"schema_version", "id", "facts", "expected"} or row.get("schema_version") != "pmo-cycle.v1":
            errors.append(f"cycle line {line}: 结构错误")
            continue
        if row["id"] in ids:
            errors.append(f"cycle line {line}: ID 重复")
        ids.add(row["id"])
        errors.extend(f"cycle line {line}: {error}" for error in cycle_fact_errors(row["facts"]))
        derived = derive_cycle(row["facts"])
        expected = row["expected"]
        if derived != (expected.get("cycle_status"), expected.get("actions")):
            errors.append(f"cycle line {line}: 期望与事实不一致")
        actions = expected.get("actions", [])
        if actions != sorted(actions, key=ACTION_ORDER.index):
            errors.append(f"cycle line {line}: 产品动作和治理动作顺序错误")
    if {row.get("expected", {}).get("cycle_status") for row in rows} != {"progressed", "partially_blocked", "waiting", "completed"}:
        errors.append("PMO 周期状态覆盖不完整")
    return errors


def validate_integration(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    outcomes: set[str] = set()
    for row in rows:
        line = row.pop("_line", "?")
        if set(row) != {"schema_version", "id", "facts", "expected"} or row.get("schema_version") != "dev-orchestration-case.v1":
            errors.append(f"integration line {line}: 结构错误")
            continue
        if row["id"] in ids:
            errors.append(f"integration line {line}: ID 重复")
        ids.add(row["id"])
        outcomes.add(row["expected"])
        errors.extend(f"integration line {line}: {error}" for error in feedback_fact_errors(row["facts"]))
        if derive_integration(row["facts"]) != row["expected"]:
            errors.append(f"integration line {line}: 期望与事实不一致")
        if row["expected"] in {"activate_owner", "admit_unit_writer"}:
            errors.extend(f"integration line {line}: {error}" for error in mandate_errors(row["facts"]))
        if row["expected"] == "admit_unit_writer":
            errors.extend(f"integration line {line}: {error}" for error in writer_admission_errors(row["facts"]))
        if row["facts"].get("systemic_invariant") and row["facts"].get("closure_status") == "complete":
            errors.extend(f"integration line {line}: {error}" for error in closure_errors(row["facts"].get("closure")))
    required = {
        "activate_owner", "admit_unit_writer", "same_unit", "new_unit", "hold_before_writer",
        "start_writer", "deferred_private", "candidate", "comment_existing",
        "create_new_feedback_issue", "submitted", "continue_delivery",
    }
    if not required <= outcomes:
        errors.append("跨 Skill 场景覆盖不完整")
    return errors


def validate_triggers() -> list[str]:
    errors: list[str] = []
    owner = json.loads(OWNER_TRIGGERS.read_text(encoding="utf-8"))
    pmo = json.loads(PMO_TRIGGERS.read_text(encoding="utf-8"))
    for name, document in (("tasks-owner", owner), ("pmo", pmo)):
        groups = [document.get(key, []) for key in ("should_trigger", "should_not_trigger", "near_neighbor")]
        if any(not isinstance(group, list) or not group for group in groups):
            errors.append(f"{name} 触发评测三类样本不完整")
            continue
        texts = [case.get("text") for group in groups for case in group]
        if any(not isinstance(text, str) or not text.strip() for text in texts) or len(texts) != len(set(texts)):
            errors.append(f"{name} 触发样本存在空值或重复")
    if "pmo_admission" not in {case.get("family") for case in owner.get("should_trigger", [])}:
        errors.append("Tasks Owner 缺少 PMO 准入触发样本")
    pmo_negative = {case.get("family") for case in pmo.get("should_not_trigger", [])}
    if not {"single_unit_owner", "one_off_implementation", "skill_maintenance"} <= pmo_negative:
        errors.append("PMO 对邻近任务的拒绝样本不完整")
    return errors


def run_existing(self_test: bool) -> list[str]:
    errors: list[str] = []
    suffix = ["--self-test"] if self_test else []
    for name in ("validate-pmo-trajectories.py", "validate-tasks-owner-trajectories.py"):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / name), *suffix], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode:
            errors.append(result.stdout.strip())
    return errors


def validate() -> list[str]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return (
        validate_contract(contract) + validate_files(contract)
        + feedback_form_errors(contract, FEEDBACK_FORM.read_text(encoding="utf-8"))
        + validate_cycles(load_jsonl(CYCLES)) + validate_integration(load_jsonl(INTEGRATION))
        + validate_triggers()
        + run_existing(False)
    )


def self_test() -> list[str]:
    failures: list[str] = []
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    bad = copy.deepcopy(contract)
    bad["capabilities"].remove("owner_sparse_delta")
    if not validate_contract(bad):
        failures.append("缺失共享能力的变异未被拒绝")
    for label, mutate in (
        ("准入字段", lambda value: value["pmo_admission"].update(required_fields=[])),
        ("反馈合同", lambda value: value.update(skill_feedback={})),
        ("复盘 trigger", lambda value: value["execution_retrospective"]["triggers"].remove("explicit_skill_correction")),
        ("根因分类", lambda value: value["execution_retrospective"]["root_cause_targets"].remove("platform")),
        ("反馈 allowlist", lambda value: value["skill_feedback"]["allowed_actions"].append("create_pull_request")),
        ("反馈写入动作", lambda value: value["skill_feedback"]["write_actions"].append("read_issue")),
        ("逐次反馈授权", lambda value: value["skill_feedback"]["submission_preconditions"].append("skill_feedback_authority")),
        ("canonical Skill 映射", lambda value: value["skill_feedback"]["canonical_repositories"].pop("pmo")),
        ("反馈状态", lambda value: value["skill_feedback"]["feedback_status"].remove("candidate")),
        ("fingerprint 字段", lambda value: value["skill_feedback"]["fingerprint_fields"].append("head")),
        ("首次 occurrence", lambda value: value["skill_feedback"].update(new_issue_occurrence="unknown")),
        ("反馈失败状态", lambda value: value["skill_feedback"]["failure_status"]["candidate"].remove("write_failed")),
        ("权威来源", lambda value: value.update(authority_source="pmo")),
        ("最低兼容版本", lambda value: value["compatible_skills"]["pmo"].update(minimum_compatible_version="0.11.0")),
    ):
        bad_contract = copy.deepcopy(contract)
        mutate(bad_contract)
        if not validate_contract(bad_contract):
            failures.append(f"破坏{label}的变异未被拒绝")
    pmo_compatibility = contract["compatible_skills"]["pmo"]
    if not version_is_compatible("0.10.1", pmo_compatibility):
        failures.append("高于最低版本的兼容补丁版本被错误拒绝")
    if version_is_compatible("0.9.9", pmo_compatibility):
        failures.append("低于最低版本的 Skill 被错误接受")
    cycles = load_jsonl(CYCLES)
    bad_cycles = copy.deepcopy(cycles)
    next(row for row in bad_cycles if row["id"] == "merge-drift-and-successor")["expected"]["actions"].reverse()
    if not validate_cycles(bad_cycles):
        failures.append("动作乱序变异未被拒绝")
    for label, mutate in (
        ("等待证明缺字段", lambda facts: facts["gaps"][0]["waiting_proof"].pop("external_condition")),
        ("陈旧等待证明", lambda facts: facts["gaps"][0]["waiting_proof"].update(freshness="stale")),
        ("前沿闭包不完整", lambda facts: facts.update(frontier_closure_status="incomplete")),
        ("重复差距", lambda facts: facts["gaps"].append(copy.deepcopy(facts["gaps"][0]))),
        ("等待伪装为无 Owner", lambda facts: facts["gaps"][0].update(waiting_proof=None)),
    ):
        bad_wait = copy.deepcopy(cycles)
        wait_case = next(row for row in bad_wait if row["id"] == "all-gaps-have-wait-proof")
        mutate(wait_case["facts"])
        if not validate_cycles(bad_wait):
            failures.append(f"{label}变异未被拒绝")
    missing_exit_gap = copy.deepcopy(cycles)
    multi_exit = next(row for row in missing_exit_gap if row["id"] == "multi-exit-closure")
    multi_exit["facts"]["gaps"].pop()
    if not validate_cycles(missing_exit_gap):
        failures.append("漏掉整个产品出口 gap 的闭包变异未被拒绝")
    integration = load_jsonl(INTEGRATION)
    bad_integration = copy.deepcopy(integration)
    next(row for row in bad_integration if row["id"] == "head-change-keeps-unit")["expected"] = "new_unit"
    if not validate_integration(bad_integration):
        failures.append("实现载体重置 Unit 的变异未被拒绝")
    for field in ("scope_locator", "global_tradeoff_authority"):
        bad_mandate = copy.deepcopy(integration)
        direct = next(row for row in bad_mandate if row["id"] == "direct-user-mandate")
        direct["facts"].pop(field)
        if not validate_integration(bad_mandate):
            failures.append(f"缺少 {field} 的 Owner 准入变异未被拒绝")
    for case_id, identity_key in (("direct-user-writer-admission", "unit_identity"), ("pmo-unit-writer-admission", "pmo_admission")):
        for field in json.loads(CONTRACT.read_text(encoding="utf-8"))["writer_admission"]["required_unit_identity_fields"]:
            bad_identity = copy.deepcopy(integration)
            writer_case = next(row for row in bad_identity if row["id"] == case_id)
            writer_case["facts"][identity_key].pop(field)
            if not validate_integration(bad_identity):
                failures.append(f"{case_id} 缺少 {field} 的 writer 准入变异未被拒绝")
    bad_admission = copy.deepcopy(integration)
    pmo_case = next(row for row in bad_admission if row["id"] == "pmo-work-item-mandate")
    pmo_case["facts"]["pmo_admission"].pop("scope_locator")
    if not validate_integration(bad_admission):
        failures.append("缺少范围定位的 PMO 准入变异未被拒绝")
    bad_admission_version = copy.deepcopy(integration)
    next(row for row in bad_admission_version if row["id"] == "pmo-work-item-mandate")["facts"]["pmo_admission"]["schema_version"] = "1.0.0"
    if not validate_integration(bad_admission_version):
        failures.append("旧共享合同版本的 PMO 准入变异未被拒绝")
    closure_schema = json.loads(CONTRACT.read_text(encoding="utf-8"))["systemic_invariant_closure"]
    for field in closure_schema["required_fields"]:
        bad_closure = copy.deepcopy(integration)
        closure_case = next(row for row in bad_closure if row["id"] == "systemic-closure-complete")
        closure_case["facts"]["closure"].pop(field)
        if not validate_integration(bad_closure):
            failures.append(f"缺少 {field} 的闭包变异未被拒绝")
    for field in closure_schema["surface_required_fields"]:
        bad_closure = copy.deepcopy(integration)
        closure_case = next(row for row in bad_closure if row["id"] == "systemic-closure-complete")
        closure_case["facts"]["closure"]["surfaces"][0].pop(field)
        if not validate_integration(bad_closure):
            failures.append(f"缺少 {field} 的闭包适用面变异未被拒绝")
    bad_feedback = copy.deepcopy(cycles)
    feedback_case = next(row for row in bad_feedback if row["id"] == "delivery-before-skill-feedback")
    feedback_case["facts"]["canonical_repository_match"] = False
    if not validate_cycles(bad_feedback):
        failures.append("canonical 仓库不匹配的提交变异未被拒绝")
    for label, mutate in (
        ("反馈提交 locator", lambda facts: facts.pop("feedback_submission_locator")),
        ("反馈提交回读", lambda facts: facts.update(feedback_readback_verified=False)),
        ("Skill digest 保持", lambda facts: facts.update(skill_digest_unchanged=False)),
        ("反馈目标仓库", lambda facts: facts.update(canonical_repository_match=False)),
        ("反馈去重", lambda facts: facts.update(feedback_dedupe_complete=False)),
        ("GitHub feedback capability", lambda facts: facts.update(github_feedback_capability_available=False)),
    ):
        bad_submission = copy.deepcopy(integration)
        submission = next(row for row in bad_submission if row["id"] == "new-feedback-submitted")
        mutate(submission["facts"])
        if not validate_integration(bad_submission):
            failures.append(f"缺少{label}的反馈提交变异未被拒绝")
    for label, mutate in (
        ("产品动作优先", lambda facts: facts.update(product_actions_complete=False)),
        ("根因枚举", lambda facts: facts.update(root_cause_target="unclassified")),
        ("candidate 字段", lambda facts: facts["feedback_candidate"].pop("product_impact")),
        ("API body 字段", lambda facts: facts["feedback_api_body"].pop("product_impact")),
        ("Skill 根因目标", lambda facts: facts["feedback_candidate"].update(affected_skill="platform")),
        ("fingerprint 易变字段", lambda facts: facts["feedback_candidate"]["fingerprint_seed"].update(head="abc")),
        ("fingerprint 根因", lambda facts: facts["feedback_candidate"]["fingerprint_seed"].update(incident_root_cause_class="platform")),
        ("首次 occurrence", lambda facts: facts["feedback_api_body"]["fingerprint_occurrence"].pop("occurrence")),
        ("dedupe 结果", lambda facts: facts.pop("existing_feedback_issue")),
    ):
        bad_payload = copy.deepcopy(integration)
        payload_case = next(row for row in bad_payload if row["id"] == "explicit-pmo-correction-no-per-run-authority")
        mutate(payload_case["facts"])
        if not validate_integration(bad_payload):
            failures.append(f"破坏{label}的反馈变异未被拒绝")
    bad_occurrence = copy.deepcopy(integration)
    next(row for row in bad_occurrence if row["id"] == "existing-feedback-occurrence")["facts"]["feedback_occurrence"].pop("source_locator")
    if not validate_integration(bad_occurrence):
        failures.append("缺少 occurrence 字段的反馈变异未被拒绝")
    bad_platform_target = copy.deepcopy(integration)
    next(row for row in bad_platform_target if row["id"] == "redaction-failed")["facts"]["feedback_candidate"]["affected_skill"] = "pmo"
    if not validate_integration(bad_platform_target):
        failures.append("platform 根因错误定位到 pmo 的变异未被拒绝")
    form_text = FEEDBACK_FORM.read_text(encoding="utf-8")
    if not feedback_form_errors(contract, form_text.replace("id: product_impact", "id: product_value")):
        failures.append("Form 与机器 schema 漂移的变异未被拒绝")
    if not feedback_form_errors(contract, form_text.replace("required: true", "required: false", 1)):
        failures.append("Form 核心必填字段失效的变异未被拒绝")
    misplaced_required = form_text.replace("    validations:\n      required: true", "    attributes:\n      required: true", 1)
    if not feedback_form_errors(contract, misplaced_required):
        failures.append("Form required 脱离 validations 的变异未被拒绝")
    forged_form = re.sub(
        r"(?ms)^  - type: textarea\n    id: product_impact\n.*?(?=^  - type:|\Z)",
        "",
        form_text,
    ).replace("value: |\n", "value: |\n        id: product_impact\n        required: true\n", 1)
    if not feedback_form_errors(contract, forged_form):
        failures.append("藏在 markdown 中的伪 Form 字段绕过了结构校验")
    body_prefix, body_text = form_text.split("body:\n", 1)
    first_control = body_text.index("  - type: dropdown")
    escaped_controls = f"{body_prefix}body:\n{body_text[:first_control]}x_controls:\n{body_text[first_control:]}"
    if not feedback_form_errors(contract, escaped_controls):
        failures.append("逃逸到 body 外的 Form 控件绕过了结构校验")
    for case_id, wrong_action in (
        ("existing-feedback-occurrence", "create_issue"),
        ("explicit-pmo-correction-no-per-run-authority", "add_comment"),
        ("existing-feedback-occurrence", "search_issue"),
        ("explicit-pmo-correction-no-per-run-authority", "read_issue"),
    ):
        bad_action = copy.deepcopy(integration)
        next(row for row in bad_action if row["id"] == case_id)["facts"]["feedback_write_action"] = wrong_action
        if not validate_integration(bad_action):
            failures.append("与 dedupe 结果不一致的反馈动作未被拒绝")
    fingerprint_facts = {
        "affected_skill": "pmo", "incident_root_cause_class": "skill",
        "governing_behavior_category": "frontier-closure", "platform_contract_major": 1,
        "branch": "one", "head": "abc", "owner": "owner-a", "heartbeat": "first",
    }
    changed_identity = dict(fingerprint_facts, branch="two", head="def", owner="owner-b", heartbeat="second")
    if feedback_fingerprint(fingerprint_facts, contract) != feedback_fingerprint(changed_identity, contract):
        failures.append("稳定 fingerprint 被 branch/head/Owner/Heartbeat 污染")
    return failures + run_existing(True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        errors = self_test() if args.self_test else validate()
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f"error: {error}")
    if not errors:
        print("双层编排自检通过。" if args.self_test else "双层编排校验通过。")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())

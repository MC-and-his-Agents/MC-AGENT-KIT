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
CYCLES = ROOT / "skills/dev/pmo/evals/cycle_cases.jsonl"
INTEGRATION = ROOT / "skills/dev/tasks-owner/evals/dev_orchestration_cases.jsonl"
OWNER_TRIGGERS = ROOT / "skills/dev/tasks-owner/evals/trigger_cases.json"
PMO_TRIGGERS = ROOT / "skills/dev/pmo/evals/trigger_cases.json"
CAPABILITIES = {
    "pmo_admission", "owner_sparse_delta", "single_scope_owner_execution",
    "bounded_finding_fix", "delivery_closeout", "bounded_execution_retrospective",
    "skill_feedback_candidate",
}
PMO_ADMISSION_FIELDS = {
    "contract_id", "schema_version", "authority_origin", "scope_kind", "scope_locator",
    "planning_truth_locator", "product_goal", "expected_contribution", "acceptance_locator",
    "product_exit_locator", "governing_invariant_locator", "convergence_chain_locator",
    "ownership_boundary_locator", "allowed_scope", "excluded_scope", "carrier_locator",
    "target_head_locator", "decision_boundary_locator", "repair_budget",
}
FEEDBACK_AUTHORITY_FIELDS = {
    "skill_feedback_authority_locator", "user_source_locator", "target_repository",
    "allowed_actions", "allowed_skill_scope", "redaction_policy", "dedupe_policy",
    "expiry", "invalidation",
}
ACTION_ORDER = [
    "closeout_unit", "correct_drift", "route_delta", "shape_work_item",
    "create_or_wake_owner", "request_user_decision", "record_evidenced_wait",
    "record_skill_feedback_candidate", "submit_or_update_skill_feedback",
]
GAP_FIELDS = (
    "remaining_gap_ids", "executable_gap_ids", "user_decision_gap_ids",
    "evidenced_wait_gap_ids", "unshaped_gap_ids",
)


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


def cycle_fact_errors(facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    gap_sets: dict[str, set[str]] = {}
    for field in GAP_FIELDS:
        value = facts.get(field)
        if not isinstance(value, list) or any(not real_locator(item) for item in value) or len(value) != len(set(value)):
            errors.append(f"{field} 必须是无重复的真实差距 ID 列表")
            continue
        gap_sets[field] = set(value)
    if len(gap_sets) != len(GAP_FIELDS):
        return errors
    remaining = gap_sets["remaining_gap_ids"]
    classified = set().union(*(gap_sets[field] for field in GAP_FIELDS[1:]))
    if not classified <= remaining:
        errors.append("差距分类包含不在 remaining_gap_ids 中的 ID")
    if gap_sets["user_decision_gap_ids"] & gap_sets["evidenced_wait_gap_ids"]:
        errors.append("同一差距不能同时请求用户决策和记录普通等待")
    if facts.get("product_exit_complete"):
        if remaining:
            errors.append("产品出口完成时不能仍有剩余差距")
    elif not remaining:
        errors.append("产品出口未完成时必须列出剩余差距")
    has_product_action = any((
        facts.get("merge_verified"), facts.get("drift_detected"), facts.get("route_delta_ready"),
        gap_sets["unshaped_gap_ids"], gap_sets["executable_gap_ids"],
    ))
    if not facts.get("product_exit_complete") and not has_product_action:
        covered = gap_sets["user_decision_gap_ids"] | gap_sets["evidenced_wait_gap_ids"]
        if covered != remaining:
            errors.append("没有产品动作时，用户决策或等待证明必须覆盖全部剩余差距")
    return errors


def derive_cycle(facts: dict[str, Any]) -> tuple[str, list[str]]:
    actions: list[str] = []
    if facts.get("merge_verified"):
        actions.append("closeout_unit")
    if facts.get("drift_detected"):
        actions.append("correct_drift")
    if facts.get("route_delta_ready"):
        actions.append("route_delta")
    if facts.get("unshaped_gap_ids"):
        actions.append("shape_work_item")
    if facts.get("executable_gap_ids"):
        actions.append("create_or_wake_owner")
    if facts.get("user_decision_gap_ids"):
        actions.append("request_user_decision")
    if facts.get("evidenced_wait_gap_ids"):
        actions.append("record_evidenced_wait")
    if facts.get("feedback_candidate"):
        actions.append("record_skill_feedback_candidate")
    if facts.get("feedback_submission_ready") and all(
        facts.get(key) is True
        for key in ("product_actions_complete", "feedback_authority_valid", "feedback_dedupe_complete", "feedback_redaction_safe")
    ):
        actions.append("submit_or_update_skill_feedback")
    product = any(action in ACTION_ORDER[:5] for action in actions)
    blocked = any(action in {"request_user_decision", "record_evidenced_wait"} for action in actions)
    if facts.get("product_exit_complete"):
        status = "completed"
    elif product and blocked:
        status = "partially_blocked"
    elif product:
        status = "progressed"
    else:
        status = "waiting"
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
        if facts.get("retrospective") != "repeated" or facts.get("root_cause_target") == "project":
            return "continue_delivery"
        if facts.get("feedback_authority") != "valid" or facts.get("feedback_redaction_safe") is not True:
            return "deferred_private"
        if facts.get("target_repository_match") is not True:
            return "deferred_private"
        if facts.get("feedback_dedupe_complete") is not True:
            return "candidate"
        if facts.get("existing_feedback_issue"):
            return "comment_existing"
        if facts.get("feedback_create_succeeded"):
            complete = (
                facts.get("feedback_write_action") == "create_issue"
                and real_locator(facts.get("feedback_submission_locator"))
                and facts.get("feedback_readback_verified") is True
                and facts.get("skill_digest_unchanged") is True
            )
            return "submitted" if complete else "candidate"
        if facts.get("feedback_create_attempted"):
            return "candidate"
        return "create_new_feedback_issue" if facts.get("feedback_write_capability") is True else "candidate"
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
    if contract.get("contract_id") != "dev-orchestration" or contract.get("schema_version") != "1.0.0":
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
    feedback = contract.get("skill_feedback", {})
    if not {
        "candidate_fields", "feedback_status", "feedback_target", "authority_required_for",
        "authority_fields", "submission_required_fields", "does_not_change_product_semantic_revision", "does_not_change_current_skill_digest",
    } <= set(feedback):
        errors.append("Skill 反馈合同不完整")
    elif set(feedback.get("authority_fields", [])) != FEEDBACK_AUTHORITY_FIELDS:
        errors.append("Skill 反馈授权字段不完整")
    elif feedback.get("does_not_change_product_semantic_revision") is not True or feedback.get("does_not_change_current_skill_digest") is not True:
        errors.append("Skill 反馈错误地改变产品或运行版本")
    return errors


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
        ("权威来源", lambda value: value.update(authority_source="pmo")),
        ("最低兼容版本", lambda value: value["compatible_skills"]["pmo"].update(minimum_compatible_version="0.10.0")),
    ):
        bad_contract = copy.deepcopy(contract)
        mutate(bad_contract)
        if not validate_contract(bad_contract):
            failures.append(f"破坏{label}的变异未被拒绝")
    pmo_compatibility = contract["compatible_skills"]["pmo"]
    if not version_is_compatible("0.9.1", pmo_compatibility):
        failures.append("高于最低版本的兼容补丁版本被错误拒绝")
    if version_is_compatible("0.8.9", pmo_compatibility):
        failures.append("低于最低版本的 Skill 被错误接受")
    cycles = load_jsonl(CYCLES)
    bad_cycles = copy.deepcopy(cycles)
    bad_cycles[0]["expected"]["actions"].reverse()
    if not validate_cycles(bad_cycles):
        failures.append("动作乱序变异未被拒绝")
    for label, mutate in (
        ("空等待证明", lambda facts: facts.update(evidenced_wait_gap_ids=[])),
        ("未覆盖差距", lambda facts: facts.update(remaining_gap_ids=["gap:external", "gap:unknown"])),
        ("重复决策等待", lambda facts: facts.update(user_decision_gap_ids=["gap:external"])),
        ("等待中可执行差距", lambda facts: facts.update(executable_gap_ids=["gap:external"], evidenced_wait_gap_ids=[])),
    ):
        bad_wait = copy.deepcopy(cycles)
        wait_case = next(row for row in bad_wait if row["id"] == "all-gaps-have-wait-proof")
        mutate(wait_case["facts"])
        if not validate_cycles(bad_wait):
            failures.append(f"{label}变异未被拒绝")
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
    feedback_case["facts"]["feedback_authority_valid"] = False
    if not validate_cycles(bad_feedback):
        failures.append("缺少反馈授权的提交变异未被拒绝")
    for label, mutate in (
        ("反馈提交 locator", lambda facts: facts.pop("feedback_submission_locator")),
        ("反馈提交回读", lambda facts: facts.update(feedback_readback_verified=False)),
        ("Skill digest 保持", lambda facts: facts.update(skill_digest_unchanged=False)),
        ("反馈目标仓库", lambda facts: facts.update(target_repository_match=False)),
        ("反馈去重", lambda facts: facts.update(feedback_dedupe_complete=False)),
    ):
        bad_submission = copy.deepcopy(integration)
        submission = next(row for row in bad_submission if row["id"] == "new-feedback-submitted")
        mutate(submission["facts"])
        if not validate_integration(bad_submission):
            failures.append(f"缺少{label}的反馈提交变异未被拒绝")
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

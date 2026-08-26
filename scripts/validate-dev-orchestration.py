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


def derive_cycle(facts: dict[str, Any]) -> tuple[str, list[str]]:
    actions: list[str] = []
    if facts.get("merge_verified"):
        actions.append("closeout_unit")
    if facts.get("drift_detected"):
        actions.append("correct_drift")
    if facts.get("route_delta_ready"):
        actions.append("route_delta")
    if facts.get("unshaped_gap_count", 0) > 0:
        actions.append("shape_work_item")
    if facts.get("ready_unit_count", 0) > 0:
        actions.append("create_or_wake_owner")
    if facts.get("user_decision_count", 0) > 0:
        actions.append("request_user_decision")
    if facts.get("evidenced_wait_count", 0) > 0:
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
        return "start_writer" if facts.get("closure_status") == "complete" and not closure_errors(facts.get("closure")) else "hold_before_writer"
    if facts.get("existing_unit"):
        return "new_unit" if facts.get("scope_change") else "same_unit"
    if facts.get("retrospective"):
        if facts.get("retrospective") != "repeated" or facts.get("root_cause_target") == "project":
            return "continue_delivery"
        if facts.get("feedback_authority") != "valid" or facts.get("feedback_redaction_safe") is not True:
            return "deferred_private"
        if facts.get("feedback_dedupe_complete") is not True:
            return "candidate"
        return "comment_existing" if facts.get("existing_feedback_issue") else "candidate"
    if facts.get("mandate_complete") and not mandate_errors(facts):
        return "admit"
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
    feedback = contract.get("skill_feedback", {})
    if not {
        "candidate_fields", "feedback_status", "feedback_target", "authority_required_for",
        "authority_fields", "does_not_change_product_semantic_revision", "does_not_change_current_skill_digest",
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
        expected = contract["compatible_skills"][skill]["minimum_version"]
        if manifest.get("version") != expected or skill_version(skill_dir / "SKILL.md") != expected:
            errors.append(f"{skill} 的入口、manifest 与共享合同版本不一致")
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
    required = {"subject", "coverage", "ordering", "failure", "surfaces", "digest"}
    if not required <= set(closure):
        return ["系统性闭包缺少范围、顺序、失败规则、适用面或摘要"]
    if any(not isinstance(closure.get(key), str) or not closure[key].strip() for key in required - {"surfaces"}):
        return ["系统性闭包的说明或摘要不能为空"]
    surfaces = closure.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        return ["系统性闭包没有适用面"]
    surface_fields = {"lifecycle", "variant", "consumer_or_effect", "code_locator", "positive", "negative_or_unavailable", "ordering", "no_side_effect"}
    if any(not isinstance(surface, dict) or not surface_fields <= set(surface) or any(not str(surface.get(key, "")).strip() for key in surface_fields) for surface in surfaces):
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
        if row["expected"] == "admit":
            errors.extend(f"integration line {line}: {error}" for error in mandate_errors(row["facts"]))
        if row["facts"].get("systemic_invariant") and row["facts"].get("closure_status") == "complete":
            errors.extend(f"integration line {line}: {error}" for error in closure_errors(row["facts"].get("closure")))
    required = {"admit", "same_unit", "new_unit", "hold_before_writer", "start_writer", "deferred_private", "comment_existing", "continue_delivery"}
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
    ):
        bad_contract = copy.deepcopy(contract)
        mutate(bad_contract)
        if not validate_contract(bad_contract):
            failures.append(f"破坏{label}的变异未被拒绝")
    cycles = load_jsonl(CYCLES)
    bad_cycles = copy.deepcopy(cycles)
    bad_cycles[0]["expected"]["actions"].reverse()
    if not validate_cycles(bad_cycles):
        failures.append("动作乱序变异未被拒绝")
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
    bad_admission = copy.deepcopy(integration)
    pmo_case = next(row for row in bad_admission if row["id"] == "pmo-work-item-mandate")
    pmo_case["facts"]["pmo_admission"].pop("scope_locator")
    if not validate_integration(bad_admission):
        failures.append("缺少范围定位的 PMO 准入变异未被拒绝")
    bad_closure = copy.deepcopy(integration)
    closure_case = next(row for row in bad_closure if row["id"] == "systemic-closure-complete")
    closure_case["facts"]["closure"]["surfaces"][0].pop("negative_or_unavailable")
    if not validate_integration(bad_closure):
        failures.append("缺少负向证据的闭包变异未被拒绝")
    bad_feedback = copy.deepcopy(cycles)
    feedback_case = next(row for row in bad_feedback if row["id"] == "delivery-before-skill-feedback")
    feedback_case["facts"]["feedback_authority_valid"] = False
    if not validate_cycles(bad_feedback):
        failures.append("缺少反馈授权的提交变异未被拒绝")
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

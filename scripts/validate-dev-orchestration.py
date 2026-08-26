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
    if facts.get("feedback_submission_ready"):
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
        return "start_writer" if facts.get("closure_status") == "complete" else "hold_before_writer"
    if facts.get("existing_unit"):
        return "new_unit" if facts.get("scope_change") else "same_unit"
    if facts.get("retrospective"):
        if facts.get("retrospective") != "repeated" or facts.get("root_cause_target") == "project":
            return "continue_delivery"
        if facts.get("feedback_authority") != "valid":
            return "deferred_private"
        return "comment_existing" if facts.get("existing_feedback_issue") else "candidate"
    if facts.get("mandate_complete") and facts.get("authority_origin") in {"user", "pmo"}:
        return "admit"
    return None


def skill_version(path: Path) -> str | None:
    match = re.search(r"^\s*version:\s*['\"]?([^'\"\s]+)", path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "dev-orchestration" or contract.get("schema_version") != "1.0.0":
        errors.append("共享合同身份或版本错误")
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
    forbidden = re.compile(r"gpt-5\.6|codex_app__|wait_agent|10_000|60_000|24 小时")
    for skill in ("pmo", "tasks-owner"):
        for path in (ROOT / f"skills/dev/{skill}").rglob("*.md"):
            if path == PLATFORM or any(part in {"evals", "reports"} for part in path.parts):
                continue
            if forbidden.search(path.read_text(encoding="utf-8")):
                errors.append(f"平台参数必须只出现在 codex-app.md：{path.relative_to(ROOT)}")
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

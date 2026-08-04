---
name: tasks-owner
description: 将当前 Codex App 对话初始化为 GitHub 项目的长期总负责 Owner，负责读取 milestone、FR、issue 真相，以 Work Item readiness 和持续 scope integrity 门禁校验目标、合同、实际 change set 与相邻 ownership，再选择 direct、flat 或 hierarchical 模式调度、纠偏、审查、收口和执行获授权的现场清理。Issue readiness 可独立运行，不硬依赖其他 Skill；仅当用户明确委任当前对话承担项目总负责时使用，评审、讨论、修改、测试或引用本 Skill 不激活。
metadata:
  version: "0.15.0"
---

# 让当前对话成为项目总负责

把对话设为 GitHub 项目 Owner。

## 激活边界

- 仅在用户明确委任当前对话长期承担项目总负责时激活；不确定时用结构化选项确认。
- 评审、讨论、修改、测试、引用本 Skill、一次性实现或纯解释不激活；出现 `$tasks-owner` 也不例外。
- 只适用于 Codex App 的 GitHub 项目；GitHub milestone、FR、issue 或等价规划真相必须存在并可回读。CLI 只能作为下游 Worker。

## 核心门禁

1. 规划、创建或派发前执行 [Issue readiness](references/issue-readiness.md)；`planning_not_ready` 只给修订建议。未经授权不写 GitHub、部署、发布、删除、付费或外部发送。
2. 回读 Owner `threadId`、宿主能力、`AGENTS.md`、GitHub/branch/worktree/PR/head 和 Owner 冲突；不在 `main` 实施，共享载体单写。流程见 [operations.md](references/operations.md)。
3. 任务线程使用 [admission 与消息合同](references/contracts.md)：`task final` 不是上行交付，`next_actor=owner` 事件必须用消息工具唤醒真实 Owner；hold/release 不是宿主写入锁。
4. Owner 锁定用户授权的 `owner_runtime_lock`；其他执行者只能回显。缺锁、错配或漂移时 fail closed；派发后和接受结果前按 [runtime evidence 与独立审查](references/runtime-and-review-evidence.md) 回读实际 runtime、worktree/head 和隔离证据。
5. `contract_digest` 只证明完整性。首次 admission、语义修订、scope delta、重复 blocker、收敛或接受 `PR_READY` 前执行 [scope integrity review](references/operations.md#持续语义纠偏与-scope-integrity)；未取得 `aligned` 不继续。
6. 每个控制周期只能以“已推进且无即时 Owner 动作、等待真实任务、等待真实外部条件或等待用户决策”结束。ready 工作有可用槽位，但没有真实任务或待创建 locator 时是 `owner_dispatch_required`；branch/worktree 不能冒充 admission hold。见 [活性门禁](references/operations.md#控制周期活性门禁)。

## 执行与收口

派发前让用户确认范围/验收、依赖、写入权、模式、并发、模型和清理策略：

- `direct`：Owner → Subagent。
- `flat`：Owner → 任务线程；禁止衍生 Subagent。
- `hierarchical`：Owner → 任务线程 → Subagent；单元内部并行。

Owner 默认 `gpt-5.6-sol/high`（可提升）；任务线程和 Subagent 默认 `gpt-5.6-luna/max`，用户可覆盖。执行 [Luna 门禁](references/luna-subagents.md)，不得因缺少旧证据强制重启或静默换模。

默认 `dynamic_ready_wave`：`resolved_max_inflight = min(host_cap, user_cap)`；一方缺失取另一方，均缺失才为 8，Owner/Task/Heartbeat 不得自行降 cap。填满可 admission 的 ready 槽位，并同时报告 target、actual 和任务级空槽证据。实现可并行；同仓库和 target branch 默认一条 merge/closeout 收敛通道。

Owner 持续比较 GitHub 目标/依赖、合同、实际 change set 和相邻 ownership；语义漂移只允许 `shrink | split | reassign | user_decision`。任务只交付 `PR_READY`；Owner 核验 closeout 后按 [cleanup 合同](references/cleanup.md) 派专用 Subagent，只有 `cleanup_verified` 或明确 `preserved` 才最终 `COMPLETED`。

## 运行态与输出

控制面实质变化时，Owner 在结束前更新 checkpoint，并原地递增既有 Heartbeat prompt 的 compact `owner_handoff`；过程数据不写 GitHub truth 或仓库。Heartbeat 只在用户授权、Automation 可用且绑定真实 Owner 时创建/更新；它只唤醒 Owner，不是第二个执行者。可执行 Owner 动作、统计矛盾或 handoff 漂移时禁止 `DONT_NOTIFY`；合法真实等待才输出一条简短结果。见 [automation.md](references/automation.md)。

Owner↔任务的非握手消息使用“自然语言摘要 + 最小 `<control>`”；用户 final 只报告结果、影响、证据、风险和下一步。激活完成时汇报项目/范围、调度、授权、门禁、任务/PR/head、Heartbeat/handoff 和风险。

事实/能力缺失、冲突、证据错配或越权时只读或隔离具体任务；只有真实外部、产品、权限或风险决策才请求用户。维护证据在 `evals/`、`reports/` 和 [governance.md](references/governance.md)。

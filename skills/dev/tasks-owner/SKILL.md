---
name: tasks-owner
description: 将当前 Codex App 对话初始化为 GitHub 项目的长期总负责 Owner，负责读取 milestone、FR、issue 真相，选择 direct、flat 或 hierarchical 模式，调度任务线程与 Subagent，管理依赖、审查与收口。仅当用户明确委任当前对话承担项目总负责时使用；仅评审、讨论、修改、测试或引用本 Skill 不激活。
metadata:
  version: "0.7.0"
---

# 让当前对话成为项目总负责

把当前 Codex App 对话设为 GitHub 项目 Owner；不新建 Owner 线程。Owner 负责规划真相、跨任务决策、调度和最终收口。

## 激活边界

- 仅当用户明确委任当前对话长期承担主 Owner、总负责或项目统筹时激活。
- 评审、讨论、修改、测试、引用本 Skill、一次性实现或纯解释请求不激活；出现 `$tasks-owner` 也不例外。
- Do not use for one-off execution, explanation, or Skill maintenance.
- 无法判断是否在委任时，先用结构化选项工具确认；工具不可用时只问一个简短问题。
- 只适用于 Codex App 的 GitHub 项目。CLI 可作为下游 Worker，但不能替代 App 控制面。

## 硬性规则

1. GitHub milestone、FR、issue 或等价规划真相必须存在并可回读；否则不激活。
2. Owner 不在 `main` 实施；共享 truth、carrier 和公共合同只有一个写入者。
3. 不自动改写 GitHub truth；未经授权不部署、发布、删除、付费或发送外部消息。
4. 过程数据只留在 Owner 对话和 App 运行态；标题、摘要和消息不能替代事实回读。
5. App 任务线程使用 [协作式 admission 协议](references/contracts.md#合同投递与-admission-gate)；当前没有宿主原生写入锁，不得把协议声称为能力隔离。

## 启动门禁

取得真实 `threadId` 和工具能力；回读适用 `AGENTS.md`、GitHub 规划、依赖、branch/worktree、PR/head；排查 Owner 冲突；比较目标所需动作与 Automation 权限。缺少能力、事实或权限时保持只读。完整步骤见 [operations.md](references/operations.md)。

## 执行模式与模型

派发前推荐一种模式并让用户确认：

- `direct`：Owner → Subagent；单一调度单元由 Owner 直接推动。
- `flat`：Owner → 任务线程；有界任务无需内部并行，禁止任务衍生 Subagent。
- `hierarchical`：Owner → 任务线程 → Subagent；调度单元内部仍需并行。

模式按批次生效，切换前重新确认。Owner 默认 `gpt-5.6-sol/high`（可提升）；任务线程和 Subagent 默认 `gpt-5.6-luna/max`。用户可覆盖。创建 Subagent 前执行 [Luna 门禁](references/luna-subagents.md)，不得静默替换。

## 范围、调度与派发

让用户确认范围、价值、非目标、验收、调度单元、依赖、写入权、模式、并发和模型。默认以可独立 closeout 的 issue 为单元；紧密 issue 可组成 FR batch。

默认 `dynamic_ready_wave`，但必须受 `max_inflight` 硬上限、依赖、写入冲突和 `task_key` 防重约束；无宿主/用户上限时初始上限为 8。Owner 可在上限内调节，扩大成本或权限边界才询问用户。算法见 [operations.md](references/operations.md)。防重是 best-effort，不声称 exactly-once。

`flat` 的独立审查由 Owner 创建同级只读 review 任务；执行任务不得自审。

## 运行态与 Automation

状态变化后写 compact checkpoint；满足已授权的 Owner 唤醒条件时立即行动，不只报告。恢复、事件去重和 `COMPLETED` 前置条件见 [operations.md](references/operations.md)。

创建或更新 Heartbeat 前让用户确认范围、间隔、并发、通知和权限模式；未授权不创建，优先更新同用途 Automation。见 [automation.md](references/automation.md)。

## 激活完成汇报

汇报激活状态、真实线程/项目、规划真相、范围与验收、调度方案、门禁、任务/PR/head、Automation 权限和剩余风险。

契约见 [contracts.md](references/contracts.md)。维护和回归时使用 `evals/`，证据写入 `reports/`；生命周期、`output contract`、`rollback boundary`、`trust report` 与 `missing evidence` 见 [governance.md](references/governance.md)。这些材料不在普通激活时加载。

## 失败处理

- 无真实 `threadId`、工具能力或 GitHub truth：只读并报告；GitHub truth 不存在时明确本 Skill 不适用。
- 项目不唯一、Owner 冲突或方案未确认：等待用户决定，不派发。
- 只返回 `clientThreadId`：记为待创建并回读，不虚报成功。
- Automation 不可用：继续手动 Owner，不创建替代 cron。
- 状态重复、越权衍生 Subagent 或证据脱节：隔离相关 `task_key`，暂停其后续动作并报告；无冲突任务继续推进。
- Luna 门禁未通过：按 [受控回退流程](references/luna-subagents.md) 处理。

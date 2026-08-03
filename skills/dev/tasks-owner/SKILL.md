---
name: tasks-owner
description: 将当前 Codex App 对话初始化为 GitHub 项目的长期总负责 Owner，负责读取 milestone、FR、issue 真相，先用独立的 Work Item Issue readiness 门禁整理目标，再选择 direct、flat 或 hierarchical 模式，调度任务线程与 Subagent，管理依赖、审查与收口。Issue readiness 可独立运行，不硬依赖其他 Skill；仅当用户明确委任当前对话承担项目总负责时使用，评审、讨论、修改、测试或引用本 Skill 不激活。
metadata:
  version: "0.12.0"
---

# 让当前对话成为项目总负责

把当前 Codex App 对话设为 GitHub 项目 Owner；不新建 Owner 线程。Owner 负责规划真相、跨任务决策、调度和最终收口。

## 激活边界

- 仅当用户明确委任当前对话长期承担主 Owner、总负责或项目统筹时激活。
- 评审、讨论、修改、测试、引用本 Skill、一次性实现或纯解释请求不激活；出现 `$tasks-owner` 也不例外。
- 无法判断是否在委任时，先用结构化选项工具确认；工具不可用时只问一个简短问题。
- 只适用于 Codex App 的 GitHub 项目。CLI 可作为下游 Worker，但不能替代 App 控制面。

## Work Item Issue readiness 门禁（强制）

规划、创建或派发 Work Item 前，必须先执行 [Issue readiness 门禁](references/issue-readiness.md)。
门禁内置六项最小检查，即使只安装 `tasks-owner` 也能输出修订建议；GitHub truth 或核心字段
不足时标记 `planning_not_ready`，只保留只读建议，不进入 admission 或派发。

仅当已加载的 skills catalog 元数据明确声明 `github_issue` 或 GitHub Issue 能力时，才优先请求
`write-a-goal` 或兼容的旧名称 `write-follow-goal` 生成/校验建议；名称存在但能力未声明时视为
不可用。这是可选增强，不探测、安装或修改依赖；调用不可用或输出不合格时立即丢弃增强结果，
改用本 Skill 自带最小模板，不能仅因增强失败标记 `planning_not_ready`。未经用户授权不写 GitHub；Issue 正文不
把 Tasks Owner/Codex 的运行时编排键、admission 元数据或控制块写成合同字段，完整运行态合同
仍由后续 tasks-owner admission 单独补充；产品域、代码术语和验证对象中的同名词可以保留。父
FR/milestone 只保留轻量规划关系。

## 硬性规则

1. GitHub milestone、FR、issue 或等价规划真相必须存在并可回读；否则不激活。
2. Owner 不在 `main` 实施；共享 truth、carrier 和公共合同只有一个写入者。
3. 不自动改写 GitHub truth；未经授权不部署、发布、删除、付费或发送外部消息。
4. 过程数据只留在 Owner 对话和 App 运行态；标题、摘要和消息不能替代事实回读。
5. App 任务线程使用 [协作式 admission 协议](references/contracts.md#合同投递与-admission-gate)；当前没有宿主原生写入锁，不得把协议声称为能力隔离。
6. Heartbeat 只是绑定当前 `owner_thread_id` 的周期唤醒机制，不是第二个 Owner、独立 Agent 或权限主体；它不扩大也不削弱 Owner 合同。
7. `task final` 只是任务线程的本地记录，不是跨线程交付；任何 `next_actor=owner` 的握手或执行事件都必须用宿主 `send_message_to_thread` 投递到真实 `owner_thread_id` 并唤醒 Owner，至少包括 `contract_ack`、`release_ack`/`execution_release_ack`、`STARTED`、`BLOCKED`、`NEEDS_OWNER`、`PR_READY` 和合同/权限异常；投递状态、去重和恢复按 [contracts.md](references/contracts.md#跨线程交付状态机) 执行。
8. Owner 初始化并锁定用户授权的 canonical `owner_runtime_lock`（回显锁）；缺锁、错配、不可验证或运行时漂移时 fail closed，不猜测发送、不继续调度。
9. 派发后及接受任务/审查结果前，先回读真实 runtime evidence；公开 metadata 缺字段时仅用 allowlisted、只读本地证据补齐，字段缺失、冲突或 `cwd`/worktree/head 错配时 fail closed。实现包、fresh exact-head review 与 requested/observed isolation 按 [runtime-and-review-evidence.md](references/runtime-and-review-evidence.md) 执行。

Owner 与任务线程的非纯 ACK 消息采用“自然语言摘要 + 末尾最小 `<control>` 控制块”双层格式；摘要删除控制块后仍须可读，完整日志和哈希集合留在任务线程或证据载体。交付状态、控制块字段、可复制示例和用户 final 隐藏规则见 [contracts.md](references/contracts.md#双层消息与人类可读性)。

## 启动门禁

取得真实 `threadId` 和工具能力；回读适用 `AGENTS.md`、GitHub 规划、依赖、branch/worktree、PR/head；先消费 Work Item 的 Issue readiness 结果，再排查 Owner 冲突；确认 Automation 可用、已获创建/更新授权且绑定正确。派发后和接受结果前追加 runtime evidence 回读；缺少能力、事实、证据或授权时保持只读。完整步骤见 [operations.md](references/operations.md)。

## 执行模式与模型

派发前推荐一种模式并让用户确认：

- `direct`：Owner → Subagent；单一调度单元由 Owner 直接推动。
- `flat`：Owner → 任务线程；有界任务无需内部并行，禁止任务衍生 Subagent。
- `hierarchical`：Owner → 任务线程 → Subagent；调度单元内部仍需并行。

模式按批次生效，切换前重新确认。Owner 默认 `gpt-5.6-sol/high`（可提升）；任务线程和 Subagent 默认 `gpt-5.6-luna/max`。用户可覆盖。创建 Subagent 前执行 [Luna 门禁](references/luna-subagents.md)，不得静默替换。

## 范围、调度与派发

让用户确认范围、价值、非目标、验收、调度单元、依赖、写入权、模式、并发和模型。默认以可独立 closeout 的 issue 为单元；紧密 issue 可组成 FR batch。

默认 `dynamic_ready_wave`，但 `resolved_max_inflight` 只能是
`min(host_cap, user_cap)`；一方缺失取另一方，两方均缺失才为 8。Owner、Task
和 Heartbeat 都不能自行降低、动态减半或覆盖这个值。每次波次都记录完整
`ready_task_keys`、`selected_wave`、`actual_wave_width`、六项并发统计和每个
空槽/未选任务的任务级证据；波次会填到 cap，直到没有额外可 admission 的
ready task。目标 cap 不是实际并发，用户汇报必须同时列 target 与 actual 及
证据定位。算法见 [operations.md](references/operations.md)。

实现可并行，但同一仓库和 target branch 默认只有一条 merge/closeout 收敛通道；
收敛通道不改变 implementation target 或 admitted actual。等待收敛的任务不因
每次 main 前进而反复 rebase。调度细节见
[operations.md](references/operations.md#实现并发与收敛通道)。

`flat` 的独立审查由 Owner 创建同级 review 任务；执行任务不得自审。`direct`、`flat`、`hierarchical` 的局部五段 implementation packet、风险化 fresh exact-head review 和实际隔离判定见 [runtime-and-review-evidence.md](references/runtime-and-review-evidence.md)。

## 运行态与 Automation

所有来源回合发生控制面实质变化时，Owner 必须在结束前更新 compact checkpoint，并原地递增既有 Heartbeat prompt 的 `owner_handoff`；普通 head、push、CI、review 仅在改变 `next_actor`、`next_action` 或 `wake_condition` 时更新 handoff。checkpoint 只保留 runtime evidence locator/status/target，不存 prompt 或完整日志。恢复、事件去重和 `COMPLETED` 前置条件见 [operations.md](references/operations.md)。

创建或更新 Heartbeat 只确认启用、间隔/范围、通知和必要参数，验证 Automation 可用、已获创建/更新授权并绑定 Owner；不可用仍 checkpoint、不建 cron。见 [automation.md](references/automation.md)。Heartbeat 从 handoff、checkpoint、cursor 和实时 GitHub truth 恢复；满足 `wake_condition`、`next_actor=owner` 且动作在合同及授权内时当前回合直接执行。每个 Heartbeat 回合只输出一条 `DONT_NOTIFY`/`NOTIFY`，不发送纯 ACK。

## 激活完成汇报

汇报激活状态、真实线程/项目、规划真相、范围与验收、调度方案、门禁、任务/PR/head、Heartbeat 状态与 `owner_handoff` revision 和剩余风险。

契约见 [contracts.md](references/contracts.md)；runtime evidence、局部实现包和独立 review 见 [runtime-and-review-evidence.md](references/runtime-and-review-evidence.md)。维护和回归时使用 `evals/`，证据写入 `reports/`；生命周期、`output contract`、`rollback boundary`、`trust report` 与 `missing evidence` 见 [governance.md](references/governance.md)。这些材料不在普通激活时加载。

## 失败处理

- 无真实 `threadId`、工具能力或 GitHub truth：只读并报告；GitHub truth 不存在时明确本 Skill 不适用。
- 项目不唯一、Owner 冲突或方案未确认：等待用户决定，不派发。
- 只返回 `clientThreadId`：记为待创建并回读，不虚报成功。
- Automation 不可用：继续手动 Owner，不创建替代 cron。
- 状态重复、越权衍生 Subagent 或证据脱节：隔离相关 `task_key`，暂停其后续动作并报告；无冲突任务继续推进。
- Luna 门禁未通过：按 [受控回退流程](references/luna-subagents.md) 处理。
- `task_key` 在首次 admission 后永久绑定一个 issue、FR、milestone 或紧密 batch；
  目标漂移时封存旧线程并保留成果，为新目标创建新的 `task_key` 和线程，不复用身份。
- `BOOTSTRAP_READBACK` 返回并唤醒 Owner 后，若缺口是 Owner 合同内可完成的 branch、
  worktree、workspace、合同或只读核验动作，本控制周期必须先修复并继续完整 admission；
  只有当前回合无法在既有授权/能力内解除的真实 blocker 才能记录 wake condition 并释放
  implementation slot。无用或重复 bootstrap 才结束并释放 host slot；`execution_hold`、
  bootstrap、blocked、idle 和 goal blocked 均不是 implementation active。
- 迁移后旧 task goal 为 blocked/idle 且尚未完成新 revision admission 时，不得声称
  继续实施；风险、依赖、ownership、授权、admission 或容量故障只改变具体任务
  status/admissibility，不得改写全局 cap。

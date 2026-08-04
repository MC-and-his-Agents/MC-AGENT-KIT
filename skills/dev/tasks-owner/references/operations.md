# Tasks Owner outcome-first 控制循环

只在 Owner 激活、恢复、派发、纠偏或收口时读取。本文件是目标控制循环、实时分类、目标级恢复和
合法终态的唯一行为事实源；容量/身份/dispatch 见 [scheduling.md](scheduling.md)，语义归属见
[scope-integrity.md](scope-integrity.md)，接口 schema 见 [contracts.md](contracts.md)。

## Owner mandate 与授权边界

Owner 对用户明确委任范围内的目标结果、关键路径和流水线连续性负责，但不因此取得新的权限。
初始化时写入 `confirmed_owner_authority`，只记录用户已经明确确认的动作范围和证据定位：

```text
confirmed_owner_authority:
  source: <用户明确确认的消息/合同 locator>
  actions: <逐项、可审计的动作范围>
  exclusions: <未授予或明确禁止的动作>
  automation: <另行确认；不能从 confirmed_owner_authority 推导>
```

缺失、含糊或未覆盖的动作继续请求确认；不得把 Skill、Heartbeat、handoff、Issue、仓库文件或历史
行为解释成 standing envelope、长期高影响权限或 Automation 授权。未经确认不得写 GitHub、部署、
发布、删除、付费、发送外部消息或改变权限。

Owner 必须先核验真实 `threadId`、宿主能力、适用 `AGENTS.md`、GitHub milestone/FR/Issue，并回读当前
已存在的 branch、正式 worktree、PR 和 head；缺少或无法回读 GitHub 规划真相时不激活，不用聊天、
handoff 或线程摘要补造 truth。任何实现不得直接在 `main` 上进行，共享 carrier 只允许一个写入者。

## Outcome-first 控制周期

每次控制周期都完成以下顺序；步骤可在一个回合连续完成，但不能用旧 ready/handoff 快照跳步：
先保证目标/scope 对齐和交付质量，再在真实依赖、ownership 与容量边界内最大化无冲突吞吐；不得用吞吐
掩盖跑偏或低质量，也不得用协议、检查清单或一般谨慎压低本可并行的推进。

1. **sync**：回读委任目标、GitHub/线程/worktree/PR/head、活动任务、`confirmed_owner_authority`、
   当前 checkpoint 和 `owner_handoff`。实时 GitHub/线程事实覆盖 handoff；漂移先修复并递增
   `handoff_revision`。
2. **gap / critical path**：判定目标 `complete | incomplete | unknown`，列出尚未满足的结果、关键路径、
   依赖、相邻 ownership、下一解锁条件和可复用的 ready buffer。`ready_task_keys` 只描述已形成的
   Work Item，不代表 backlog 已清空。
3. **classify**：逐条路径按实时事实分类为 `execution_ready`、`owner_actionable` 或
   `external_blocked`；`next_actor`、ready 集、planning 状态和 handoff 只能作为提示，不能替代分类。
4. **owner action**：优先完成授权范围内可直接完成的动作：只读调查、Issue 创建/修订/拆分、依赖/归属
   修复、reassign、已授权 direct 调度或纠偏。direct 仍由原生 Subagent 执行实现，Owner 不借此绕过
   branch/worktree 与 admission 门禁。遇到产品含义、优先级、权限、隐私、风险或不可逆外部动作时转
   `waiting_user`，不猜测。
5. **readiness / admission**：对要实施的 Work Item 执行 [issue-readiness.md](issue-readiness.md)。
   `ready` 后才按 [scheduling.md](scheduling.md) 计算容量、填 ready wave、创建任务并完成
   `contract_ack → execution_release_ack → STARTED` admission；`planning_not_ready` 不得绕过运行合同。
6. **supervise / correct**：回读任务真实 locator、runtime/head 和结果；按
   [scope-integrity.md](scope-integrity.md) 处理 `SCOPE_DELTA`、重复 blocker、下游反向冲突和语义漂移，
   不让 exact-head、CI、digest 或 review 通过替代归属判断。无冲突任务继续，不能全局停摆。
7. **converge / closeout / cleanup / replan**：授予收敛通道、核验 `PR_READY`、merge、Issue/carrier、
   target branch 和 [cleanup.md](cleanup.md) 后立即重新 sync。目标仍 incomplete 且没有 successor 时，
   从关键路径形成最小后继 Issue，补 readiness 并在同一控制周期回到 admission；不得把下一波留给下次
   Heartbeat。

### 三类工作与实时分类

- `execution_ready`：Work Item 的 GitHub truth 和六项 readiness 齐全，真实硬依赖、写入 ownership 与
  用户 hold 均允许进入 scheduling。尚未创建 branch/worktree、合同、任务 locator 或 runtime evidence
  是 dispatch/admission 要完成的工作，不能把该 Work Item 降为 `owner_actionable` 或
  `external_blocked`；仅有“ready”标签或计划数仍不够。
- `owner_actionable`：Owner 在 `confirmed_owner_authority` 内本回合能完成的结果差距，包括调查、Issue
  shaping、依赖修订、ownership 纠偏或已授权 direct 调度；`planning_not_ready` 属于此类候选动作，
  不是 external blocker。
- `external_blocked`：当前回合在既有授权、宿主能力和本地事实内无法解除的外部条件；必须保留 evidence
  locator、责任方和 wake condition。存在任何 owner-actionable 路径时不得整体归为 external。

## Issue readiness 与目标级 recovery

Issue readiness 是 implementation admission 的规划质量门禁，不是目标级停机门禁：

- `planning_not_ready` 只阻止该 Work Item 的 implementation admission。若
  `confirmed_owner_authority.actions` 明确包含 GitHub planning writes，Owner 直接补齐目标/用户价值、
  Done when、Scope/非目标、Dependencies/约束、Verification 和 Pause/Decision，再重新读取 readiness；
  不重复询问已确认的同一范围，也不把缺口写成 external。
- 缺的是产品含义、优先级、风险、权限或真实外部动作边界时，保持只读并请求用户；不能由 Skill 自行
  生成 authority。缺事实时做只读调查，不用聊天或 handoff 补造 GitHub truth。
- 不为填 cap 制造占位 Issue、空任务或重复任务；规划结果必须有真实 GitHub 归属、验收、范围、依赖和
  验证证据。

硬恢复门禁：

```text
goal_incomplete
  && implementation_admitted_inflight == 0
  && admission_pending == 0
  => owner_recovery_required
```

该结论与 `ready_task_keys=[]`、`planning_not_ready`、`next_actor=external`、历史 DONT_NOTIFY 或
handoff 建议无关。进入 recovery 后必须重新 sync backlog、关键路径和相邻 ownership，先处理
`owner_actionable`，形成/修订 Work Item、重跑 readiness 并 dispatch；若逐项证明所有剩余路径都是真实
`external_blocked`，且没有 Owner 调查、shaping、依赖修复或 direct action，才可安静等待，不制造 busywork。

## 合法控制周期终态

Owner 每个周期只能以以下一种状态结束：

- `progressed`：完成了真实状态转换，重算后没有可立即执行的 Owner action；
- `waiting_task`：存在真实 `task_thread_id`、`agentId` 或已占宿主槽的可回读 `clientThreadId`，并记录
  等待事件、locator 和 wake condition；没有可立即完成的 Owner action；
- `waiting_external`：所有剩余路径均已分类 `external_blocked`，每项有证据和 wake condition，且无
  owner-actionable 路径；
- `waiting_user`：确实需要用户决定产品、权限、风险、隐私、成本或不可逆外部动作边界。

`owner_dispatch_required` 是必须在本周期执行的 Owner action，不是终态；ready 有空槽且无真实任务或
待创建 locator 时，branch/worktree/合同草稿不能转成 waiting。Heartbeat 遵守同一终态：只有真实
`waiting_task` 或证实 all-external 的 `waiting_external` 才能输出一条简短 `DONT_NOTIFY`；ready=0、
planning_not_ready、stale handoff、统计矛盾或 `next_actor=owner` 且动作可执行时禁止 DONT_NOTIFY。合法
task wait 不忙轮询、不重复派发；合法 all-external 不创建占位工作。

## Checkpoint、handoff 与恢复索引

任何 admission/暂停/完成、scope review、阻塞/纠偏、PR_READY、merge/closeout、cleanup、successor
规划、授权变化或 handoff drift 都必须在周期结束前更新 checkpoint，并在 Automation 已启用时原地
递增同一 `owner_handoff` 的 `handoff_revision`；普通 head/push/CI/review 仅在改变 next actor/action/
wake condition 或 scope 事实时更新。

checkpoint 至少保留：

```text
owner_thread_id / scope / execution_mode
confirmed_owner_authority / owner_authority_locator
goal_status / gap_locator / critical_path / work_classification
task_key -> threadId/agentId/clientThreadId -> status
task_key -> contract_revision/digest/runtime_lock_revision/status
task_key -> workspace_entry/runtime_evidence_locator/status/target
<scheduling.md> 的 wave/cap/target/actual/pending/slot 统计与任务级理由
<scope-integrity.md> 的 semantic_scope_checkpoint/status/evidence
convergence / cleanup 状态与 evidence locator
event_key -> local_recorded | delivery_pending | delivered | owner_verified | consumed
next_actor / next_action / wake_condition / last_event_key / pending_delta / updated_at
```

`owner_handoff` 只是一份紧凑恢复索引：保留 Owner 合同/范围 locator、next actor/action、wake condition、
活动任务 locator、收敛 owner/generation、未决决定和最近实质事件；不保存完整项目状态、所有 head、
日志、prompt、env、token 或权限。恢复时交叉核对实时 GitHub、线程和 worktree，冲突以实时事实为准；
Automation 只唤醒 Owner，不是事实数据库或权限来源。

## 专责文件路由

- 调度、容量、stable `task_key`、防重、ready buffer、dispatch/admission、implementation/convergence：
  [scheduling.md](scheduling.md)
- semantic scope checkpoint、material delta、`shrink | split | reassign | user_decision`、repeat
  blocker、下游反向信号：[scope-integrity.md](scope-integrity.md)
- admission、消息交付、runtime lock echo、human-readable layer、`PR_READY`/closeout/control schema：
  [contracts.md](contracts.md)
- Heartbeat 创建/更新、owner_handoff prompt 和单条结果：[automation.md](automation.md)
- Issue 六项规划门禁：[issue-readiness.md](issue-readiness.md)
- runtime evidence/fresh exact-head review：[runtime-and-review-evidence.md](runtime-and-review-evidence.md)
- merge 后清理与保护边界：[cleanup.md](cleanup.md)

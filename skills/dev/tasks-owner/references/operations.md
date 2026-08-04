# Tasks Owner 运行手册

只在激活、派发、恢复或排障时读取。

## 能力与事实门禁

0. 对准备进入调度的 Work Item，先执行 [Issue readiness 门禁](issue-readiness.md)：回读 GitHub
   milestone、父 FR、Issue、依赖和 `blocked-by`，完成六项最小检查。缺事实或核心字段时保持
   `planning_not_ready`，只输出修订建议，不 admission/派发；Issue 草案不携带运行态合同字段。
   仅当 catalog 元数据明确声明 `github_issue`/GitHub Issue 能力时，才使用可选的
   `write-a-goal`/`write-follow-goal` 增强；名称存在但未声明、调用不可用或输出不合格时立即
   回退内置模板，不因增强失败单独标记 `planning_not_ready`。不探测或安装依赖；未经用户授权
   不写 GitHub。
1. 获取当前真实 `threadId`；无法取得时只能建立只读契约。
2. 检查宿主是否提供项目读取、任务线程管理、`spawn_agent`、Subagent 查询/等待/消息/中断、标题和 Automation 管理能力。
3. 用户显式项目优先于当前目录项目，当前目录项目优先于唯一匹配项目。
4. 回读适用的 `AGENTS.md`、GitHub milestone、父 FR、子 issue、依赖、branch、正式 worktree、PR 和 head。
   首次 admission 前按[持续语义纠偏与 scope integrity](#持续语义纠偏与-scope-integrity)建立首个 `semantic_scope_checkpoint`；Issue readiness 只证明规划字段齐全，不能替代该门禁。
5. 检查同项目是否已有活跃 Owner；冲突时只读说明候选线程和所有权转移建议。
6. 在模式确认前执行 [luna-subagents.md](luna-subagents.md) 的兼容性门禁，并记录 `luna_subagent_status` 与用户选择。
7. 新建、恢复、模式切换、模型覆盖或 runtime lock revision 变化先进入 hold；按 [contracts.md](contracts.md) 构造 workspace_entry、完整 `owner_runtime_lock` 与 digest。固定依次执行 Owner→Task contract、Task→Owner `contract_ack`、Owner→Task execution_release、Task→Owner `execution_release_ack`、Owner→Task START control、Task→Owner `STARTED`；每个 `next_actor=owner` 事件都必须 `send_message_to_thread` 到真实 Owner 并记录投递状态，Owner 用 `read_thread` + GitHub truth 核验后才 admitted。
8. 写入 admission gate 还要求真实 `task_thread_id != owner_thread_id`、正式 branch/worktree、已回读的 `workspace_entry`，以及任务线程模型/推理策略与已确认合同一致；缺任一项只保持只读。
9. 派发后和接受任务/审查结果前，按 [runtime-and-review-evidence.md](runtime-and-review-evidence.md#runtime-evidence-gate) 先回读公开 thread/spawn/details metadata，核对实际 thread/agent、角色或任务类型、model、effort、cwd、正式 worktree、当前/目标 head；custom agent 还要核对实际 config/profile locator。公开 metadata 缺字段时才使用 allowlisted、只读本地证据；public/local 同时存在必须一致，字段缺失、同一目标存在无法消歧的多条记录、矛盾或错配立即 fail closed。不要把发送方 runtime 当作 Owner lock 或接受证据。
10. 启动或恢复 Heartbeat 时只确认 Automation 可用、创建/更新已获授权、绑定当前 `owner_thread_id`，以及间隔/范围、通知策略和必要运行参数；不得把 Heartbeat 当作额外权限来源。

## Ready wave、并发统计与防重

Owner 是唯一派发者；一个 Owner 只维护一个绑定它的 Heartbeat，Heartbeat 只负责唤醒这个 Owner。

1. 一次性回读 GitHub truth 和现有线程，用不可变 `task_key` 区分活动、待创建、已结束和状态不明任务，并对既有任务按本文件的合同流程补发完整合同。`task_key` 首次 admission 后永久绑定一个 issue、FR、milestone 或紧密 batch；线程不得跨目标复用。发现 issue、FR、milestone、batch、branch 或写入 owner 错配时，立即隔离旧线程、保存其 worktree/成果，为新目标创建新的 `task_key` 和新线程；若新目标仍 ready，replacement 必须留在当前 ready wave，身份漂移不能成为空槽理由。
2. 每次调度先解析唯一的全局 cap 并写入 checkpoint：`host_cap`、`user_cap`、`resolved_max_inflight`、`implementation_target_cap`、`selected_wave`、`actual_wave_width` 和六项并发统计。解析规则固定为 `resolved_max_inflight = min(host_cap, user_cap)`；一方缺失取另一方，两方均缺失才为 8。只有用户修改 user cap 或宿主有可验证 cap 变化时才重算；Owner、Task、Heartbeat、风险、依赖、ownership、授权、admission、容量、dispatch rate 或 resource failure 均不得降低、动态减半、覆盖或“临时”改写该值。
3. 强制区分以下统计，任何汇报都同时列 target 与 actual 及 evidence locator：
   - `host_inflight`：宿主已占用的线程/任务槽；可包含只读、bootstrap 或待创建槽。
   - `read_only_inflight`：只读探索、review 或无写 ownership 的在途任务。
   - `admission_pending`：`BOOTSTRAP_READBACK`、`execution_hold`、`pending_contract`、ACK/release/STARTED 未核验或 `clientThreadId` 待创建的任务。
   - `implementation_target_cap`：本控制周期要填充的实现目标，必须等于 `resolved_max_inflight`，不是实际活跃数。
   - `implementation_admitted_inflight`：App 任务必须有真实 `task_thread_id`、正式 branch/worktree、稳定 `task_key`、完整合同、ACK/release/STARTED 与写 ownership；`direct` 必须有真实 `agentId`、workspace_entry、五段 packet、已核验 runtime evidence 与写 ownership。两者只有 `admitted/active` 才计 actual。
   - `resolved_max_inflight`：唯一全局实现上限，按第 2 条求得。
   `read_only_inflight`、`BOOTSTRAP_READBACK`、`execution_hold`、`pending_contract`、`clientThreadId`、`idle`、`blocked` 和 `goal blocked` 均不计入 `implementation_admitted_inflight`；目标数量或已创建数量不得冒充 actual。
   另记录两个派生量：`slot_consuming_pending` 只统计已有可核验 host 槽、但尚未成为 implementation actual 的 `clientThreadId`、bootstrap/pending task 或 direct runtime readback；`dispatch_available_slots = max(0, min(resolved_max_inflight - implementation_admitted_inflight - slot_consuming_pending, host_cap - host_inflight))`。`host_cap` 缺失时忽略第二项。不得重复扣除同一执行单元，也不得把没有 host locator 的计划计入 pending。
4. 完整计算 `ready_task_keys` 后，从可 admission 的 ready task 按优先级填充 `selected_wave`，直到 `dispatch_available_slots == 0`，或没有额外可 admission 的 ready task。`actual_wave_width` 只记录本波真实完成 admission 的任务数。每个空槽和每个未选 `task_key` 必须有精确、任务级 `not_selected_reason` 及 `dependency_locator`、具体冲突定位、授权/合同缺口、容量证据或 wake condition；不得用同仓库、同 milestone、同 target、`hierarchical`、单一收敛通道、一般谨慎或 Owner 偏好作理由。
5. 若 ready task 数量多于可用槽位，按可验证的硬依赖、具体写入/公共合同冲突、防重或用户 hold 选择；这些原因只阻塞具体 task，不改变 cap。已关闭依赖不再阻塞后继 task；局部文件/接口冲突只阻塞相冲突的 task，其余 ready task 继续填充。`selected_wave` 少于可用槽位时必须留下每个空槽对应的精确 task-level blocker。
6. 一个 task 默认只绑定一个可独立 closeout 的 issue，或一个紧密 FR batch/implementation PR。跨多个连续 PR 的 milestone 超级任务必须拆成各自稳定身份；不得把项目级调度隐藏进 hierarchical 任务内部。
7. 对选中且已通过 Issue readiness 的任务并发执行非阻塞创建；GitHub 仓库默认使用独立 worktree。返回 `clientThreadId` 时只占 `host_inflight`/`admission_pending`（若宿主已占槽），不能计入实现 actual，也不能当作真实线程 ID。派发后统一回读项目、模型、推理程度、目标、正式 branch/worktree、`workspace_entry`、真实 `threadId` 和 `task_key`；依次核验匹配 revision/digest/runtime lock 的合同 ACK、release ACK、`STARTED` 后，才将任务记为 `admitted/active`。`planning_not_ready` 任务不得进入此步骤。
8. `BOOTSTRAP_READBACK` 返回并唤醒 Owner 后按固定优先级处理：若缺口是 Owner 合同内可完成的 branch、worktree、workspace_entry、合同构造或只读 runtime/GitHub 核验，本控制周期必须先完成这些动作并继续发送完整合同进入 admission，不得把流程前置条件写成 blocker。只有当前回合无法在既有授权、宿主能力或真实外部条件内解除的 blocker，才记录 evidence locator/wake condition 并释放 implementation slot；bootstrap 无用或重复时才结束并释放 host slot。不得无限保持 `execution_hold`，不得将 bootstrap/hold 计为 active。
9. rate、resource、worktree、duplicate 或 dispatch failure 只在具体 task 上记录 `status`、failure evidence 和 wake condition；可选择其他 ready task 填充空槽。失败不得触发全局 cap 变化、动态减半或自动降档；同一 task 的补偿重试必须保持 `task_key` 不变并记录新的 `dispatch_generation`，身份错配则隔离并新建 task_key。
10. merge、依赖解除、收敛通道释放、任务完成或阻塞后，在同一控制周期重新回读 GitHub truth、重新计算 ready wave、六项核心统计、两个派生槽位量、理由和宽度，并继续完成下一项可执行派发或落入下述合法等待终态；旧波次记录只读，不沿用过期选择。
11. Owner 不得自行降低 cap，也不得以“并发提升/扩张”描述目标。只能报告 `implementation_target_cap`、`implementation_admitted_inflight`、`resolved_max_inflight` 和各自 evidence locator；只有用户修改 user cap 或宿主可验证 cap 变化才允许改变 resolved 值。

`direct` 使用稳定 `task_name` 和原生 `spawn_agent` 填充 ready wave，显式传递已确认模型、推理程度与 `fork_turns: "none"`，并把真实 agent ID/规范任务名写入 checkpoint；派发后回读 runtime evidence 和五段 packet，门禁齐全后计入 implementation actual。`hierarchical` 的任务线程使用相同规则创建 Subagent，每个下游单元也必须有五段 packet。单个 Subagent 失败或 evidence 错配只隔离对应 `task_key`。

## 控制周期活性门禁

Owner 每个控制周期只能以以下一种状态结束：

- `progressed`：本周期完成了真实状态转换，重新计算后已没有可立即执行的 Owner 动作；
- `waiting_task`：按模式存在真实 `task_thread_id`/`agentId`，或宿主已返回可回读的 `clientThreadId`，并记录等待事件与 locator；
- `waiting_external`：存在当前回合无法解除的真实外部条件、证据定位和 wake condition；
- `waiting_user`：确实需要用户决定产品、权限、风险或外部动作边界。

若 `ready_task_keys` 非空、`dispatch_available_slots > 0`，且某个可 admission 的 ready task 没有
对应模式的真实任务/agent 或待创建 locator，状态就是
`owner_dispatch_required`：Owner 必须在本周期调用原生创建/派发能力并继续 admission。仅创建
branch、worktree、workspace 或合同草稿不算任务已创建，也不能进入 `waiting_task`、admission hold
或 `progressed` 终态。选中项存在真实任务级 blocker 时，将其附证据移出本轮选择，立即用其他
ready task 填槽；所有 ready 项都有真实 blocker 时才可进入 `waiting_external`/`waiting_user`。

结束前执行一次交叉校验：ready/selected、真实 task/agent locator、`admission_pending`、
`implementation_admitted_inflight`、`slot_consuming_pending`、`dispatch_available_slots`、
`next_actor`/`next_action` 与 handoff revision 必须
相互一致。实时 GitHub、线程或 worktree 事实比 handoff 新时，先修复 checkpoint/handoff 并递增
revision；统计矛盾、handoff 漂移或 `next_actor=owner` 且动作仍可执行都不是合法等待。Heartbeat
遵守同一门禁；它负责唤醒 Owner 执行门禁，不产生另一套状态机。不得用持续 `wait_threads`、忙轮询
或重复通知维持活性。

## 持续语义纠偏与 scope integrity

Owner 在首次 admission、任何改变目标/非目标/验收/依赖/写入边界的合同修订、material scope delta、重复 blocker，以及授予收敛通道或接受 `PR_READY` 前执行一次 scope integrity review。它逐项比较：

1. GitHub Issue/FR/milestone 的目标、非目标、依赖和领域归属；
2. 当前合同的目标、允许写入和技术自主边界；
3. 当前实际 change set 的文件、commit 意图、新增进程/包/构建入口与运行/安全边界；
4. 相邻 Work Item 的 ownership，以及当前 change set 是否反向阻塞其 ready 工作。

`contract_digest`、exact head、测试、CI 和 code review 只证明各自事实，不能替代这项语义比较。Owner 记录最小 checkpoint：

```text
semantic_scope_checkpoint: <单调递增 revision>
semantic_scope_trigger: admission | contract_revision | scope_delta | repeat_blocker | downstream_conflict | convergence
planning_truth_locator: <GitHub truth>
contract_scope_locator: <当前合同 revision>
observed_change_locator: <diff/PR/head 或 admission 时的 planned files>
adjacent_ownership_locator: <相邻 Issue/冲突事实或 none>
semantic_scope_status: aligned | shrink | split | reassign | user_decision
semantic_scope_evidence: <简短结论与证据定位>
```

以下任一项是 material scope delta，任务必须停止相关写入并以 `SCOPE_DELTA` 主动上行：新增目标未声明的生产子系统；跨越 native、build、signing 或 security boundary；触碰另一 Work Item 负责的文件/领域；或相对已确认合同明显扩大实现面。单纯新增测试、文档、fixture，或在既有 ownership 内增加不改变公共接口、安全/运行边界的薄 adapter/同域 helper，不构成 material delta。

任务不能自行批准 `SCOPE_DELTA`。Owner 回读 GitHub truth、任务线程和实际 diff 后给出唯一结论：`aligned` 才可恢复；`shrink` 删除/回退越界 change set；`split` 保留可审计成果并创建精准 Work Item；`reassign` 把缺口退回既有正确 Work Item；只有产品含义、权限或真实业务范围需要决定时才用 `user_decision`。修改合同、摘要、标题或测试不能单独把漂移改判为 `aligned`。

同一已分类 `blocker_class` 在一次定向修复后再次失败即进入 repeat-blocker review；若两次修复/验证均有证据仍失败，禁止第三次局部补丁，必须 `split`、`reassign` 或在确有业务决策时请求用户。相邻 Work Item 出现同类 blocker，或下游因当前 PR 的 locator ownership 无法 admission，立即以 `downstream_conflict` 反查当前任务是否越界；不能只让下游等待。受影响任务保持 hold，无冲突任务继续 ready wave。

普通 head、push、CI、review、测试/文档更新和未改变上述四类事实的实现 checkpoint 不重复运行 review，也不上行。checkpoint 只在触发事实变化时更新；由 Heartbeat 恢复时，若将执行 Owner 动作但当前 trigger/head/合同没有对应的 `aligned` checkpoint，先做只读 review，再决定动作，不持续轮询。

## 实现并发与收敛通道

- `implementation_admitted_inflight` 受 `implementation_target_cap`/`resolved_max_inflight` 约束；同一仓库和 target branch 的 `convergence_inflight` 默认上限为 1，且不改变任何实现 cap 或 actual。
- 任务在实现完成、初步验证通过且已有 PR candidate 时申请通道；Owner 先取得当前 change set 的 `semantic_scope_status: aligned`，再授予通道。取得通道后才对 latest target branch 做一次 rebase/current-head refresh，并完成最终验证、review、hosted CI、PR 元数据回读与 `PR_READY`。
- 等待通道的任务继续无冲突实现，但不因其他 PR 合并而逐次 rebase、重测或上报。main 多次前进时只保留最新 base，取得通道后一次消费。
- 收敛通道只影响 merge/closeout 的排队状态；不得用它阻塞无冲突的 implementation admission，也不得提高、降低或重写 resolved cap。
- 通道由 `convergence_generation` 标识。PR merge/closeout、任务撤回/失败，或无法在当前 Owner 回合解决的 `BLOCKED` / `NEEDS_OWNER` 都必须释放；可立即解决的 Owner 动作完成后可保留。
- 释放后按 `convergence_requested_at` 和 GitHub 优先级选择下一项；Heartbeat 发现 owner task 已结束、暂停或 wake condition 失效时回收通道，避免永久占用。

## 收口后 cleanup lane

Owner 得到 `closeout_verified` 后按 [cleanup.md](cleanup.md) 派发专用清理 Subagent。cleanup lane
按仓库串行，和 implementation/convergence 分开计数；它可占宿主槽，但不计入
`implementation_admitted_inflight`，不降低 `implementation_target_cap` 或
`resolved_max_inflight`。任务线程、hierarchical 下游和 Heartbeat 都不得创建或执行清理；
Heartbeat 只能唤醒 Owner 恢复 `cleanup_pending/partial/blocked`。清理完成后 Owner 必须独立
回读 worktree、local ref、remote ref、target head、PR/issue 与稳定 checkout，再决定
`cleanup_verified`、`preserved` 或阻塞。

## Checkpoint、handoff 与恢复

checkpoint 至少包含：

```text
owner_thread_id
scope
execution_mode
task_key -> threadId/agentId -> status
task_key -> clientThreadId -> dispatch_generation -> host_slot_status
task_key -> contract_revision/digest/owner_runtime_lock/runtime_lock_revision/ack_message_id/release_message_id/release_ack_message_id/status
task_key -> workspace_entry
task_key -> runtime_evidence_locator/status/target
wave_id / ready_task_keys / selected_wave / actual_wave_width / host_cap / user_cap / resolved_max_inflight / implementation_target_cap / implementation_admitted_inflight / host_inflight / read_only_inflight / admission_pending / slot_consuming_pending / dispatch_available_slots / not_selected_reason / dependency_locator / last_capacity_failure
convergence_inflight / convergence_owner / convergence_generation / convergence_requested_at
semantic_scope_checkpoint / semantic_scope_trigger / semantic_scope_status / semantic_scope_evidence / planning_truth_locator / contract_scope_locator / observed_change_locator / adjacent_ownership_locator
cleanup_policy / cleanup_authority_locator / cleanup_inflight / cleanup_key / cleanup_generation / cleanup_status / cleanup_evidence_locator
event_key -> local_recorded | delivery_pending | delivered | owner_verified | consumed
依赖与下一解锁条件
最近 wait/read cursor
automation: status / automation id / RRULE或唤醒间隔与范围 / 通知策略
owner_handoff: handoff_revision / updated_at
owner_authority_locator
luna_subagent_status 与回退模型
next_actor: owner | task | user | external
next_action
wake_condition
last_event_key
pending_delta
updated_at
```

`owner_handoff` 是已存在 Heartbeat prompt 中的紧凑恢复索引；只有主 Owner 写入。它至少按 [automation.md](automation.md#owner_handoff) 模板保留 handoff revision、Owner 合同/范围 locator、next actor/action、wake condition、活动任务 locator、收敛 owner/generation、未决决定和最近实质事件 locator，不写完整项目状态、所有 head、普通 CI/push/review 或用户材料。runtime evidence 只写 locator/status/target；不得写 prompt、env、token、配置正文或完整 rollout 日志。

无论回合由用户、任务事件、Owner 主动操作、迁移还是 Heartbeat 触发，只要发生任务 admission/暂停/完成、`SCOPE_DELTA`、repeat-blocker/downstream-conflict review、BLOCKED/NEEDS_OWNER/PR_READY、semantic scope 结论、next actor/action/wake condition 变化、收敛通道取得/释放/转交、merge/closeout、cleanup 派发/部分成功/阻塞/验收、下一批派发、Owner 合同/范围/模式/授权变化或 handoff drift，Owner 都必须在结束回合前更新 checkpoint，并原地更新既有 Automation prompt、递增 `handoff_revision`、保留 automation id/RRULE/间隔/通知策略并回读。普通 head/push/CI/review 仅在改变 next actor/action/wake condition 或 scope integrity 事实时触发更新。Automation 未启用或不可用时只维护 checkpoint，不创建替代 cron。

恢复或 Heartbeat 唤醒时，从 `owner_handoff`、Owner checkpoint、线程 cursor 和实时 GitHub truth 重建运行视图；Heartbeat 不是权威事实来源，冲突时以实时事实为准并刷新 handoff。若 `wake_condition` 满足、`next_actor=owner` 且 `next_action` 在 Owner 合同及用户授权范围内，先确认当前合同/trigger/change set 有对应的 `semantic_scope_status: aligned`；缺失或过期时当前回合先完成只读 scope integrity review。门禁通过后直接执行，不只报告“可继续”、写 `owner_action_required` 或等待再次唤醒；门禁不通过时执行收缩、拆分、退回或必要决策，不继续原动作。只有 `next_actor=user`、动作超出合同、缺少真实授权/事实或存在真实 blocker 才请求用户；Heartbeat 回合若由 task/external 继续，则更新 locator、不执行额外动作，但仍输出一条 `DONT_NOTIFY`；普通非 Heartbeat Owner 回合无动作时可静默结束，不向任务或用户发送纯 ACK。

## 下游阶段事件与上行投递

任务内可以记录 `HEAD_CHANGED`、`CI_TERMINAL` 和 `REVIEW_TERMINAL`，但不得逐条上行。所有 `next_actor=owner` 的控制握手（`contract_ack`、`execution_release_ack`、`STARTED`）及需要立即处理的 `SCOPE_DELTA` / `BLOCKED` / `NEEDS_OWNER` / `PR_READY`、合同拒绝/漂移/锁权限异常，都必须主动投递真实 Owner；`COMPLETED` 仅由 Owner 在满足 [closeout contract](contracts.md#closeout-contract) 后发出。每个事件按 `local_recorded → delivery_pending → delivered → owner_verified → consumed` 记录，`task final` 不推进 Owner 状态。审查需要独立 review 时，按 exact reviewed head、被审 change set 的文件清单、空写入范围和完整 diff locator 绑定 verdict；后续 diff/head 立即作废，修复后 fresh review。

`event_key = task_key + execution_generation + event + head/status`；App 任务线程的 `execution_generation` 为 contract revision/digest，direct 为 spawn/dispatch generation。相同 key、旧 head、被较新事实覆盖或没有改变 `next_actor/next_action/wake_condition` 的事件直接静默丢弃。非紧急变化写入任务内唯一 `pending_delta`，新事实覆盖旧事实，下一次允许上行时一次带出。

所有 `next_actor=owner` 的事件必须通过宿主线程消息工具投递到真实 `owner_thread_id`，并携带 `event`、`task_key`、`execution_generation`、`event_key`、`next_actor`、`next_action`、`wake_condition`、`runtime_lock_revision` 和证据 locator。`SCOPE_DELTA` 还要携带变化区域、四类 trigger 中的命中项和受影响 ownership。任务先留本地短记录，调用工具并记录 message locator；不等待纯 ACK。Owner 收到消息或恢复回读后必须 `read_thread` + GitHub truth 验证，再把已验证 locator 写入自己的 checkpoint 与 owner_handoff。投递不可验证时标记 `<EVENT>_PENDING_DELIVERY`，在自身 final 中保留结构化事件、不推进 Owner 合同状态；Owner/Heartbeat 只补消费漏投、pending 和漂移，不承担正常 admission。不得引入数据库、文件 registry 或无限重试。

上述跨线程消息遵守 [双层消息与人类可读性](contracts.md#双层消息与人类可读性)：先用自然语言说明结论、影响/风险和下一步，再在末尾放最小 `<control>`；完整日志、证据清单和哈希集合不跨线程转发。纯 ACK、hold、release、`STARTED` 仍可保持短机器格式并内部化。

每次 Heartbeat 回合在当前 Owner 任务中只输出一条简短结果：无可执行变化为 `DONT_NOTIFY` 并说明 next actor/action 或等待方；需要用户决定或真实风险为 `NOTIFY`。禁止逐任务 head/push/CI/review 展开、纯“已回读/继续等待”ACK 和多条阶段播报；该结果是运行记录，不是任务线程 ACK。

## 既有 Owner 迁移

1. 识别旧 Heartbeat/合同中的无界并发、完整项目快照、逐 checkpoint 汇报或纯 ACK；停止新派发，读取活动任务的真实 thread/workspace/head 和当前 revision。
2. 发送 migration hold，允许任务完成当前原子写入/命令后在安全边界停止，并回报 `sealed_revision`、`cutover_head` 与 worktree 状态；回读后封存旧 revision，保留已有 worktree/branch 结果。
3. 原地更新同一 Heartbeat：改为绑定当前 Owner 的唤醒机制，加入稳定 owner_handoff 模板、`resolved_max_inflight` 的 host/user 来源、六项并发统计、`convergence_inflight=1`、上行门禁、事件去重、禁止向任务回纯 ACK 和 Heartbeat 单条结果；移除完整项目状态、无界并发、动态降 cap 和逐 checkpoint 汇报。保留 automation id、RRULE/间隔、通知策略和 Owner 已有授权，不创建第二个 Automation。
4. 递增 `handoff_revision` 与 `contract_revision`，重新执行完整合同、合同 ACK、release ACK 与 `STARTED` admission。封存后的旧 revision 消息只读合并到 pending_delta，不驱动动作；旧 task goal 为 `blocked`/`idle` 时，在新 revision admission 完成前不得声称继续实施。新合同显式接管 cutover head；所有活动任务完成新 revision admission 后才恢复派发。

## 策略违规

hold/release 与 `flat`/`direct` 下级衍生禁令都是协作策略，宿主没有已验证的原生写入锁或禁用开关。发现提前写入、digest 错配或越权衍生时暂停执行单元、回读影响并报告；不采用违规输出。其他无冲突任务继续。

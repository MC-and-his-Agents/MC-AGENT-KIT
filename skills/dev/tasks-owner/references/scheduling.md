# Tasks Owner 调度与 admission

本文件是 dynamic ready wave、容量统计、任务身份、防重和实现/收敛通道的唯一行为事实源。
Owner 控制循环见 [operations.md](operations.md)；本文件不决定目标是否值得做，也不把容量状态当作
目标完成证据。

## 容量与事实

每次 dispatch 先从宿主和用户事实解析一次全局上限，并把来源写入 checkpoint：

```text
resolved_max_inflight = min(host_cap, user_cap)
```

缺一取另一，两者都缺才取 `8`。只有用户修改 `user_cap` 或宿主提供可核验的 cap 变化时才重算；
Owner、Task、Heartbeat、风险、依赖、ownership、授权、admission、容量或 resource failure 不得
降低、动态减半或临时覆盖该值。

同时记录 target、actual 和 evidence locator：

```text
host_inflight                         # 宿主已占用的线程/任务槽
read_only_inflight                    # 只读、review 或无写 ownership 的在途任务
admission_pending                     # bootstrap/hold/ACK/release/STARTED 未核验或待创建
implementation_target_cap             # 本周期目标，必须等于 resolved_max_inflight
implementation_admitted_inflight     # 真实 admitted/active 实现任务
resolved_max_inflight                 # 唯一全局实现上限
slot_consuming_pending                # 有宿主槽但尚未成为实现 actual 的执行单元
dispatch_available_slots              # 本周期可创建的真实实现槽
```

`implementation_admitted_inflight` 只计入：App 任务具备真实 `task_thread_id`、稳定
`task_key`、正式 branch/worktree、完整合同、ACK/release/STARTED 和写 ownership；`direct` 具备真实
`agentId`、`workspace_entry`、五段 packet、核验过的 runtime evidence 和写 ownership。只读、
`BOOTSTRAP_READBACK`、`execution_hold`、`pending_contract`、`clientThreadId`、`idle`、`blocked`、
`goal blocked` 和计划数量都不计 actual。

```text
slot_consuming_pending = 有可核验 host 槽但尚未成为 actual 的 clientThreadId/bootstrap/pending/direct readback
dispatch_available_slots = max(
  0,
  min(resolved_max_inflight - implementation_admitted_inflight - slot_consuming_pending,
      host_cap - host_inflight)
)
```

`host_cap` 缺失时忽略第二项；同一执行单元不得重复扣除；没有 host locator 的计划不得计入
`slot_consuming_pending`。

## 稳定身份与 ready buffer

1. 一次性回读 GitHub truth 和现有线程，使用不可变 `task_key` 区分活动、待创建、已结束和状态不明。
   首次 admission 后，`task_key` 永久绑定一个 Issue、FR、milestone 或紧密 batch；线程不得跨目标、
   branch 或 ownership 复用。
2. 目标、Issue、FR、milestone、branch、worktree 或写入 ownership 错配时隔离旧线程并保留成果，
   为新目标创建新 `task_key`/线程；若新目标仍 ready，replacement 留在当前 ready wave。
3. 每次调度完整回读 `ready_task_keys`，按可核验硬依赖、具体写入/公共合同冲突、防重或用户 hold
   选择 `selected_wave`，直到 `dispatch_available_slots == 0` 或没有可 admission 的 ready task。
   只要 ready buffer 仍有可推进的后继，不能把“等下一次 Heartbeat”当作规划动作。
4. 每个空槽和每个未选 task 都写任务级 `not_selected_reason`，附 dependency/冲突 locator、
   合同/授权缺口、容量证据或 wake condition。不得用同仓库、同 milestone、同 target、hierarchical、
   单一收敛通道、一般谨慎或 Owner 偏好留空。
5. `actual_wave_width` 只记录本波真实完成 admission 的任务数。收口、merge、依赖解除或收敛通道
   释放后，在同一 Owner 控制周期回读并重算 ready wave，优先形成并 admission 下一项关键路径工作。

## Dispatch 与 admission 协调

- readiness 通过只是规划质量门禁，不是运行 admission。`planning_not_ready` 任务不得进入本节。
- `execution_ready` 不要求预先存在 branch/worktree、合同、任务 locator 或 runtime evidence；这些是
  本节 dispatch/admission 的产物与门禁。容量不足只使已选项等待真实槽位，不改变其工作分类。
- ready、可用槽且没有对应模式真实 locator 或可回读待创建 locator 时，状态回到
  `owner_dispatch_required`；branch/worktree/合同草稿不能冒充任务。
- `clientThreadId` 只表示宿主已占槽的待创建单元；它可计入 `host_inflight`、`admission_pending`、
  `slot_consuming_pending`，但不能计入 implementation actual，也不能重复创建。
- App 任务按 [contracts.md](contracts.md#admission-control) 的 `contract → contract_ack →
  execution_release → execution_release_ack → START → STARTED` 顺序 admission；direct 使用真实
  `agentId`、`workspace_entry`、packet 和 runtime evidence，不虚构 task thread。
- 派发后和接受结果前按 [runtime-and-review-evidence.md](runtime-and-review-evidence.md) 回读目标、
  model/effort、cwd/worktree/head、custom profile 和执行代次；缺失、矛盾或错配只隔离具体 task。

失败、速率限制、资源、worktree 或重复状态只影响具体 `task_key`，附 status、evidence 和 wake
condition；不改变全局 cap。补偿重试保持同一 `task_key` 并递增 `dispatch_generation`，不可无限重试。

## 实现、收敛与 ready successor

- `implementation_admitted_inflight` 受 target/resolved cap 约束；实现任务和只读/review 任务分开统计。
- 同一仓库与 target branch 的 `convergence_inflight` 默认上限为 `1`，只影响 merge/closeout 排队，
  不阻塞无冲突 implementation admission，也不改写 cap。
- PR candidate 取得收敛通道前，Owner 必须完成 [scope integrity](scope-integrity.md) 并取得
  `semantic_scope_status: aligned`；取得后一次消费最新 target head，完成 exact-head review、hosted
  CI、PR metadata 和 `PR_READY`。
- `convergence_generation` 在 merge/closeout、撤回、失败或真实 `BLOCKED`/`NEEDS_OWNER` 时释放；
  任务完成后仍有未完成目标时，回到 [operations.md](operations.md) 形成 successor Work Item。
- cleanup 是独立 lane，按 [cleanup.md](cleanup.md) 串行，不计实现 actual，也不以清理槽位降低 cap。

## Checkpoint 最小调度载体

```text
wave_id / ready_task_keys / selected_wave / actual_wave_width
host_cap / user_cap / resolved_max_inflight / implementation_target_cap
host_inflight / read_only_inflight / admission_pending
implementation_admitted_inflight / slot_consuming_pending / dispatch_available_slots
task_key -> threadId/agentId/clientThreadId -> dispatch_generation -> status
task_key -> branch/worktree/workspace_entry -> runtime_evidence_locator/status/target
task_key -> not_selected_reason / dependency_locator / last_capacity_failure
convergence_inflight / convergence_owner / convergence_generation / convergence_requested_at
```

这些字段只记录真实 locator 和短状态，不把完整项目快照、prompt、env、token 或日志写进 GitHub、
仓库或 handoff。

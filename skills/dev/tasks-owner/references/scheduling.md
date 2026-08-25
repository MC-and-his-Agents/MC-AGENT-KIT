# Tasks Owner 调度与 admission

本文件是 dynamic ready wave、容量统计、任务身份、防重和实现/收敛通道的唯一行为事实源。
Owner 控制循环见 [operations.md](operations.md)；本文件不决定目标是否值得做，也不把容量状态当作
目标完成证据。

## 有效交付批次与依赖

调度对象是“最小有效交付批次”，不是孤立的最小后继 Issue。两个以上候选若共享写入 carrier、验证矩阵和
closeout lane，默认合为一个 tight batch，并绑定一个稳定 `task_key`/ownership；只有以下任一真实证据存在时
才拆分：独立用户价值、独立风险/权限/数据边界、独立 ownership、真实 hard dependency，或独立回滚证据。
不得把整个 milestone 变成一个超级任务，也不得为填槽制造空批次。拆分要同时更新 acceptance/backlog matrix
和相邻 Work Item ownership。

依赖只按语义分类：`hard`（不满足就不能安全开始实现）、`soft`（只改变优先级或补充信息）、
`convergence`（只阻最终 merge、认证或 closeout）。`blocked-by` 只是 GitHub 声明事实，不是 hard 证明；父子、
同 milestone、同 target 或外部 blocker 也不会自动把后继传播为 blocked。只有逐条具备以下反事实证据的依赖
才能标为 `hard`；`residual_integration_boundary` 与 Issue 的 `deferred_boundary` 必须指向同一延期范围：

```text
dependency: <真实 locator>
unsafe_to_start_without: <缺失时为何连安全开始都不可能>
fixture_or_recorded_contract_insufficient_because: <为何固定证据、recorded contract、只读准备或隔离 carrier 不能先跑薄切片>
residual_integration_boundary: <哪些部分仍需真实上游；无残余则写 none>
deferred_boundary: <与 residual_integration_boundary 对应的延期完备性；无延期则写 none>
```

若 fixture、recorded contract、只读准备或隔离 carrier 足以安全开始某个薄切片，则该部分不得被整体 hard
阻塞；将薄切片 admission，只有仍依赖真实上游的 residual integration 才保留 `hard`。不能证明安全反事实的
依赖只可为 `soft`/`convergence`，或退回 readiness 补证。Owner 必须保留责任方、证据和 wake condition；residual
hard 只有在 resolution evidence 可回读且 wake condition 已验证时才算解除。blocked successor 可先由
Owner/direct Subagent/共享只读 checkout 完成 readiness；在 residual hard dependency resolution 和 verified
wake condition 之前禁止正式 execution branch/worktree、完整 contract 和 `START`，解除后在同一周期立即创建现场并
admission。resolution 可来自真实上游能力、权限、运行时或其他非 Git 条件，不要求存在 merge commit。

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
`task_key`、正式 branch/worktree、完整合同、ACK/release/STARTED、`delivery_route_status=armed` 和写 ownership；`direct` 具备真实
`agentId`、`workspace_entry`、五段 packet、核验过的 runtime evidence、native agent completion/wait locator 和写 ownership。只读、
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

## Admission 前 execution mode selection

在 capability compatibility 通过后、创建 branch/worktree 或发送 `START` 前，记录一次拓扑选择：

```text
execution_mode_selection:
  mode: <direct | flat | hierarchical>
  independently_admissible_subunits: <locators 或 none>
  write_carrier_overlap: <none | shared + locators>
  acceptance_and_rollback_independence: <verified | not_verified + evidence>
  critical_path_benefit: <true + 说明 | not_applicable>
```

`flat` 是单一 writer、共享 carrier、统一验证/收口路径的默认值；`hierarchical` 只有至少两个可独立 admission 的子单元、carrier 不相交、验收与回滚独立且确实缩短关键路径时才成立；`direct` 仅用于当前 Owner 回合可完成且由原生 wait 消费的有界动作。模式选择不改变容量、权限或 review 预算；未能证明独立性时保持 `flat`。

## 稳定身份与 ready buffer

1. 一次性回读 GitHub truth、acceptance/backlog matrix 和现有线程，使用不可变 `task_key` 区分活动、待创建、已结束和状态不明。
   GitHub acceptance、ownership、dependency、shared carrier 或 closeout consumer 任一变化，或
   `truth_revision`/`truth_digest` 与 checkpoint 不匹配，立即把 matrix 标为 `stale`；stale 时禁止声称
   backlog clear 或基于旧 matrix 新 dispatch，先刷新 `matrix_revision` 并重新回读 truth。
   首次 admission 后，`task_key` 永久绑定一个 Issue、FR、milestone 或紧密 batch；线程不得跨目标、
   branch 或 ownership 复用。
2. 目标、Issue、FR、milestone、branch、worktree 或写入 ownership 错配时隔离旧线程并保留成果，
   为新目标创建新 `task_key`/线程；若新目标仍 ready，replacement 留在当前 ready wave。
3. 每次调度完整回读 `ready_task_keys` 和矩阵未满足行，按可核验 hard 依赖、具体写入/公共合同冲突、防重或用户 hold
   选择 `selected_wave`，直到 `dispatch_available_slots == 0` 或没有可 admission 的 ready task。
   只要 ready buffer 仍有可推进的后继，不能把“等下一次 Heartbeat”当作规划动作。
4. 每个空槽和每个未选 task 都写任务级 `not_selected_reason`，附 dependency/冲突 locator、
   合同/授权缺口、容量证据或 wake condition。不得用同仓库、同 milestone、同 target、hierarchical、
   单一收敛通道、一般谨慎或 Owner 偏好留空。
5. `actual_wave_width` 只记录本波真实完成 admission 的任务数。收口、merge、依赖解除或收敛通道
   释放后，在同一 Owner 控制周期回读并重算 ready wave，优先形成并 admission 下一项关键路径工作。

6. 当 `goal_status=incomplete`、`resolved_max_inflight > 1` 且 `critical_path_width=1` 连续两个控制周期，
   同时 `truth_digest`/`state_digest` 未变化时，必须产生实际动作：重分类依赖、admission 可并行的 tight
   batch，或为每个剩余候选给出逐项不可并行证据与 `wake_condition`。仅写 `fanout_audit completed` 不算动作；
   已完整且仍有效的逐项证明可在 digest 未变化时复用，但必须保留 locator、复用原因和下一次 wake condition。
   `implementation_target_cap` 始终等于 `resolved_max_inflight`，Owner 不得降低 cap；occupancy、readiness/review、
   单一收敛 lane 和“2–3 条路径”都不是 implementation width 或新 cap 的替代。

## Dispatch 与 admission 协调

### 独立任务/Subagent runtime admission

调度器在创建、恢复和每次触发任务前都必须生成并显式传入以下参数；缺参即拒绝 admission，不能让宿主
默认值接管：

```text
App task:  model=gpt-5.6-luna, thinking=max
spawn_agent: model=gpt-5.6-luna, reasoning_effort=max
```

这些值只对独立任务/下游 Subagent 生效；Owner 继续使用自己的 `owner_runtime_lock`，发送方 runtime、
父任务当前 runtime、Heartbeat、旧合同、风险或容量不得覆盖下游。只有用户对具体 task 的
`task_runtime_override`（含授权 locator、模型、推理程度和明确传播范围）才可替换；未明确命名的派生
Subagent 仍回到 Luna/max。每个成功目标回合必须回读 `turn_context`，核对 task locator、model、effort、
contract digest/revision、override locator、时间和 workspace/head；缺失、Unknown model、不支持 reasoning、
静默 Terra/Sol/低 effort 或实际值不符都标 `TASK_RUNTIME_DRIFT`，隔离结果并 `fail closed`，不计 admitted。
宿主拒绝时保留 attempted runtime、错误和 wake condition，等待用户选择，不改配置、不重启、不静默降级。

活动任务 runtime audit/migration 只允许最小动作：`reopen_with_explicit_runtime`（可重新创建同一
`task_key`，递增 generation）或 `hold_for_user_choice`；保留旧成果和 locator，不改变 Owner runtime，且已有
成功 runtime evidence 不因重新阅读文档而失效。

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
- 每个 App bootstrap/full task prompt 必须携带 `upstream_delivery_contract`、`task_model` 和
  `task_reasoning_effort`；默认值只能是 `gpt-5.6-luna` / `max`，并必须与创建/恢复消息的
  `model`/`thinking` 参数逐字一致。任务在 contract_ack 后、
  release/START 前只主动调用一次 `codex_app__send_message_to_thread` 投递 `DELIVERY_ROUTE_ACK`，Owner 回读真实
  message locator、确认 `delivery_route_status=armed`，并验证 sender locator 与创建返回的真实 task locator
  一致且不等于 Owner thread。direct 免 route ACK，依赖 native agent completion/wait locator，不得永久 pending。
  `armed` 只允许继续完整 admission，不是结束或 admitted 证据；只有完整 admission 后满足
  [contracts.md](contracts.md) 的 `safe_sleep_predicate` 才能结束或进入 `waiting_task`。未 armed/错配保持
  `admission_pending`，本回合做有界 wait/read；task thread created、BOOTSTRAP active、发送 `START`、
  `BOOTSTRAP_READBACK`/task final 都不是交付或 admitted 证据。
- 派发后和接受结果前按 [runtime-and-review-evidence.md](runtime-and-review-evidence.md) 回读目标、
  model/effort、cwd/worktree/head、custom profile 和执行代次；缺失、矛盾或错配只隔离具体 task。

失败、速率限制、资源、worktree 或重复状态只影响具体 `task_key`，附 status、evidence 和 wake
condition；不改变全局 cap。补偿重试保持同一 `task_key` 并递增 `dispatch_generation`，不可无限重试。

## 实现、收敛与 ready successor

- `implementation_admitted_inflight` 受 target/resolved cap 约束；实现任务和只读/review 任务分开统计。
  `actual_wave_width` 只计真实 admission；readiness、review、occupancy 或计划数量不能冒充实现宽度。
- 同一仓库与 target branch 的 `convergence_inflight` 默认上限为 `1`，只影响 merge/closeout 排队，
  不阻塞无冲突 implementation admission，也不改写 cap。
- PR candidate 取得收敛通道前，Owner 必须完成 acceptance-derived preflight、[scope integrity](scope-integrity.md) 并取得
  `semantic_scope_status: aligned`；取得后一次消费最新 target head，完成 exact-head review、hosted
  CI、PR metadata 和 `PR_READY`。
- `convergence_generation` 在 merge/closeout、撤回、失败或真实 `BLOCKED`/`NEEDS_OWNER` 时释放；
  任务完成后仍有未完成目标时，回到 [operations.md](operations.md) 依据 matrix 形成最小有效 successor batch。
- cleanup 是独立 lane，按 [cleanup.md](cleanup.md) 串行，不计实现 actual，也不以清理槽位降低 cap。

收敛期间可以预塑形下一解锁：回读稳定的 successor Issue、依赖、只读 readiness 和 wake condition，但不把它当作正式 admission。hard/shared carrier/exact-main 未释放前，不创建正式 branch/worktree、完整合同或 `START`；释放且 readiness/capability/mode 通过后，同一控制周期可正式 admission。预算仍绑定当前 product exit、finding 因果链和 scope，不因 successor 预塑形而重置。

## Checkpoint 最小调度载体

```text
wave_id / ready_task_keys / selected_wave / actual_wave_width
host_cap / user_cap / resolved_max_inflight / implementation_target_cap
host_inflight / read_only_inflight / admission_pending
implementation_admitted_inflight / slot_consuming_pending / dispatch_available_slots
task_key -> threadId/agentId/clientThreadId -> dispatch_generation -> status
task_key -> branch/worktree/workspace_entry -> runtime_evidence_locator/status/target
task_key -> upstream_delivery_contract / delivery_route_status / delivery_route_locator / native_agent_locator
task_key -> execution_mode_selection / capability_compatibility / next_unlock_locator / next_unlock_status
execution_generation -> quarantine_status / slot_impact / replacement_forbidden
task_key -> not_selected_reason / dependency_locator / last_capacity_failure
acceptance_matrix_locator / matrix_revision / matrix_status / matrix_truth_revision / matrix_truth_digest
dependency_proof_locator / hard_dependency_proof_status / residual_integration_boundary / deferred_boundary
truth_digest / state_digest / fanout_audit_locator / fanout_action_locator / critical_path_width / critical_path_stable_cycles /
  implementation_width_reason / wake_condition
convergence_inflight / convergence_owner / convergence_generation / convergence_requested_at
```

这些字段只记录真实 locator 和短状态，不把完整项目快照、prompt、env、token 或日志写进 GitHub、
仓库或 handoff。

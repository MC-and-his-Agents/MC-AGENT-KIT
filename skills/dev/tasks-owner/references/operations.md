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

## Unified owner action loop、pre-final 与 safe-sleep 门（唯一控制面）

本节是所有 Owner 回合的唯一控制循环入口。用户事件、App task 事件、native Subagent
completion、Heartbeat、merge/closeout、依赖解除，以及 Owner 在 gate 前尝试写出的总结，都是
`control_trigger`，不是终态；它们只能启动或继续本循环。`next_actor`、`ready`、任务
`final`、handoff、摘要和 Heartbeat 文案不能替代本回合动作或证据。

```text
control_trigger = user_event | app_task_event | native_subagent_completion
                | heartbeat | merge | closeout | dependency_resolved
                | pre_final_attempt | owner_action_result

每个 control_trigger 在同一 Owner 回合执行：
  1. consume/verify：回读并核验触发事实、真实 locator、runtime、GitHub truth 和去重键；
  2. gap/matrix：更新目标差距、critical path、acceptance/backlog matrix 和责任归属；
  3. owner_action：执行 confirmed_owner_authority 内全部可执行 owner_action；不能用摘要跳过；
  4. recompute：重算依赖、ready wave、successor、容量、pending 和 admission；
  5. dispatch/admit：派发/推进所有当回合可安全执行的后继，或逐项记录真实
     waiting_task / waiting_external / waiting_user 的 evidence locator 与 wake condition；
  6. continue：owner_action 或投递/消费产生新 trigger 时，回到第 1 步，不得先 final。
```

native Subagent completion 特别要求：消费 completion 后，若目标仍 incomplete，Owner 必须在
同一回合重算 ready wave 并形成、readiness、派发和 admission successor；“已完成”“正在并行”或
“等下一次 Heartbeat”不能结束该回合。

### pre-final gate

任何自然语言 final、`DONT_NOTIFY` 或等待输出前，Owner 必须通过以下门；失败时继续循环并执行
owner action，不得以“无需用户操作”“已回读”“可继续”代替：

```text
pre_final_gate =
  control_loop_quiescent
  && no unconsumed/executable next_actor=owner event
  && no executable owner_action
  && ready_wave_recomputed
  && no ready successor requiring admission
  && current_generation_execution_units_inventory_complete with host readback evidence
  && no active native child without verified completion-wake evidence
  && every terminal/completed execution unit completion is owner_verified or consumed
  && (goal_incomplete
      || convergence_writer_quiescence == verified for current generation + exact head)
  && admission_pending == 0
  && every admitted task has runtime/workspace/head evidence
  && every App route is armed (direct has native completion/wait locator)
  && (goal_complete
      || every remaining gap is an evidenced waiting_task | waiting_external | waiting_user)
  && exhausted/quarantined pending has evidence + wake_condition
```

`pre_final_gate` 只引用本文件的控制循环和 [contracts.md](contracts.md) 的
`safe_sleep_predicate`；其他文件不得定义第二套“已完成/无需操作/正在并行”终态。
其中 `control_loop_quiescent` 仅表示本回合最后一次核验、owner_action、dispatch/admission 和 delivery
recovery 都没有产生新 trigger；它不是“没有任务”或 ready=0 的同义词。

`pre_final_attempt` 只表示一次 gate 前的 `attempted_summary`：在 `pre_final_gate` 之前写出摘要会
重新进入本循环，不能结束回合。通过门禁后才可写真正的 `final_output`；该 final 是本控制周期的完成输出，
不再把自身重新排队为 trigger，也不强迫已完成目标进入任一 `waiting_*` 状态。

### Execution-unit 与写入收敛门禁

每个实现 generation 的恢复索引都必须保留以下有界记录；它只描述当前 generation，不替代 GitHub、线程或
仓库事实：

```text
related_execution_units:
  - locator: <threadId | agentId>
    generation: <execution generation>
    role: <writer | reviewer | task | cleanup>
    is_writer: <true | false>
    kind: <app_task | native_subagent | cleanup_subagent>
    host_status: <running | quiescing | quiesced | terminal | unknown>
    write_authority: <active | revoked | none | unknown>
    host_quiesce_capability: <verified | unavailable | unknown>
    quiesce_ack_locator: <host locator or missing>
    revocation_evidence_locator: <host locator or missing>
    observed_at: <ISO-8601>
    wait_locator: <bounded wait locator or missing>
    completion_locator: <final/completion locator or missing>
    owner_consumption: <pending | verified | consumed>
execution_unit_inventory:
  generation: <current execution generation>
  host_readback_locator: <list_agents/task-state readback>
  observed_at: <ISO-8601>
  complete: <true only when host readback and listed locators match>
```

`inventory_complete` 不是 Owner 自报布尔值：必须用当前 generation 的 `list_agents`/任务状态回读证明宿主活动
单元集合与列表完全一致，并保存 locator 与时间；任何新 spawn、completion、归档或宿主状态变化都会使证明失效。

发布前执行 `convergence_writer_quiescence`：native writer 必须 `terminal`；App writer 只有在
`host_quiesce_capability=verified` 且 `quiesce_ack_locator`、`revocation_evidence_locator` 和 `observed_at`
均可回读时才可使用 `quiesced + revoked`。当前宿主没有该能力时一律等待当前 generation terminal。
门禁通过后重新读取 worktree diff、文件哈希、PR head，再绑定 fresh exact-head review。`review=ship` 不能覆盖
`writer=running`，也不能覆盖晚到 completion。
`convergence_writer_quiescence=verified` 必须同时保存 current generation、回读 locator、`verified_at`、diff/hash
locator 与 reviewed exact head；generation/head 或 writer 状态变化立即失效，禁止复用旧 `verified`。

cleanup 门禁还要求待清理的当前 generation 中所有既有 execution unit terminal、最终事件已
`owner_verified → consumed`，且 handoff 尚未删除活动 locator；pre-spawn inventory 不包含尚未创建的 cleanup
Subagent。满足后 Owner 才能派专用 Luna/max cleanup Subagent，随后独立回读 worktree/ref/remote 状态。任何
活动 writer、未消费 completion、handoff/宿主冲突都阻止 merge、cleanup 和 `COMPLETED`。

`direct` 路由只承载有界、预期在当前 Owner 回合完成的工作。创建 native Subagent 后，Owner 保持回合，以不超过
60 秒一段的 bounded native wait 消费 completion，并在同一回合继续 action loop；实际 `wait_agent.timeout_ms`
取 `10000..60000`。预计长时工作直接选 App task。
若 active native child 仍运行且没有经过验证的宿主 completion-wake 证据，Owner 不得 final 或进入
`safe_sleep_predicate`。Heartbeat 仅恢复漏消费，不是 direct 的正常推进器。

## Outcome-first 控制周期

每次控制周期都完成以下顺序；步骤可在一个回合连续完成，但不能用旧 ready/handoff 快照跳步：
先保证目标/scope 对齐和交付质量，再在真实依赖、ownership 与容量边界内最大化无冲突吞吐；不得用吞吐
掩盖跑偏或低质量，也不得用协议、检查清单或一般谨慎压低本可并行的推进。

1. **sync**：回读委任目标、GitHub/线程/worktree/PR/head、活动任务、`confirmed_owner_authority`、
   当前 checkpoint 和 `owner_handoff`。实时 GitHub/线程事实覆盖 handoff；漂移先修复并递增
   `handoff_revision`。
2. **gap / critical path**：判定目标 `complete | incomplete | unknown`，列出尚未满足的结果、关键路径、
   依赖、相邻 ownership、下一解锁条件和可复用的 ready buffer。`ready_task_keys` 只描述已形成的
   Work Item，不代表 backlog 已清空。首次调度、重大 closeout/replan 或用户效率复盘时，必须建立或刷新
   完整的 acceptance/backlog matrix；缺矩阵或任一验收项没有归属时，目标只能是 `incomplete`/`unknown`，
   不得声称“没有其他工作”。
3. **classify**：逐条路径按实时事实分类为 `execution_ready`、`owner_actionable` 或
   `external_blocked`；`next_actor`、ready 集、planning 状态和 handoff 只能作为提示，不能替代分类。
4. **owner action**：优先完成授权范围内可直接完成的动作：只读调查、Issue 创建/修订、tight batch
   shaping、合法拆分、依赖/归属修复、reassign、已授权 direct 调度或纠偏。direct 仍由原生 Subagent
   执行实现，Owner 不借此绕过 branch/worktree 与 admission 门禁。遇到产品含义、优先级、权限、隐私、
   风险或不可逆外部动作时转 `waiting_user`，不猜测。
5. **readiness / admission**：对要实施的 Work Item 执行 [issue-readiness.md](issue-readiness.md)，先核验首个消费者 capability 的存在性和 required/observed semantics。
   `ready` 且 `capability_compatibility=compatible|provided_by_current_batch|not_applicable` 后才按 [scheduling.md](scheduling.md) 选择 execution mode、计算容量、填 ready wave、创建任务并完成
   `contract_ack → execution_release_ack → STARTED` admission；每个 bootstrap/full task prompt 还必须携带
   `upstream_delivery_contract`；App task 在 contract_ack 后、release/START 前只用
   `codex_app__send_message_to_thread` 主动投递一次 `DELIVERY_ROUTE_ACK`，Owner 逐任务回读
   `delivery_route_status=armed`、真实 message locator，并验证
   sender locator 与创建返回的真实 task locator 一致且不等于 Owner thread；direct 免 route ACK，改用 native
   agent completion/wait locator。`armed` 只允许继续完整 admission，不是结束或 admitted 证据。
   只有完整 admission 后，目标 `goal_complete` 分支或目标 `goal_incomplete` 且满足 [contracts.md](contracts.md) 的
   `safe_sleep_predicate` evidenced waiting 分支才可结束/等待。未 armed/错配时保持 `admission_pending`，在当前回合做有界 wait/read 核验；
   `planning_not_ready` 不得绕过运行合同。
6. **supervise / correct**：回读任务真实 locator、runtime/head 和结果；按
   [scope-integrity.md](scope-integrity.md) 处理 `SCOPE_DELTA`、重复 blocker、下游反向冲突和语义漂移，
   不让 exact-head、CI、digest 或 review 通过替代归属判断。无冲突任务继续，不能全局停摆。
7. **converge / closeout / cleanup / replan**：授予收敛通道、核验 `PR_READY`、merge、Issue/carrier、
   target branch 和 [cleanup.md](cleanup.md) 后立即重新 sync。目标仍 incomplete 时，无论矩阵是否已有
   successor，都必须在当前控制周期重算 ready wave、形成/补 readiness 并完成下一项可安全 admission；不得把
   native completion、merge/closeout 或依赖解除后的 successor 留给下次 Heartbeat，也不得先输出总结。

完成上述步骤后才可运行 `pre_final_gate`；门禁未通过时，结果只能是继续控制循环或执行对应 Owner action，
不能写 `progressed`/等待或结束自然语言回合。

App task 的 delivery 规则在本循环中不可旁路：`delivery_mode=app_thread` 的 Owner↔Task 控制消息只能调用
`codex_app__send_message_to_thread({threadId: <真实目标>, model: <目标任务/Owner 合同 runtime>, thinking: <目标 effort>, prompt: <完整控制消息>})`；
`codex_app__read_thread` 和 `codex_app__wait_threads` 只做回读/等待。成功必须保存真实 message locator 并
回读目标线程唤醒；失败保持 canonical `event`，将 `delivery_state: pending` 与
`route_status: <EVENT>_PENDING_DELIVERY` 分离记录，不能把 pending 当 event、delivery 或唤醒证据。direct
Subagent 继续 native completion/wait，不调用 App 消息工具。

### Acceptance/backlog matrix

矩阵是 Owner 的短恢复索引，不是 GitHub 或仓库运行数据。每行至少写：

```text
acceptance -> Work Item/owner -> hard/soft/convergence -> shared carrier
           -> parallel lane -> closeout consumer -> locator/status
```

`acceptance` 必须覆盖成功、失败或不可用状态；一行可映射到 tight batch，但不能把多个无关用户价值
塞进 milestone 超级任务。只有所有行都有 Work Item/owner、依赖分类、carrier、lane 和 closeout consumer，
并且已回读 GitHub truth，Owner 才能声称 backlog 清空；matrix 只保留 locator/短状态。
`matrix_status=stale` 的触发条件是 GitHub acceptance、ownership、dependency、shared carrier 或 closeout
consumer 任一变化，或 `truth_revision`/`truth_digest` 与 checkpoint 不匹配。stale 时禁止声称 backlog clear，
也禁止基于旧 matrix 新 dispatch；本周期先刷新 matrix、递增 `matrix_revision` 并重新回读 GitHub truth，完成
后才可继续调度。

### 依赖分类与执行现场时机

依赖分类和 hard 证明以 [scheduling.md](scheduling.md) 为唯一语义源：`hard` = 不满足不能安全开始；`soft` =
只影响优先级或信息；`convergence` = 只阻最终 merge、认证或 closeout。`blocked-by`、父子、同 milestone 或同
target 关系不会自动传播 external blocker。控制周期消费依赖时，必须逐行回读 `dependency` locator、
`unsafe_to_start_without`、`fixture_or_recorded_contract_insufficient_because`、`residual_integration_boundary`
和对应的 `deferred_boundary`；二者必须指向同一延期范围，没有安全开始反事实证明的项不能 admission 为 hard。能
用 fixture、recorded contract、只读准备或隔离 carrier 安全开始的薄切片先行，仍需真实上游的残余集成保留
residual hard。Owner 仍须保留责任方、证据和 wake condition；residual hard 只有在 resolution evidence 可回读且
verified wake condition 满足后才解除。resolution 可是上游能力、权限、运行时或其他非 Git 条件，不要求 merge。

`goal_status=incomplete` 且 `resolved_max_inflight > 1` 时，若 `critical_path_width=1` 连续两个控制周期且
`truth_digest`/`state_digest` 未变化，本周期必须完成依赖重分类、可并行 tight batch admission，或逐候选不可并行
证据与 wake condition；单独写 `fanout_audit completed` 不足。truth/state 未变化且证明仍有效时可复用完整逐项
证明，但要留下复用 locator/原因。`implementation_target_cap = resolved_max_inflight` 不变；occupancy 不是效果，
readiness/review 不是实现槽，2–3 条真实路径也不是新 cap。

blocked successor 可以提前由 Owner/direct Subagent/共享只读 checkout 做 acceptance、依赖和验证 readiness；
在 residual hard dependency resolution 和 verified wake condition 前禁止正式 execution branch/worktree、完整
contract 或 `START`。依赖解除后同一控制周期立刻创建正式现场并 admission，不能把预读 checkout 当成已开始执行。

### 三类工作与实时分类

- `execution_ready`：Work Item 的 GitHub truth 和六项 readiness 齐全，真实硬依赖、写入 ownership 与
  用户 hold 均允许进入 scheduling。尚未创建 branch/worktree、合同、任务 locator 或 runtime evidence
  是 dispatch/admission 要完成的工作，不能把该 Work Item 降为 `owner_actionable` 或
  `external_blocked`；仅有“ready”标签或计划数仍不够。
- `owner_actionable`：Owner 在 `confirmed_owner_authority` 内本回合能完成的结果差距，包括调查、Issue
  shaping、tight batch 归并/拆分、依赖修订、ownership 纠偏或已授权 direct 调度；`planning_not_ready`
  属于此类候选动作，不是 external blocker。
- `external_blocked`：当前回合在既有授权、宿主能力和本地事实内无法解除的外部条件；必须保留 evidence
  locator、责任方和 wake condition。存在任何 owner-actionable 路径时不得整体归为 external。

### PMO 稀疏结果与 blocker/finding 路由

Unit Owner 不把内部控制循环上报成 heartbeat 表单；仅在会改变 PMO 全局判断时发送 `owner_sparse_delta`，字段细节和枚举以 [contracts.md](contracts.md#pmo--unit-owner-双向结果合同) 为唯一来源。最小内容是实际产品效果/证据、blocker、finding、scope change、`remaining_executable_surface` 和 `next_unlock`。

- **局部 blocker**：用普通语言指出缺什么、阻塞 shaping/admission/implementation/verification/release/acceptance 哪一阶段、未阻塞什么、独立安全增量、next actor、wake/invalidation 和证据；只限制本 Unit 的该阶段，Owner 仍推进剩余可执行面。
- **全局等待**：仅在没有剩余可执行面，且 next actor 为 PMO、外部或用户时成立；PMO 可据 delta 区分等待原因，不重审整个 Unit。
- **Finding**：分别记录 `exit_impact`、`treatment`、`authority`、`lifecycle`；`uncertain` 只允许暂时 hold，证据明确后必须入路。常规 finding 由 Unit Owner 自主处置；跨 Unit、超 product-exit 修复预算或出口裁决才上行 PMO，越过产品/成本/风险/权限边界才交用户。

PMO 只保留 admission/sparse-delta/convergence/next-unlock locator 与短状态，不新增 FINDING 事件或第二状态数据库。产品出口、finding 因果链与 scope 共用同一收敛预算；新 Issue、Owner 或 generation 不得重置，熔断只停止未经裁决的范围扩张。

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

- `goal_complete` / `completed`：所有目标验收、收口和必要 cleanup 事实已核验，`pre_final_gate` 通过后输出
  `final_output`；这是完成分支，不创建或伪造任何 `waiting_*`。
- `progressed`：完成了真实状态转换，重算后没有可立即执行的 Owner action；
- `waiting_task`：存在真实 `task_thread_id`、`agentId` 或已占宿主槽的可回读 `clientThreadId`；每个 App
  task 均已 `delivery_route_status=armed`、sender locator 已与真实 task locator 核对，direct 则有 native
  agent completion/wait locator，并记录 route/event locator、等待事件和 wake condition；没有可立即完成的
  Owner action。未 armed 只能保持 `admission_pending` 并在当前回合核验，不能休眠等待。该判断统一服从
  `safe_sleep_predicate`。
- `waiting_external`：所有剩余路径均已分类 `external_blocked`，每项有证据和 wake condition，且无
  owner-actionable 路径；
- `waiting_user`：确实需要用户决定产品、权限、风险、隐私、成本或不可逆外部动作边界。

`owner_dispatch_required` 是必须在本周期执行的 Owner action，不是终态；ready 有空槽且无真实任务或
待创建 locator 时，branch/worktree/合同草稿不能转成 waiting。Heartbeat 遵守同一终态：只有真实
`waiting_task` 或证实 all-external 的 `waiting_external` 才能输出一条简短 `DONT_NOTIFY`；ready=0、
planning_not_ready、stale handoff、统计矛盾或 `next_actor=owner` 且动作可执行时禁止 DONT_NOTIFY。合法
task wait 不忙轮询、不重复派发；合法 all-external 不创建占位工作。任何 `next_actor=owner` 事件若为仍可执行且
recovery 未耗尽的 `pending/unconsumed`、缺真实 message locator，或未完成 received/verified/consumed 记录，都禁止
`waiting_task`、`DONT_NOTIFY` 或结束回合；必须先完成交付，或保持 canonical `event` 并写
`delivery_state: pending` + `route_status: <EVENT>_PENDING_DELIVERY`，转 Owner action。
耗尽/quarantine 的 pending 仅在 evidence+wake_condition 完整且无 Owner action 时允许按 `safe_sleep_predicate`
等待外部/用户。
delivery recovery 不是无限队列：同一 `event_key` 在一个 `recovery_epoch` 内每控制周期最多一次、总计最多两次；若宿主无可执行投递/
唤醒能力或上限耗尽，保留 `delivery_violation`、`pending/missing evidence`、authority/host evidence
locator 和 `wake_condition`，转合法 `waiting_external`；需要用户选择替代通道/授权才转 `waiting_user`。
只有仍有可执行投递且未耗尽上限时禁止结束；新的外部事实或用户决定只开启新的 `recovery_epoch`，否则不重试。
达到两次上限后 quarantine 该 generation，记录 slot impact，禁止 admitted、replacement 或重复 dispatch，
并引用 [contracts.md](contracts.md) 的 `safe_sleep_predicate`。

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
pmo_admission_contract_locator / owner_sparse_delta_locator
remaining_executable_surface / parent_outcome_locator / product_exit_locator
convergence_chain_locator / finding_budget_status / next_unlock_locator / next_unlock_status
task_key -> threadId/agentId/clientThreadId -> status
task_key -> contract_revision/digest/runtime_lock_revision/status
task_key -> workspace_entry/runtime_evidence_locator/status/target
<scheduling.md> 的 wave/cap/target/actual/pending/slot 统计与任务级理由
<scope-integrity.md> 的 semantic_scope_checkpoint/status/evidence
acceptance_matrix_locator / matrix_revision / matrix_status / matrix_truth_revision / matrix_truth_digest /
  missing_acceptance_rows
dependency_proof_locator / hard_dependency_proof_status / residual_integration_boundary / deferred_boundary
truth_digest / state_digest / fanout_audit_locator / fanout_action_locator / critical_path_stable_cycles /
  implementation_width_reason / wake_condition
control_signals_locator: first_review_pass / acceptance_coverage_per_merge / same_carrier_pr_count /
  event_to_action_latency / critical_path_width / admitted_one_owner_actionable_remaining
convergence / cleanup 状态与 evidence locator
event_key -> event=<canonical> / delivery_state=local_recorded | pending | delivered | owner_verified | consumed
event_key -> received_at / verified_at / consumed_at / message_locator
task_key -> upstream_delivery_contract / delivery_route_status / delivery_route_locator / native_agent_locator
execution_generation -> quarantine_status / slot_impact / replacement_forbidden
related_execution_units -> locator / generation / kind / host_status / write_authority /
  role / is_writer / host_quiesce_capability / quiesce_ack_locator / revocation_evidence_locator /
  observed_at / wait_locator / completion_locator / owner_consumption
execution_unit_inventory -> generation / host_readback_locator / observed_at / complete
convergence_writer_quiescence -> status / evidence_locator / verified_at / reviewed_head
heartbeat_cadence -> base_interval / current_interval / unchanged_epochs / cadence_revision / reason /
  override / last_user_feedback_revision / last_external_fact_revision / state_digest
event_key -> delivery_recovery.attempt_in_cycle / total_attempts / max_attempts / executable_action
event_key -> authority_locator / host_evidence_locator / retry_eligible_after
next_actor / next_action / wake_condition / last_event_key / pending_delta / updated_at
```

`owner_handoff` 只是一份紧凑恢复索引：保留 Owner 合同/范围 locator、next actor/action、wake condition、
活动任务 locator、收敛 owner/generation、未决决定和最近实质事件；不保存完整项目状态、所有 head、
日志、prompt、env、token、完整 matrix 或完整指标。恢复时交叉核对实时 GitHub、线程和 worktree，冲突以实时事实为准；
Automation 只唤醒 Owner，不是事实数据库或权限来源。

### 效率反馈

控制周期可用以下信号调整下一波的 batch shaping、fan-out 和纠偏顺序：`first-review pass`、`acceptance
coverage per merge`、`same-carrier PR count`、`event-to-action latency`、`critical-path width`，以及
`implementation_admitted_inflight=1` 时剩余 `owner_actionable` 数量。它们是本地 checkpoint 的短状态/locator，
不是新的 cap、数据库或 handoff 全量快照；occupancy 只能说明占用，不能证明效果。

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

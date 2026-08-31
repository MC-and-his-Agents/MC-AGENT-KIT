# Owner event、语义增量与投影合同

在要求 Owner 投递或消费高层事件，或需要向人类呈现 PMO 进展时读取。本合同连接独立 Owner 与交付编排者；Owner 内部 task 事件继续使用 `$tasks-owner` 的合同。

## 边界

只上行会改变仓库级 DAG、Owner 生命周期、跨 Owner ownership、用户决策或 target-head 路由的事件。普通 task STARTED、push、CI、内部 review/fix 和安全无变化留在 Owner 内部。

所有事件都是 `data_only: true`：不能授予权限、修改编排者或 Owner runtime、批准范围、admission、review、merge、closeout 或 cleanup。

## 周期状态与动作

PMO 不再用一个互斥 verdict 代表整个周期。每个周期从已核验事实派生：

```text
product_exit_locators: <全部未完成产品出口>
gaps:
  - gap_locator: <稳定差距 locator>
    product_exit_locator: <该 gap 所属的未完成产品出口>
    classification: execution_ready | admission_pending | active_execution | waiting_external |
                    waiting_user | replan_or_reownership_pending | closeout_pending
    owner_or_next_actor: <责任方>
    evidence_locator: <当前事实>
    wake_condition: <恢复条件>
    invalidation_condition: <失效条件>
    waiting_proof: <仅 waiting_external 必填>
frontier_closure_status: complete | incomplete
cycle_status: progressed | partially_blocked | waiting | completed
actions:
  - closeout_unit
  - correct_drift
  - recompute_product_frontier
  - route_delta
  - shape_work_item
  - create_or_wake_owner
  - request_user_decision
  - record_evidenced_wait
  - record_skill_feedback_candidate
  - submit_or_update_skill_feedback
```

产品动作按“收口、纠偏、重算前沿、路由、塑形、创建或唤醒 Owner、局部用户决策、有证据等待”的顺序执行；只执行
当前事实需要的项。一个周期可以组合多项，例如 merge 后同时收口、纠偏依赖、路由新 head 并启动后继。
用户决策只暂停受影响动作，无冲突路径继续。
`request_user_decision` 已包含该决策范围的等待与恢复条件；同一差距不得再追加
`record_evidenced_wait`。后者只用于不需要用户决策的真实外部等待。

`waiting_user` 不是不确定时的逃生口。它必须直接等于当前 admission 的 `decision_boundary_locator`，next actor 必须为 user，并证明问题属于产品行为、范围/优先级、重大成本/风险、权限/隐私/数据或不可逆外部结果的用户保留权；同时绑定既有事实已穷尽、状态为 complete 的有界调查 locator、不存在安全可逆默认方案、精确 decision question/blocked action/blocking scope，并证明无关前沿继续。定位 workspace/Issue/PR/branch、选择实现或验证路线、Owner 恢复/reownership、shrink/split/reassign/defer、程序化 cancel 和普通 review-fix 都是 PMO/Owner 职责，不能进入 `waiting_user`。只能由用户执行但不需要产品判断的机械动作归 `waiting_external` 并提供现有 waiting proof；`waiting_user` 不得附加第二套 waiting proof。
每个未完成出口和 gap 必须恰好出现一次。只有 `frontier_closure_status=complete`，且所有剩余 gap 都是
`active_execution`、`waiting_external` 或 `waiting_user`，整个周期才可等待。`waiting_external` 的 proof 必须有
subject、不可替代 external condition、responsible party、evidence locator、observed_at/freshness、wake 与
invalidation；缺任一项即改为 `replan_or_reownership_pending`。Issue 仍 OPEN、历史 blocked-by/handoff、旧 external
描述、`ready=0` 或没有 writer 都不是等待证明。关系、merge、Owner、外部事实或用户纠偏变化时，同周期失效旧 proof
并重算；漏掉一个出口或仍有 owner-actionable gap 都不能返回 `waiting`。
`complete` 只证明枚举、分类与证据闭包完整；即使仍有 execution/admission/replan/closeout 动作也应为 complete，
并在同一周期继续执行。只有未知或漏项才是 incomplete。重算触发已执行时，即使最终 closure 已恢复 complete，
`actions[]` 仍记录 `recompute_product_frontier`。

`record_skill_feedback_candidate` 和 `submit_or_update_skill_feedback` 是低优先级治理动作，不改变产品
`semantic_revision`。只有当前产品动作已经完成、候选已到期，并通过 canonical repository、GitHub capability、去重
和脱敏检查时，才可提交或补充反馈；每周期最多一次外部写入。canonical 仓库不要求逐次反馈授权；非 canonical
写入仍使用普通用户授权。目标不匹配、工具不可用、去重不完整或不能安全脱敏时只保留候选。

- `progressed`：完成了产品推进动作，且没有必须等待的受影响差距。
- `partially_blocked`：完成了可执行产品动作，但仍有局部用户决策或有证据等待。
- `waiting`：没有可执行产品动作，所有剩余差距都有合法等待证据。
- `completed`：总体产品出口已有真实证据，且收口完成。

旧的 `KEEP_CURRENT` 等标签只可作为兼容投影或人类摘要，不能掩盖 `actions[]` 中仍需执行的动作。

## 唯一 authority contract

`pmo_authority_contract` 是唯一的 PMO 授权事实，必须有唯一 `contract_locator`、`digest`、`revision`，并与用户来源、仓库和 target 范围、产品/优先级基线、规划与依赖关系写权、Owner 创建/恢复、finding 裁决、merge/closeout、重试/收敛、排除项、独立的 automation 授权，以及 `observed_at`、`expiry`、`invalidation` 交叉绑定。合同不授予新权限；authority checkpoint/handoff 只保存该合同的 `contract_locator`、`digest`、`revision`、`freshness`、`status` 和合同恢复位置，运行 checkpoint 的最小索引仍按 [automation.md](automation.md) 执行。

合同有效且可回读时按原授权恢复；缺失、过期或冲突时只暂停受影响动作并记录 wake condition，不能从历史行为、Issue、Heartbeat、摘要或工具成功反推权限。规划、关系、Owner、finding、merge 和 closeout 仍分别受合同边界约束。

## 一个事实、三层投影

通信分为三层，不能把任一层直接当成另一层：

1. **底层事件**：Owner event、heartbeat、receipt、GitHub 或 host 变化。它们服务于恢复、核验和路由，不自动成为用户消息。
2. **产品语义变化**：把同一权威证据在当前 `delivery_unit`/产品出口下与上一个已核验事实比较，只有目标、产品效果、风险/阻塞、责任/动作或用户决策含义发生实质变化时才成立。
3. **用户通知**：产品语义变化的 human projection。没有 semantic delta 时不生成；有变化也先按产品结果聚合，紧急事项才立即绕过聚合。

### Canonical delivery fact（唯一交付事实）

canonical delivery fact 是唯一的产品交付事实，不是新数据库或新的 PMO 状态对象。它必须能回溯到已经权威的 GitHub、Owner `owner_sparse_delta` locator、thread、worktree 或其他 evidence locator，并在同一事实中确定：

- 产品出口/目标及本次产品效果（或明确 `no_change`）；
- 真实风险、阻塞或失效条件（没有则为 `none`）；
- 下一责任方与动作、wake condition；
- `execution_generation`、只在产品含义改变时递增的 `semantic_revision`，以及发生/观察时间语义；
- 可回读的证据 locator。

PMO 只消费 `$tasks-owner` 已定义的 `owner_sparse_delta` locator，不重新定义 Unit 内 schema。human projection 与 machine projection 都从这个事实派生，互不回写产品判断，也不各自持久化一份事实。

### Human projection（人类投影）

human projection 是面向管理判断的普通中文语义合同，不是固定的五栏表单。可按场景压缩成一句或数句，但读者必须能直接判断（不适用项可省略）：

- 目标是什么；
- 产品事实发生了什么变化；
- 真实风险或阻塞是什么；
- 下一步由谁做什么；
- 是否需要用户决策。

默认摘要不展示完整 event envelope、receipt、generation/digest、DAG、checkpoint、Skill rules、长 SHA、prompt 或工具日志。需要审计时只给短的 evidence locator，并按需展开技术附录；locator 不能替代摘要中的产品含义。

用户决策的 human projection 必须给出：可选项、推荐项及理由、各选项影响，以及不响应时的默认后果。不要把原始协议字段伪装成选项或推荐。

### Machine projection（机器投影）

每个 canonical event 可以有 machine projection；只有 `notification-worthy` semantic delta 才有 human projection。机器投影只保留恢复、去重、路由和核验真正需要的最小事实：

```text
machine_projection:
  schema: pmo-machine-projection.v1
  event_identity:
    event: <canonical event>
    event_key: <stable event identity>
  source:
    repo_locator: <唯一仓库>
    target_ref: <目标 ref>
    delivery_unit: <stable task_key/scope locator>
    owner_thread_id: <真实 Owner threadId 或 none>
  generation:
    execution_generation: <执行代次>
    semantic_revision: <产品语义修订；无变化不递增>
  time:
    occurred_at: <事实发生时间，或 unknown + reason>
    observed_at: <发送方观察时间>
  receipt:
    received_at: <接收时间或 missing>
    verified_at: <核验时间或 missing>
    consumed_at: <消费时间或 missing>
  product_effect: <kind/status + outcome locator；不得复制完整摘要>
  next_actor: <orchestrator | owner | user | external>
  next_action: <一项短动作>
  wake_condition: <下一次可执行条件>
  invalidation_condition: <何时事实失效>
  evidence_locator: <GitHub/thread/host locator>
```

上例中的 receipt 时间仍由现有 `receiver_receipt` 记录；machine projection 只引用同一记录，不创建第二份 receipt。`runtime_lock_revision`、`observed_head`、`terminal_reason` 等既有字段继续保留在下方 immutable payload 中，只在相应事件需要恢复、路由或核验时使用。

## 通知判断与聚合

投影层在生成用户消息前给当前 canonical fact 一个短暂的派生结论：

- `silent`：重复 `event_key`、重复 receipt/heartbeat、陈旧 generation、相同 `semantic_revision`，或产品含义没有变化；不通知。
- `aggregate`：存在产品语义变化，但不是需要立即打断用户的风险或决策；把同一产品出口/结果链上的 Owner、CI、PR、merge 等工程事实聚合成一条产品摘要，机器事件仍逐条保留。
- `immediate`：真实产品阻塞、关键路径改变、security/safety、权限或数据损失风险、已承诺动作被 invalidation，或 `next_actor=user` 的决策；不得等待聚合窗口。

聚合是生成 human projection 时的派生判断，不是队列、消息总线或独立状态源。聚合依据同一产品出口/结果 locator、连续的语义修订和可回溯的 source evidence；不要用“最后一条事件”覆盖并发 Owner，也不要丢弃机器事件。

## Freshness 与去重

时间和身份含义必须分开：

- `occurred_at` 是事实在来源发生的时间；
- `observed_at` 是发送方看到该事实的时间；
- `attempted_at` 是一次投递尝试的时间；
- `received_at`、`verified_at`、`consumed_at` 是接收方 receipt 生命周期时间。

时间用于审计和 latency，不以晚到的 wall-clock 覆盖较新的 generation/revision。`execution_generation` 表示执行生命周期，`semantic_revision` 只在产品意义改变时递增，`delivery attempt` 只表示重试：

1. 相同 `event_key` 的重试保持相同 canonical fact 和 semantic revision，只增加 sender-local attempt；不产生用户通知。
2. 低于当前已核验 generation 的重放是 stale；可保留机器证据用于恢复/审计，但不得更新产品进展、覆盖 cursor 或通知用户。
3. 同一 generation 中，未产生新 semantic revision 的 receipt、heartbeat、CI 状态或路由变化不得伪装成新进展。
4. 新 generation/revision 或真实产品效果、风险、next action、wake/invalidation 变化才进入 `aggregate` 或 `immediate` 判断。
5. 缺少发生时间时必须显式 `unknown` 并保留证据；不能用 receipt 时间冒充 occurred time，也不能因无法排序就猜测新进展。

### canonical disposition 优先级

持久来源中较新的 `OWNER_TERMINAL`、`RETHINK`、`SHIP`、`interrupted` 或 `scope-violation` 原子淘汰旧 checkpoint 的 `active|waiting`。prompt、摘要、Owner 静默回合和 direct delivery 丢失都只是投影事实，不能覆盖可回读的 canonical disposition。

在诊断、替换或中断 Owner、读取冻结 carrier 之前，必须先比较 canonical cursor/generation；冲突时最多做一次定向回读。若较新事实为终态，同周期将 writer width 归零，重规划并只重算受影响的 Unit、Parent、Milestone 与 successor；不得先执行上述恢复副作用。已消费或更旧事实的重放保持幂等，不重复回读、重算或通知。较新 `active` 事实则继续路由真实 delta，作为普通路径的 proceed-control。

## 不可变事件 payload

只有 notification decision 为 `aggregate` 或 `immediate` 且存在 human projection 时，默认人类消息才附最多三行普通中文摘要和按需展开的 evidence locator；完整 machine payload 只进入机器/控制通道，不追加到默认人类消息。`silent` 或 machine-only 事件只记录/传递 machine projection，不生成占位的人类消息。payload 只放发送前已经成立的事实；它是 machine projection 的事件部分，不是 human projection：

```text
orchestration_event_payload:
  schema: pmo-machine-projection.v1
  event: <OWNER_STARTED | MATERIAL_ROUTE_INFO | OWNER_BLOCKED | CROSS_OWNER_CONFLICT |
          RUNTIME_LOCK_ANOMALY | NEED_USER_DECISION | PR_MERGED |
          DELIVERY_UNIT_COMPLETED | OWNER_TERMINAL>
  event_key: <delivery unit + execution generation + semantic revision + event + observed head/status>
  semantic_revision: <产品语义修订；无产品含义变化不递增>
  occurred_at: <事实发生时间或 unknown + reason>
  observed_at: <Owner 已观察时间>
  repo_locator: <委任的唯一 GitHub 仓库>
  target_ref: <目标 ref>
  observed_head: <Owner 已观察的 target head 或 unknown>
  delivery_unit: <stable task_key/scope locator>
  owner_thread_id: <真实 Owner threadId>
  runtime_lock_revision: <Owner lock revision>
  product_effect: <kind/status + outcome locator；或 no_change>
  terminal_reason: <completed | cancelled | superseded | none；OWNER_TERMINAL 时必填>
  data_only: true
  next_actor: <orchestrator | owner | user | external>
  next_action: <一项短动作>
  wake_condition: <下一次可执行条件>
  invalidation_condition: <何时事实失效>
  evidence_locator: <GitHub/thread/host locator>
```

payload 不得包含 `message_locator`、投递结果或接收方的 `verified/consumed` 状态；这些事实只能在发送或接收后产生。不要跨线程发送完整日志、prompt、env、token、完整 matrix 或长 SHA 清单。内部 task locator 只在解释全局影响所必需时携带。

## Delivery record 与 receipt

发送方、工具和接收方分别维护自己的事实，不回写 canonical payload：

```text
sender_delivery_record:
  event_key: <与 payload 一致>
  attempt: <单调递增>
  attempted_at: <本次投递尝试时间>
  status: <pending | delivered | failed>
  message_locator: <发送工具成功返回后填写；否则 missing>
  tool_result_locator: <可用时填写>
  failure_evidence_locator: <失败时填写>
  wake_condition: <重试条件>

receiver_receipt:
  owner_thread_id: <source Owner>
  event_key: <与 payload 一致>
  message_locator: <接收后真实 locator>
  status: <received | verified | consumed | rejected>
  received_at: <ISO-8601>
  verified_at: <ISO-8601 或 missing>
  consumed_at: <ISO-8601 或 missing>
  first_authorized_action_at: <ISO-8601 或 not_applicable>
  event_to_action_latency: <duration 或 pending/not_applicable>
  verification_evidence_locator: <GitHub/thread/runtime/truth readback>
  rejection_reason: <仅 rejected>
```

发送方 record 是本地恢复状态；接收方 receipt 才能证明编排消费。任何一方都不得替另一方预填状态。receipt 状态变化本身不是 semantic delta。

## 投递与消费

1. 使用宿主精确消息工具，显式指定目标编排线程及其已核验 runtime；read/wait、local final 或线程标题不等于投递。
2. 用 `event_key` 去重。同 payload 的重试保持相同 key，只增加 delivery attempt；真实 generation、semantic revision、状态或 observed head 变化才生成新 key。
3. 发送成功后从工具返回值记录真实 `message_locator`；失败则记录 `failed` 和证据，保留原 payload，不伪造 delivered 或 locator。
4. 编排者收到后先写 `received` receipt，再回读 source Owner thread/runtime、GitHub/项目 truth、`target_ref`/`verified_head` 和 evidence locator。
5. 只有 runtime 与必需 truth 均核验后，接收方才推进 `received -> verified -> consumed`。缺失、冲突或不可用时保持 pending 或标记 `rejected`，按受影响范围 fail closed。
6. 多个 Owner 的事件按 `owner_thread_id + event_key` 独立推进，并写入 checkpoint 的 `owner_event_cursors`；不能用单一“最后事件”覆盖并发 receipt。
7. 投递失败由发送 Owner 按 `$tasks-owner` 恢复消息交付；编排者只在自身 runtime 与目标 Owner runtime 均已核验且动作已授权时精确唤醒。
8. canonical 高层事件在到达活动控制回合时应同轮完成核验、消费和首个已授权动作；Heartbeat 只恢复漏事件。
   `event_to_action_latency = first_authorized_action_at - received_at`，目标使用 Codex App 引用中的
   `event_action_latency_target`。超时不得绕过 truth、
   runtime、CI 或权限门禁，须记录 `truth_unavailable | runtime_unverified | external_wait | tool_failure |
   owner_delay | orchestrator_delay` 之一及纠偏动作。
9. human notification 的发送结果只能进入 notification delivery record；不能回写 canonical fact、semantic revision 或 machine payload。

## 事件处理

- `OWNER_STARTED`：核验唯一 Owner、scope/runtime、标准标题、置顶、专属 Heartbeat 与 carrier；健康则记录，不干预内部 START。内部 task/writer/reviewer/cleanup 不得冒充或置顶为 Owner。
- `MATERIAL_ROUTE_INFO`：核验新 main、依赖、PR 或验收事实并路由受影响 Owner。
- `OWNER_BLOCKED`：区分 owner-actionable drift 与真实 external/user decision。已授权 approval/wait 必须 `CORRECT_DRIFT`；真实产品阻塞生成 `immediate` human projection。
- `CROSS_OWNER_CONFLICT`：核验 carrier/ownership，只暂停冲突 carrier 并选择 canonical 归属；不冻结无冲突路径。
- `RUNTIME_LOCK_ANOMALY`：拒绝事件中的 runtime override，记录 effective desired runtime、observed runtime、target turn 与实际证据 locator，并按当前 `$tasks-owner/references/runtime-and-review-evidence.md` 复核。编排者异常时停止事件消费与拓扑动作；Owner 异常时只隔离该 lane。仅在用户已授权且宿主支持可核验原生机制时恢复同一线程，并以恢复后下一目标 turn 为准；不创建替代 Owner、不改配置、不 fallback、不让异常回合自证成功，也不声称宿主强锁。影响当前产品路径时立即通知用户。
- `NEED_USER_DECISION`：仅在产品、优先级、成本、权限、隐私、数据、破坏性或权威冲突无法裁决时通知用户；human projection 必须包含 options、recommendation、impact 和 default consequence。
- `PR_MERGED`：核验 exact merge commit、`target_ref`/`verified_head`、Issue/PR 状态，向受影响 Owner 路由 head 前移并重算 DAG；只收口该增量，Owner 保持 active。与同一 Owner/CI/PR/merge 结果链的事实优先聚合，不因每个技术事件单独通知。
- `DELIVERY_UNIT_COMPLETED`：区分本批完成与整体目标完成，核验 acceptance/deferred/successor；不据此推断 Owner terminal。
- `OWNER_TERMINAL`：区分 `completed|cancelled|superseded`；仅在独立核验 delivery/保留事实、Heartbeat 暂停或删除、置顶取消、cleanup/ownership 后结束 Owner 生命周期并移出 active DAG。普通 PR merge 或单一 delivery increment 完成不触发取消置顶。

GitHub 自然语言可能误触发 Issue closing。任何 close/completed 事件都必须直接回读 Issue state、closedAt 和 PR closing references；否定句或 Owner 摘要不能作为状态证据。

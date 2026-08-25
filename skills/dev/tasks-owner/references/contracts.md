# Tasks Owner admission、消息与收口合同

只在 Owner 激活、创建/恢复任务线程、接收控制事件或 closeout 时读取。本文件只定义接口字段、握手、
消息投递和完成证据；目标控制循环见 [operations.md](operations.md)，调度事实见
[scheduling.md](scheduling.md)，Heartbeat 见 [automation.md](automation.md)。

## confirmed_owner_authority 接口

Owner contract 必须原样保留用户已经明确确认的授权范围，不得由 Skill、合同、Heartbeat、handoff、
Issue 或历史动作生成或扩展：

```text
confirmed_owner_authority:
  source: <用户明确确认的消息/合同 locator>
  actions: <逐项、可审计的已确认动作范围>
  exclusions: <未授予或明确禁止的动作>
  automation: <另行确认的 Automation 范围；缺失即未授权>
```

缺字段、未确认或动作超出范围时保持只读并请求用户；不得将其表述成 standing envelope、长期高影响
权限或隐含授权。

## Owner contract schema

```text
owner_thread_id: <真实 threadId>
owner_model: <默认 gpt-5.6-sol>
owner_reasoning_effort: <默认 high>
owner_runtime_lock: <下方完整 canonical lock>
owner_runtime_lock_status: <verified | unverified>
confirmed_owner_authority: <上方接口对象>
execution_mode: <direct | flat | hierarchical>
luna_subagent_status: <supported | probe_ready | fallback | pending_restart | unverified>
scope_locator: <GitHub milestone/FR/Issue>
planning_truth_locator: <已回读的目标、依赖和归属>
delivery_batch: <最小有效交付批次 / tight batch locator>
acceptance_matrix_locator: <Owner checkpoint matrix locator>
dependency_classification: <hard | soft | convergence + evidence>
contract_revision: <单调递增整数>
contract_digest: <规范字段 canonical JSON 的 SHA-256>
related_execution_units: <当前 generation 的执行单元恢复索引>
convergence_writer_quiescence: <pending | blocked | verified + current generation/exact head/diff/hash/host evidence locator/verified_at>
heartbeat_cadence: <base/current interval, unchanged epochs, revision, reason>
```

`luna_subagent_status: fallback` 仅可记录历史/诊断事实，绝不表示任务可 admission 或可消费；新建、恢复和
消息触发若实际不是合同 runtime 必须走 `runtime_status: failed`/`TASK_RUNTIME_DRIFT` 的 fail-closed 路径。

### 任务 runtime contract（独立任务与派生 Subagent）

任务 runtime 与 Owner runtime 是两条隔离链。除非用户在**具体任务授权**中以可定位的
`task_runtime_override` 明确指定其他模型/推理程度，否则每次独立任务线程的创建、恢复和消息触发都必须
显式传入：

```text
task_model: gpt-5.6-luna
task_reasoning_effort: max
runtime_source: tasks_owner_default
runtime_override: none | <用户授权 locator>
runtime_propagation: task_only | task_and_named_descendants
```

`runtime_override` 只能改变该任务及合同明确的传播范围；不得从 Owner 当前 runtime、父任务当前 runtime、
Heartbeat、旧合同、风险推断或宿主默认值覆盖。`task_and_named_descendants` 也必须把同一用户授权 locator
写入每个明确命名的下游合同；未命名下游仍使用 Luna/max。主 Owner 的 `owner_runtime_lock` 永不被任务
配置反向修改。

direct/hierarchical/flat 中每个 `spawn_agent` 都必须显式传入
`model: "gpt-5.6-luna"`、`reasoning_effort: "max"`（或合同批准的 task-specific override）；不得省略参数、
静默 fallback Terra/Sol/低 effort，或用发送方 runtime 代替目标 runtime。独立 App task 的创建和每一条
触发 Owner→Task 消息同样必须显式携带目标任务的 `model` 与 `thinking`，不能把 Owner 的模型参数透传给任务。

宿主拒绝/Unknown model/不支持 reasoning 时，保留 `attempted_model`、`attempted_reasoning_effort`、目标 locator、
错误和时间，标记 `runtime_status: failed`，fail closed：不消费结果、不 admission、不 merge/closeout，不修改
`~/.codex`、不自动重启、不改用其他 runtime；只有用户明确选择后才恢复。已有成功的目标 runtime evidence
不得因重新阅读模板而重新卡 Luna 门禁。

最小活动任务 runtime audit/migration：Owner 每次创建、恢复、消息触发及接受结果前，回读目标回合
`turn_context`，逐字段核对 `task_model/task_reasoning_effort`、任务 locator、时间、合同 digest/revision 和
override locator；缺失/矛盾/静默 fallback 只隔离该 task，记录 `TASK_RUNTIME_DRIFT` 和迁移动作
`reopen_with_explicit_runtime | hold_for_user_choice`，不改变 Owner runtime，不把旧结果计入 admission。

`contract_digest` 只证明字段未被改写，不证明 GitHub 目标或实际 change set 语义正确；首次 admission、
合同语义修订、scope delta、review finding disposition、修复回合、收敛和 `PR_READY` 仍须执行
[scope-integrity.md](scope-integrity.md) 的独立检查。

### Execution-unit 与 generation 状态

Owner 对每个实现 generation 保留有界的 `related_execution_units`，不得只依赖任务摘要或最新 final：

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
    wait_locator: <bounded native wait locator or missing>
    completion_locator: <final/completion locator or missing>
    owner_consumption: <pending | verified | consumed>
execution_unit_inventory:
  generation: <current execution generation>
  host_readback_locator: <list_agents/task-state readback>
  observed_at: <ISO-8601>
  complete: <true only when host readback and listed locators match>
```

`inventory_complete` 必须由当前 generation 的 `list_agents`/任务状态回读证明宿主活动单元集合与上述列表一致；
它不是可自由填写的布尔值。任何 spawn、completion、归档或宿主状态变化都会使证明失效。

写入单元在 `terminal` 前保持 `write_authority=active`。native writer 只接受 terminal；App writer 只有
`host_quiesce_capability=verified`、真实 `quiesce_ack_locator`、`revocation_evidence_locator` 与 `observed_at`
齐全时才可使用 `quiesced + revoked`。当前宿主没有可靠暂停/撤权证据时禁止推断 quiesced。
`convergence_writer_quiescence` 必须在
stage、commit、push、PR、merge 前通过；通过后重新读取 diff、文件哈希和 exact head，再派 fresh review。
`review=ship` 与 `writer=running` 同时出现时一律 fail closed。
`convergence_writer_quiescence=verified` 还必须绑定 current generation、宿主回读 locator、`verified_at`、
diff/hash locator 与 reviewed exact head；generation/head 或 writer 状态变化立即使它失效。

## canonical owner runtime lock（回显锁）

这是 Skill 层的 compensating control，不是宿主强写入锁，也不授予新权限：

```text
owner_runtime_lock:
  model: gpt-5.6-sol
  reasoning_effort: high
  revision: 1
  authority: user
```

四个字段整体进入 Owner contract、活动任务 contract、`contract_digest` 和 checkpoint。锁只能由用户
修改；修改时递增 revision、重算 digest，并让活动任务重新 admission。`verified` 只表示工具参数与目标
回读相互匹配；没有宿主强制证据就记 `unverified`，不声称宿主会执行回显。

任务或 Subagent 使用 Codex App 的 `codex_app__send_message_to_thread` 唤醒 Owner 时，实际参数必须逐字回显锁：
`model: owner_runtime_lock.model`、`thinking: owner_runtime_lock.reasoning_effort`；宿主参数名是
`model`/`thinking`，不得改成 `target_model`。控制块只携带 `runtime_lock_revision`。锁缺失、格式/摘要/
revision/支持性异常，或目标 `turn_context` 无法回读/不一致时，保持 canonical `event`，并写
`delivery_state: pending`、`route_status: <EVENT>_PENDING_DELIVERY`、`failure_code: RUNTIME_LOCK_ANOMALY`、
`message_locator: missing`（或具体错误 locator），暂停受影响 admission、派发、merge、closeout 和外部动作。
`codex_app__read_thread`/`codex_app__wait_threads` 只用于回读或等待，不能替代消息投递；泛称
`send_message_to_thread` 也不是可接受的 App 投递工具。direct native agent 走原生 completion/wait，免除 App
消息工具要求但仍须留下可回读 locator/status。

Owner 与独立 Codex App task thread 的双向通信只能调用精确工具
`codex_app__send_message_to_thread`：Owner→Task 的 hold、contract、release、`START`、纠偏，以及
Task→Owner 的 ACK、readiness、阻塞、scope、PR/完成事件都适用。只有该工具成功返回可回读结果，且目标
thread 经 `codex_app__read_thread` 核验后，才能推进 delivery/admission；本地 final、泛称工具、
`codex_app__read_thread` 或 `codex_app__wait_threads` 都不构成投递。direct native agent 不创建独立 App task
thread，继续使用 native orchestration completion/wait。

方向与参数不得含糊：

```text
Owner → Task:
  codex_app__send_message_to_thread({
    threadId: <创建返回且已回读的真实 task_thread_id>,
    model: <该 task contract.task_model，默认 gpt-5.6-luna>,
    thinking: <该 task contract.task_reasoning_effort，默认 max>,
    prompt: <完整 hold/contract/release/START/纠偏控制消息>
  })

Task → Owner:
  codex_app__send_message_to_thread({
    threadId: <真实 owner_thread_id>,
    model: <owner_runtime_lock.model，默认 gpt-5.6-sol>,
    thinking: <owner_runtime_lock.reasoning_effort，默认 high>,
    prompt: <canonical event + 最小控制块>
  })
```

`threadId` 必须是消息目标而非发送方或 display name；`prompt` 必须包含自然语言摘要和最小
`<control>`，不得用空 prompt、local final、read/wait 结果或日志代替。目标 runtime 不能从发送方 runtime
推导：Owner→Task 用任务合同，Task→Owner 用 canonical Owner lock；direct native completion/wait 不调用
App 消息工具。

## Admission control

### Bootstrap hold

新建、恢复、模式切换、模型覆盖或 lock revision 变化先发送只读 hold：

```text
owner_thread_id: <真实 Owner threadId>
task_key: <GitHub Issue/FR/batch locator>
execution_hold: true
目标摘要: <短摘要>
```

任务此时只能回报真实 `task_thread_id`、branch/worktree/head、模型/推理程度和 runtime locator。只有
真实任务或宿主返回可回读 `clientThreadId` 才能处于 hold；branch/worktree/合同草稿不能冒充任务。若该批次
仍有未解除 `hard` dependency，hold 只能支持只读 readiness/共享 checkout，不得建立正式 execution
branch/worktree、完整 contract 或 `START`；Owner 用 `task_thread_id + branch + absolute_worktree + head`
构造正式 `workspace_entry`，只存 Owner checkpoint/App 运行态，除非 `AGENTS.md` 明确要求，不写 GitHub 或仓库。

### Upstream delivery contract

每个 bootstrap prompt 和完整任务 prompt 都必须原样携带 `upstream_delivery_contract`；它是任务向 Owner
主动回报的路由合同，不是任务自行改写目标 runtime 的权限：

```text
upstream_delivery_contract:
  delivery_mode: <app_thread | direct>
  owner_thread_id: <真实 Owner threadId>
  sender_locator_kind: <task_thread_id | clientThreadId | agentId>
  sender_task_thread_id: <完整合同固定真实 task threadId；bootstrap 可留空>
  expected_sender_locator: <bootstrap 的 clientThreadId 或 direct agentId；解析后升级>
  message_tool: codex_app__send_message_to_thread
  owner_runtime_lock: <canonical owner_runtime_lock 原样回显>
  event_revision: <contract/dispatch revision>
  event_digest: <contract digest>
  event_key: <稳定 task + revision + event + head/status key>
  human_summary: <自然语言摘要>
  failure_code: <MESSAGE_DELIVERY_FAILED | DELIVERY_VIOLATION | CONTRACT_REJECTED | CONTRACT_DRIFT>
  failure_route_status: <EVENT>_PENDING_DELIVERY（仅 delivery/route 状态，不是 event）
```

任务不得自行改写 `owner_thread_id`、目标 runtime、锁或 event revision/digest。App task thread 在
`CONTRACT_ACK` 后、`execution_release`/`START` 前必须先用 `codex_app__send_message_to_thread` 主动投递一次
`DELIVERY_ROUTE_ACK`（包含真实 message locator、`sender_locator_kind` 和 sender locator），再写本地 final；
每个 `task_key + execution_generation` 只允许一次。bootstrap 只有 `clientThreadId` 时以
`sender_locator_kind=clientThreadId + expected_sender_locator` 绑定；解析出真实 `task_thread_id` 后升级并核对，
完整合同再固定 `sender_task_thread_id`。`direct` 模式明确免此 route ACK，改由 native agent completion/wait
locator 完成 route gate，不能永久保持 pending。`local_recorded`/task final 不等于 delivered、armed 或 consumed。

### Complete contract fields

bootstrap 回读后，Owner 发送同 revision/digest 的完整合同；至少包含：

```text
owner_thread_id / task_thread_id / task_key
issue_readiness: ready
planning_truth_locator / scope_locator
delivery_batch / acceptance_matrix_locator
contract_revision / contract_digest
owner_runtime_lock / owner_runtime_lock_status / runtime_lock_revision
upstream_delivery_contract / delivery_route_status / delivery_route_locator
execution_hold: true
milestone / FR / Issue / 用户价值 / 目标 / 非目标 / 验收
hard dependencies / soft dependencies / convergence dependencies
允许写入的仓库、文件、branch、正式 worktree、workspace_entry
禁止修改的 carrier、公共接口和越界边界
execution_mode / task_model / task_reasoning_effort / subagent_policy
OBJECTIVE / FILES AND OWNERSHIP / INTERFACES / CONSTRAINTS / VERIFICATION
汇报门禁 / PR_READY 条件 / evidence locator
```

### PMO ↔ Unit Owner 双向结果合同

PMO 的 admission 只提供一个 `pmo_admission_contract` locator；以下是 Unit Owner 对该 locator 的字段解释和回报边界，避免 PMO references 复制可漂移 schema：

```text
pmo_admission_contract:
  product_goal: <产品目标>
  expected_contribution: <本 Unit 对产品出口的预期贡献>
  acceptance: <可观察验收与失败/不可用出口>
  allowed_scope: <允许写入与实现范围>
  excluded_scope: <明确排除范围>
  convergence_chain:
    product_exit_locator: <产品出口/Parent locator>
    repair_budget: <finding 修复回合；本批为 1>
    reset_forbidden: true
  authority_boundary:
    unit_owner: <自主实现、测试、finding、PR、merge、closeout、cleanup>
    pmo: <跨 Unit、超预算、出口与 DAG/范围裁决>
    user: <产品/成本/风险/权限边界外的决定>
  baseline:
    exact_main: <exact-main SHA>
    evidence_locators: <基线证据>
  next_unlock: <可执行下一解锁与 wake condition>
```

Owner→PMO 只在全局判断会改变时发送稀疏 `owner_sparse_delta`；普通内部步骤不发送 heartbeat 表单、全量状态或新事件/状态源：

```text
owner_sparse_delta:
  product_effect: <实际产品效果与证据 locator>
  blocker: <none 或以下结构>
    missing: <缺什么>
    blocking_stage: <shaping | admission | implementation | verification | release | acceptance>
    not_blocking: <没有阻止什么>
    independent_safe_increment: <可独立完成的安全增量或 none>
    next_actor: <unit_owner | pmo | user | external>
    wake_condition: <唤醒条件>
    invalidation_condition: <失效条件>
    evidence_locator: <证据>
  finding: <none 或以下结构>
    finding_locator: <finding 证据>
    exit_impact: <blocks_current_exit | does_not_block_current_exit | uncertain>
    treatment: <fix_now | defer_followup | reject_not_applicable>
    authority: <unit_owner_authorized | pmo_authority_required | user_authority_required>
    lifecycle: <pending_evidence | decided | in_progress | verified | closed>
    evidence_locator: <证据>
  scope_change: <none 或 scope delta locator/短状态>
  remaining_executable_surface: <短状态与证据 locator>
  next_unlock: <下一解锁与 wake condition locator>
```

`uncertain` finding 可以暂时 hold，但证据明确后必须进入 treatment/authority 路线。`exit_impact` 不自动决定 treatment；`fix_now` 仍受 [scope-integrity.md](scope-integrity.md) 的验收、不变量和 generation-wide 修复预算约束。预算绑定同一 product exit、finding 因果链与 scope，不能用新 Issue、Owner 或 execution generation 重置；熔断只停止未经裁决的范围扩张，不削弱已证明的质量门禁。

`planning_not_ready` 或 GitHub truth 缺失时不发送完整合同、不 admission；`issue_readiness` 只证明规划
字段，不替代运行态合同、runtime evidence、scope integrity 或用户授权。

### Fixed handshake

Admission 严格使用以下顺序，不以 final、标题、wait 结果或 branch/worktree 跳步：

```text
Owner → Task: contract
Task → Owner: contract_ack
Task → Owner: DELIVERY_ROUTE_ACK (once, before release/START)
Owner → Task: execution_release
Task → Owner: execution_release_ack
Owner → Task: START control
Task → Owner: STARTED
Owner: codex_app__read_thread + GitHub truth + runtime evidence → admitted/active
```

任务收到合同后先在自身会话写 `contract_ack: local_recorded`，再用锁定的
`codex_app__send_message_to_thread` 投递真实 Owner；Owner 回读 `codex_app__read_thread`、GitHub truth 和 runtime evidence 后
才消费并发送 release。`execution_release_ack`、`STARTED` 也必须由任务主动投递；缺失、错配、不可验证
或 release ACK 前写入均保持 `pending_contract`，隔离且不采用输出。START control 是执行许可，任务投递
`STARTED` 后可继续执行，不等待 Owner 纯 ACK。App task 必须在 contract_ack 后、release/START 前主动投递
`DELIVERY_ROUTE_ACK`；Owner 只有逐任务回读 `delivery_route_status=armed`、真实 locator，并验证
bootstrap 的 `expected_sender_locator` 或完整合同的 `sender_task_thread_id` 与创建返回的真实 task locator
一致且不等于 `owner_thread_id` 后，才能标记 `armed` 并继续完整 admission；`armed` 不是结束或 admitted 证据。
direct 以 native agent completion/wait locator 通过同一 gate。工具 accepted 不等于 armed。未 armed/错配时保持 `admission_pending`，在当前回合做有界
wait/read 核验；不得以“无需操作”“正在并行”、task thread created、`BOOTSTRAP_READBACK` final、发送
`START` 或任一 task final 冒充交付/实现 admission。

首次写入的最低事实是：真实 `task_thread_id != owner_thread_id`、稳定 `task_key`、正式 branch/worktree、
已回读 `workspace_entry`、完整合同、ACK/release/STARTED、写 ownership、当前/目标 head 和 runtime evidence。
`direct` 没有 task thread 时使用真实 `agentId`、workspace_entry、五段 packet 和已核验 runtime evidence；
不虚构 task thread。下游不得自行衍生不在合同中的任务。

## 双层消息与交付状态

除纯 ACK、hold、release、STARTED 等内部握手外，Owner↔Task 消息必须先有自然语言摘要，再有最小
`<control>`；删除控制块后仍能读到结论、影响/风险和下一步。用户 final 不展示控制块或握手字段。

```text
结论：<发生了什么>
影响/风险：<对目标、admission 或 closeout 的影响>
下一步：<由谁执行什么，证据在哪里>

<control>
event: <DELIVERY_ROUTE_ACK | contract_ack | execution_release_ack | STARTED | BOOTSTRAP_READBACK |
FINAL_BATCH_READINESS | PLANNING_READINESS | CONVERGENCE_REQUEST | SCOPE_DELTA | BLOCKED | NEEDS_OWNER | PR_READY | COMPLETED>
task_key: <稳定 task_key>
execution_generation: <contract revision/digest 或 dispatch generation>
event_key: <task_key + execution_generation + event + head/status>
next_actor: <owner | task | user | external>
next_action: <短动作或等待原因>
wake_condition: <可执行条件>
runtime_lock_revision: <锁 revision>
sender_locator_kind: <task_thread_id | clientThreadId | agentId>
sender_task_thread_id: <真实 task threadId；bootstrap 可空>
expected_sender_locator: <bootstrap expected locator>
message_locator: <真实 message locator；缺失写 missing evidence>
delivery_state: <local_recorded | pending | delivered | owner_verified | consumed>
route_status: <pending | armed | EVENT_PENDING_DELIVERY>
failure_code: <NEEDS_OWNER 时必填：CONTRACT_REJECTED | CONTRACT_DRIFT | RUNTIME_LOCK_ANOMALY | DELIVERY_VIOLATION>
evidence_locator: <消息/线程/GitHub/PR/head locator>
</control>
```

`event` 和 `event_key` 只能使用上方 canonical 枚举及其稳定键，例如 `STARTED`、`PR_READY` 或
`NEEDS_OWNER`；不得生成 `STARTED_PENDING_DELIVERY`、`PR_READY_PENDING_DELIVERY` 等伪事件。投递失败的唯一
结构是：

```yaml
event: STARTED
event_key: <task + generation + STARTED + status>
delivery_state: pending
route_status: STARTED_PENDING_DELIVERY
failure_code: MESSAGE_DELIVERY_FAILED
message_locator: missing
```

成功取得真实 locator 后只推进 `delivery_state: delivered`（再由 Owner 核验、消费），清除 pending route
状态；不得在已 delivered/verified/consumed 的事件上继续写 `*_PENDING_DELIVERY=true`。`route_status` 的
`EVENT_PENDING_DELIVERY` 是失败/恢复状态而非 event 枚举。

成功路径必须同时清除此前同一 `event_key` 的 `failure_code`、缺失/错误 host evidence 和 pending route 字段；
恢复后的 canonical 事件只能沿 `delivered → owner_verified → consumed` 前进。若成功 locator 与 pending/failure
仍并存，视为合同漂移，停止 admission、merge、closeout 和 cleanup，重新执行该 generation 的 delivery recovery。

控制块条件门禁：当 `delivery_state: pending` 时，`failure_code` 必填，`message_locator` 必须为
`missing` 或宿主返回的错误 locator，且 `evidence_locator`（必要时连同 `host_evidence_locator`）必须记录
缺失/错误来源；不能只写一个 pending 布尔值。`delivery_state: delivered` 及以后必须有真实
`message_locator`，再分别补 `received_at`、`verified_at`、`consumed_at`（或等价回读 locator）。
`event=NEEDS_OWNER` 的 `failure_code` 仍只允许 `CONTRACT_REJECTED | CONTRACT_DRIFT |
RUNTIME_LOCK_ANOMALY | DELIVERY_VIOLATION`；投递失败的其他 canonical event 使用
`MESSAGE_DELIVERY_FAILED`，不把失败状态改名为 event。

`delivery_mode=app_thread` 的所有 `next_actor=owner` 事件（至少 `DELIVERY_ROUTE_ACK`、`contract_ack`、`execution_release_ack`、`STARTED`、
`BOOTSTRAP_READBACK`、`FINAL_BATCH_READINESS`、`PLANNING_READINESS`、`CONVERGENCE_REQUEST`、`SCOPE_DELTA`、
`BLOCKED`、`NEEDS_OWNER`、`PR_READY`、`COMPLETED`、合同拒绝/漂移/锁权限异常）必须调用
`codex_app__send_message_to_thread({threadId: owner_thread_id, model: owner_runtime_lock.model,
thinking: owner_runtime_lock.reasoning_effort, prompt: <control>})` 请求唤醒真实 Owner。每次投递在任务会话留短记录，
不得把完整日志、证据清单、env、token 或完整 SHA 集合跨线程转发。必须先调用消息工具并取得真实
message locator，再写本地 final；工具失败保持 canonical `event`，写 `delivery_state: pending`、
`route_status: <EVENT>_PENDING_DELIVERY`、`failure_code` 和缺失/错误证据。即使 local final，仍保留最小 control
envelope（event、generation、event_key、next_actor、evidence/message locator、delivery_state/route_status）
供 recovery 使用，但不推进 delivered/armed/consumed。

`direct` 的 owner-facing 结果只通过 native orchestration completion/wait locator 返回，不调用 App 消息工具。

合同拒绝、合同漂移和 runtime lock 异常统一使用 `event=NEEDS_OWNER`，并填写对应 `failure_code`；
`*_PENDING_DELIVERY` 是 delivery/route status，不是 event 枚举。

每个事件严格单向推进：

```text
local_recorded → pending → delivered → owner_verified → consumed
```

每个事件还必须记录 `message_locator`、`received_at`、`verified_at`、`consumed_at`（或等价的可回读 locator）。
所有 `next_actor=owner` 事件都要求真实 locator；缺 locator、工具失败、锁/目标 runtime 无法核对或状态不明时
保持 canonical `event`，写 `delivery_state: pending`、`route_status: <EVENT>_PENDING_DELIVERY`、
`failure_code` 和缺失/错误证据，本地 final 不推进合同状态。只要存在仍可执行且 recovery 未耗尽的
`pending`/`unconsumed` Owner 事件，Owner 不得进入 `waiting_task`、`DONT_NOTIFY` 或结束回合，必须先投递、
核验并消费；耗尽/quarantine 的 pending 只有在 evidence+wake_condition 完整且无 Owner action 时，才能按
`safe_sleep_predicate` 转 `waiting_external/user`，不伪造 delivered/consumed。
每个相同 `event_key` 在一个控制周期最多执行一次可验证的 delivery recovery，跨周期总尝试最多 `2` 次，
并记录：

```text
delivery_recovery:
  event_key: <稳定 event_key>
  recovery_epoch: <外部事实/用户决定代次>
  attempt_in_cycle: <0 | 1>
  total_attempts: <0..2>
  max_attempts: 2
  executable_action: <true | false>
  authority_locator: <用户/合同授权 locator>
  host_evidence_locator: <宿主能力/错误/返回值 locator；缺失写 missing evidence>
  retry_eligible_after: <新外部事实或用户决定；否则 hold>
```

若宿主始终不能提供可回读的 message locator/wake 能力，或 `total_attempts=2` 已耗尽，绝不伪造
`delivered`、`owner_verified` 或 `consumed`；保留 `delivery_violation`、`pending/missing evidence`、
`authority_locator`、`host_evidence_locator` 和 `wake_condition`，并分类为合法 `waiting_external`。只有
需要用户选择替代通道、补充授权或确认不可逆风险时才转 `waiting_user`。在仍有
`delivery_recovery.executable_action=true` 且未耗尽上限时，禁止等待、`DONT_NOTIFY` 或结束回合；新的外部事实
或用户决定前不得再次尝试。新的外部事实或用户决定只开启新的 `recovery_epoch`（保留旧证据并在该 epoch
重新从 0 计数），不得把同一无变化的 Heartbeat 当作新事实。相同 generation/head/status 的重复事件静默丢弃；新 revision/digest 或真实状态变化
必须保留。Owner 收到事件后先 `codex_app__read_thread` + GitHub truth + runtime evidence 核验，再更新 checkpoint/handoff
并消费，不让 Heartbeat 承担正常 admission。

唯一安全静默/等待谓词 `safe_sleep_predicate`：

```text
safe_sleep_predicate =
  no pending/unconsumed next_actor=owner event with executable_action=true and recovery not exhausted
  && every App task route is armed (or direct has native agent locator/status)
  && current_generation_execution_units_inventory_complete with host readback evidence
  && no active native child without verified completion-wake evidence
  && every terminal/completed execution unit completion is owner_verified or consumed
  && (goal_incomplete
      || convergence_writer_quiescence == verified for current generation + exact head)
  && admission_pending == 0
  && every admitted task has runtime/workspace/head evidence
  && no executable owner_action
  && exhausted/quarantined pending has evidence + wake_condition
  && (goal_complete
      || (goal_incomplete
          && legal waiting_task | waiting_external | waiting_user is evidenced))
```

`goal_complete` 是完成分支：通过前述无 pending/action/route/admission 门后可直接 `final_output`，不必伪造
`waiting_*`。只有 `goal_incomplete` 才要求后面的合法 evidenced waiting；`COMPLETED`/`goal_complete` 不是新的
等待状态。

`direct` 仅适用于当前 Owner 回合内可完成的有界工作。Owner 创建 native Subagent 后必须保持回合，并以不超过
60 秒一段的 bounded native wait（实际 `wait_agent.timeout_ms=10000..60000`）消费 completion；checkpoint 保存 child/generation、`wait_locator`、completion
与 consumption locator，并证明当前 turn 尚未 final。不能在 child 仍运行时写 final。若工作预计长时或超过该边界，
应在 admission 时选择 App task 的精确消息唤醒路径；Heartbeat 只负责异常漏消费恢复，不能作为 direct 的正常推进器。

其他文件只引用此谓词，不另行定义“无需操作/正在并行”或等待条件。达到同一 `event_key` 的 recovery 上限
后，隔离并 quarantine 该 `execution_generation`，保留 slot impact、pending/violation/evidence；禁止计入
admitted、replacement 或重复 dispatch，直到新的外部事实/用户决定解除 quarantine。

`HEAD_CHANGED`、push、CI pending/success、review pending/success 可留任务内；仅当它们改变 Owner 的
决策时合并为一次 `NEEDS_OWNER`，不逐条通知。

Heartbeat 首次发现 `next_actor=owner` 事件漏投、未验证或未消费时，将其记录为 `delivery_violation`，立即
纠偏投递并要求 Owner 消费；它是审计/漏投恢复，不是正常控制队列、数据库或常驻 supervisor。

## PR_READY 与 closeout contract

任务只能报告 `PR_READY` 或局部完成，不能自行发 `COMPLETED`。`PR_READY` 必须绑定 acceptance-derived
`preflight_locator/preflight_status: ready`、exact reviewed head、准确 reviewed files、空 review write
scope、完整 diff locator、验证结论、`semantic_scope_status: aligned` 和 hosted/PR metadata 终态；后续
diff/head 使旧 verdict 失效，修复后 fresh preflight/review。

审查 finding 的处理还必须满足 [scope-integrity.md](scope-integrity.md) 的 admission 与 generation-wide
修复预算：每个 finding 有 disposition、当前验收/不变量映射或现实 P0/P1 风险证据；同一
`task_key + scope_revision` 在首次 finding-driven 写入后不得启动第二轮。只有有证据的更窄新 task_key
才可重新计数；`user_decision` 必须带真实产品、权限或外部结果决策 locator；reviewer 不得写入修复。

Owner 只有独立回读以下事实后才写 `closeout_verified`：目标验收通过；PR 已 merge 或有明确无需 PR 的依据；
merge commit 与 target branch 可验证；GitHub Issue 状态和适用 repo carrier/current pointer 已同步；
外部状态与仓内事实一致。缺项保持 `NEEDS_OWNER`/`BLOCKED`，不把 PR/head 当完成证据。

`closeout_verified` 后按 [cleanup.md](cleanup.md) 的 `cleanup_key`/generation、exact path/ref/OID 和
逐项授权执行清理；cleanup lane 串行、不得改代码/GitHub truth/保护分支。只有 Owner 独立回读
`cleanup_verified`，或用户明确选择全部 `preserve`，才允许 `COMPLETED`。`cleanup_pending`、
`cleanup_partial`、`cleanup_blocked` 不能冒充完成。

最小 closeout 控制事件：

```text
event: PR_READY | COMPLETED
task_key: <稳定 task_key>
execution_generation: <代次>
event_key: <唯一事件键>
next_actor: owner
next_action: <核验 PR_READY 或收口证据>
wake_condition: <可回读的 head/merge/cleanup 条件>
evidence_locator: <PR/commit/Issue/carrier/cleanup locator>
runtime_lock_revision: <锁 revision>
```

## rollback boundary

- 派发前：可撤回建议，不产生任务状态。
- 已创建未写入：暂停/归档对应 task，并在 checkpoint 记录取消原因。
- 已有 branch/PR：停止继续写入，保留可审计证据；关闭/删除按 Owner 与 cleanup 合同执行。
- 已进入 cleanup：保存每个 ref 删除前 exact OID；部分成功只保留未完成资产和恢复建议，不重建已删资产。
- 已执行外部可见或不可逆动作：不承诺自动回滚，立即停止并交由用户决定。

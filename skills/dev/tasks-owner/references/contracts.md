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
contract_revision: <单调递增整数>
contract_digest: <规范字段 canonical JSON 的 SHA-256>
```

`contract_digest` 只证明字段未被改写，不证明 GitHub 目标或实际 change set 语义正确；首次 admission、
合同语义修订、scope delta、重复 blocker、收敛和 `PR_READY` 仍须执行
[scope-integrity.md](scope-integrity.md) 的独立检查。

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

任务或 Subagent 使用宿主 `send_message_to_thread` 唤醒 Owner 时，实际参数必须逐字回显锁：
`model: owner_runtime_lock.model`、`thinking: owner_runtime_lock.reasoning_effort`；宿主参数名是
`model`/`thinking`，不得改成 `target_model`。控制块只携带 `runtime_lock_revision`。锁缺失、格式/摘要/
revision/支持性异常，或目标 `turn_context` 无法回读/不一致时，事件写为
`<EVENT>_PENDING_DELIVERY` 或 `unverified`，暂停受影响 admission、派发、merge、closeout 和外部动作。

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
真实任务或宿主返回可回读 `clientThreadId` 才能处于 hold；branch/worktree/合同草稿不能冒充任务。Owner
用 `task_thread_id + branch + absolute_worktree + head` 构造 `workspace_entry`，只存 Owner checkpoint/App
运行态，除非 `AGENTS.md` 明确要求，不写 GitHub 或仓库。

### Complete contract fields

bootstrap 回读后，Owner 发送同 revision/digest 的完整合同；至少包含：

```text
owner_thread_id / task_thread_id / task_key
issue_readiness: ready
planning_truth_locator / scope_locator
contract_revision / contract_digest
owner_runtime_lock / owner_runtime_lock_status / runtime_lock_revision
execution_hold: true
milestone / FR / Issue / 用户价值 / 目标 / 非目标 / 验收
硬依赖 / 软依赖 / 收敛依赖
允许写入的仓库、文件、branch、正式 worktree、workspace_entry
禁止修改的 carrier、公共接口和越界边界
execution_mode / task_model / task_reasoning_effort / subagent_policy
OBJECTIVE / FILES AND OWNERSHIP / INTERFACES / CONSTRAINTS / VERIFICATION
汇报门禁 / PR_READY 条件 / evidence locator
```

`planning_not_ready` 或 GitHub truth 缺失时不发送完整合同、不 admission；`issue_readiness` 只证明规划
字段，不替代运行态合同、runtime evidence、scope integrity 或用户授权。

### Fixed handshake

Admission 严格使用以下顺序，不以 final、标题、wait 结果或 branch/worktree 跳步：

```text
Owner → Task: contract
Task → Owner: contract_ack
Owner → Task: execution_release
Task → Owner: execution_release_ack
Owner → Task: START control
Task → Owner: STARTED
Owner: read_thread + GitHub truth + runtime evidence → admitted/active
```

任务收到合同后先在自身会话写 `contract_ack: local_recorded`，再用锁定的
`send_message_to_thread` 投递真实 Owner；Owner 回读 `read_thread`、GitHub truth 和 runtime evidence 后
才消费并发送 release。`execution_release_ack`、`STARTED` 也必须由任务主动投递；缺失、错配、不可验证
或 release ACK 前写入均保持 `pending_contract`，隔离且不采用输出。START control 是执行许可，任务投递
`STARTED` 后可继续执行，不等待 Owner 纯 ACK。

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
event: <contract_ack | execution_release_ack | STARTED | SCOPE_DELTA | BLOCKED | NEEDS_OWNER | PR_READY>
task_key: <稳定 task_key>
execution_generation: <contract revision/digest 或 dispatch generation>
event_key: <task_key + execution_generation + event + head/status>
next_actor: <owner | task | user | external>
next_action: <短动作或等待原因>
wake_condition: <可执行条件>
runtime_lock_revision: <锁 revision>
evidence_locator: <消息/线程/GitHub/PR/head locator>
</control>
```

所有 `next_actor=owner` 事件（至少 `contract_ack`、`execution_release_ack`、`STARTED`、`SCOPE_DELTA`、
`BLOCKED`、`NEEDS_OWNER`、`PR_READY`、合同拒绝/漂移/锁权限异常）必须调用
`send_message_to_thread(owner_thread_id, model=owner_runtime_lock.model,
thinking=owner_runtime_lock.reasoning_effort)` 请求唤醒真实 Owner。每次投递在任务会话留短记录，
不得把完整日志、证据清单、env、token 或完整 SHA 集合跨线程转发。

每个事件严格单向推进：

```text
local_recorded → delivery_pending → delivered → owner_verified → consumed
```

工具失败、缺 message locator、锁/目标 runtime 无法核对或状态不明时写 `<EVENT>_PENDING_DELIVERY`，
本地 final 不推进合同状态。相同 generation/head/status 的重复事件静默丢弃；新 revision/digest 或
真实状态变化必须保留。Owner 收到事件后先 `read_thread` + GitHub truth + runtime evidence 核验，再更新
checkpoint/handoff 并消费，不让 Heartbeat 承担正常 admission。

`HEAD_CHANGED`、push、CI pending/success、review pending/success 可留任务内；仅当它们改变 Owner 的
决策时合并为一次 `NEEDS_OWNER`，不逐条通知。

## PR_READY 与 closeout contract

任务只能报告 `PR_READY` 或局部完成，不能自行发 `COMPLETED`。`PR_READY` 必须绑定 exact reviewed head、
准确 reviewed files、空 review write scope、完整 diff locator、验证结论、`semantic_scope_status: aligned`
和 hosted/PR metadata 终态；后续 diff/head 使旧 verdict 失效，修复后 fresh review。

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

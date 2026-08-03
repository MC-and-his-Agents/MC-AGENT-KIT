# Tasks Owner 与下游任务合同

只在激活 Owner 或创建独立任务线程时读取本文件。发送前必须根据已回读的 GitHub 事实填写完整合同，不保留占位符。

## Owner 契约

```text
当前对话现作为 <GitHub 项目> 的总负责线程。

owner_thread_id: <真实 threadId>
owner_model: <默认 gpt-5.6-sol>
owner_reasoning_effort: <默认 high，可提升为 xhigh / max>
owner_runtime_lock: <完整 canonical lock；model/reasoning_effort/revision/authority:user>
owner_runtime_lock_status: <verified | unverified>
execution_mode: <direct / flat / hierarchical>
luna_subagent_status: <supported / fallback / pending_restart / unverified>

项目与范围
- GitHub 项目：<project>
- 管理范围：<milestone / FR / issue>
- 用户价值：<本批次要产生的结果>
- 非目标：<明确不交付的内容>
- 验收标准：<成功、失败状态、真实验证和完成证据>

GitHub 规划真相
- milestone：<已回读项>
- 父 FR：<已回读项>
- 子 issue / 依赖：<已回读项>

调度方案
- 执行模式：<direct / flat / hierarchical，已由用户确认>
- 并发策略：<dynamic_ready_wave / fixed；fixed 时填写上限>
- 收敛通道：<同一仓库/target branch 默认 1>
- 推荐调度单元：<milestone / FR batch / issue>
- 第一波任务：<task_key 列表>
- 硬依赖：<依赖>
- 软依赖：<依赖>
- 收敛依赖：<依赖>
- 单一写入者：<任务到文件/仓库/PR 的映射>

决策边界
- 任务线程：局部、可逆、不改变公共合同的实现选择。
- Owner：跨任务依赖、公共接口、调度、审查、合并和 closeout。
- 用户：产品含义、优先级、权限、隐私、显著成本和不可逆外部动作。

Automation
- 状态：<未启用 / 已启用>
- automation id：<如有>
- 唤醒间隔/范围：<RRULE 或 interval、scope>
- 通知策略：<策略>
- owner_handoff：<handoff_revision / updated_at>

完成条件
- <可验证条件>
```

Owner authority 来自用户委任、Owner 契约、适用 `AGENTS.md` 和外部动作边界，不来自 Heartbeat prompt。外部可见或不可逆动作仍须按既有明确授权执行；Heartbeat 不能扩权，也不能削弱 Owner 合同。Heartbeat 只是绑定 `owner_thread_id` 的周期唤醒机制。

## canonical owner runtime lock（回显锁）

Owner 初始化时建立唯一的用户授权运行时锁，并把完整对象原样纳入 Owner contract、每个活动任务合同、`contract_digest` 和 Owner checkpoint：

```text
owner_runtime_lock:
  model: gpt-5.6-sol
  reasoning_effort: high
  revision: 1
  authority: user
```

这是 Skill 层的 compensating control（回显锁），不是宿主强安全边界。锁的四个字段整体纳入 `contract_digest`；`owner_runtime_lock_status: verified | unverified` 单独记录，不属于用户授权锁。`verified` 只表示工具参数和目标回读已相互匹配；仓库没有宿主实际强制证据时必须记为 `unverified`，不得声称已验证宿主。锁只能由用户修改；用户修改时递增 `revision`、重算 Owner contract，并让活动任务重新走 admission。旧 `runtime_lock_revision` 的事件只读，不驱动动作。

任务线程或 Subagent 用宿主 `send_message_to_thread` 唤醒 Owner 时，实际工具参数必须逐字回显锁：`model: owner_runtime_lock.model`、`thinking: owner_runtime_lock.reasoning_effort`。发送方的 Luna/max、默认配置或当前 Owner runtime 都不得参与；宿主参数名是 `model` / `thinking`，不得杜撰 `target_model`。控制块只需带 `runtime_lock_revision`，不复制整把锁。

发送前发现锁缺失、格式错误、revision/`contract_digest` 不匹配或值不受支持时，不得省略参数或猜测发送；事件记为 `<EVENT>_PENDING_DELIVERY`，等待 Heartbeat/用户修复。消息送达后由 Owner 核对实际 `turn_context`：一致时才把锁状态记为 `verified` 并消费事件；不一致或无法回读时记为 `unverified` 并 fail closed，只读核验并通知用户，暂停调度、派发、merge、closeout 和其他外部动作。

能力门禁只在有证据时标记 `verified`：Luna/max sender 必须显式以锁中 `model=gpt-5.6-sol`、`reasoning_effort=high`（工具 `thinking=high`）唤醒，目标 `turn_context` 仍须为 Sol/high；省略参数、使用 sender 自身 Luna/max 或旧 revision 均为负向场景，不得宣称宿主已强制回显。

## 双层消息与人类可读性

除纯 ACK、hold、release、`STARTED` 等内部握手外，Owner↔任务线程的消息都采用双层格式：先写一段简短自然语言摘要，末尾再放最小 `<control>` 控制块。摘要在删除控制块后仍应让读者知道发生了什么或结论、为什么/影响或风险，以及下一步由谁做什么；没有实际相关项时不硬凑句子。

控制块只保存路由、防重和恢复所需字段。事件上行通常使用 `event`、`task_key`、`execution_generation`、`event_key`、`next_actor`、`next_action`、`wake_condition` 和 `evidence_locator`；不相关字段省略。`contract_digest`、完整 SHA 和 `execution_generation` 只在 admission、迁移、错配消歧或控制块确实需要时出现，普通任务指令和摘要不堆这些字段。完整测试日志、证据清单和完整哈希集合留在任务线程、PR 或证据载体；跨线程只带结论、风险、下一步和 evidence locator。

可复制示例（删除 `<control>` 后仍可读）：

```text
阻塞：本地测试已通过，但 hosted CI 仍失败，当前不能进入合并。
影响：PR #456 的合并门禁被阻塞；完整日志留在任务线程，Owner 只需查看下方证据定位。
下一步：Owner 回读 CI run #789，决定修复或重跑；任务线程继续保留原始日志。

<control>
event: BLOCKED
task_key: #123
execution_generation: r4
event_key: #123:r4:BLOCKED:abc123
next_actor: owner
next_action: 回读 CI run #789 并决定修复或重跑
wake_condition: Owner 选择路径或新 CI 结果可用
runtime_lock_revision: 1
evidence_locator: PR #456 / CI run #789
</control>
```

`BLOCKED`、`NEEDS_OWNER`、`PR_READY`、`COMPLETED` 以及 Owner→task 的普通指令都必须有人话层；握手可保持短机器格式并只留在任务/Owner 内部。给用户的 Owner final 不展示控制块或协议握手字段，除非用户明确要求底层诊断；只报告结果、影响、阻塞/风险和下一步。

## 跨线程交付状态机

`task final` 只是任务线程的本地记录，不能代替跨线程交付。任一控制握手或执行事件只要 `next_actor=owner`，任务都必须对真实 `owner_thread_id` 调用宿主 `send_message_to_thread` 并请求唤醒 Owner；至少覆盖 `contract_ack`、`execution_release_ack`、`STARTED`、`BLOCKED`、`NEEDS_OWNER`、`PR_READY`，以及合同拒绝、合同漂移、锁/权限异常。每次投递同时在任务自身会话留下短记录；消息成功也不等于 Owner 已验证。

每个 `event_key` 的最小状态严格单向推进：

```text
local_recorded → delivery_pending → delivered → owner_verified → consumed
```

任务先写 `local_recorded`，再调用 `send_message_to_thread`。工具失败、返回值缺少可验证 message locator、锁/目标 runtime 无法核对或投递状态不明时写 `<EVENT>_PENDING_DELIVERY`，保留同一事件控制块；本地 final 不推进 Owner 合同状态。可验证投递写 `delivered`，Owner 仍必须用 `read_thread` 和实时 GitHub truth 核验后才写 `owner_verified`，消费控制动作后才写 `consumed`。`event_key` 去重只在当前合同/执行代次内生效；不建数据库或 registry，不无限重试，Heartbeat 只补漏投、pending 和漂移恢复。

admission 固定顺序，不得用 final、标题或 wait 结果跳步：

```text
Owner → Task: contract
Task → Owner: contract_ack
Owner → Task: execution_release
Task → Owner: execution_release_ack
Owner → Task: START control
Task → Owner: STARTED
Owner: read_thread + GitHub truth 核验 → admitted → Owner 可结束回合，Task 继续执行
```

每一步 `next_actor=owner` 的握手都要真实投递并记录状态。`START` control 是执行许可：Task 收到后先投递 `STARTED`，随后可继续执行，不等待 Owner 纯 ACK；Owner 核验该事件后把任务记为 `admitted/active`。Owner 当前回合在线时可用 `wait_threads` 降低延迟，但它不能替代投递或核验；`read_thread` 用于 admission 核验和恢复。Owner 收到任何事件后必须回读任务线程与 GitHub truth，再决定是否消费；Heartbeats 不承担正常 admission 推进。

## Bootstrap hold

新任务的初始消息只用于建立执行现场，必须包含主 Owner ID、`task_key`、目标摘要和 `execution_hold: true`，要求任务保持只读、只回报真实 `task_thread_id`、branch/worktree/head、模型与推理程度后结束当前回合。恢复、模式切换或模型覆盖时先发送同样的 hold。

Owner 从该回报构造 `workspace_entry = task_thread_id + branch + absolute_worktree + head`，回读后只存入 Owner checkpoint/App 运行态；除非适用的 `AGENTS.md` 明确要求，不写入 GitHub 或仓库。它不是宿主原生字段。

## output contract：下游任务线程合同

bootstrap 完成后发送的完整合同，先用一段简短自然语言说明本任务的目标、范围和下一步，再在其后放 admission contract 字段；这些字段只服务于 admission，不是普通任务摘要或用户 final。第一行仍写入主 Owner 的真实线程 ID，并包含：

```text
主 owner 线程 ID: <真实 threadId>
owner_thread_id: <同一真实 threadId>
task_thread_id: <真实 task threadId；不得等于 owner_thread_id>
task_key: <GitHub issue URL 或 issue 编号>
subagent_policy: <flat 必须为 forbidden；hierarchical 为 allowed>
contract_revision: <单调递增版本>
contract_digest: <下述合同绑定摘要>
owner_runtime_lock: <与 Owner contract 完全一致的完整锁对象>
owner_runtime_lock_status: <verified | unverified>
runtime_lock_revision: <锁 revision；控制块仅带此字段>
execution_hold: true

任务身份与目标
- GitHub milestone / FR / issue
- 权威事实定位
- 已确认的用户价值、范围、非目标与验收标准

依赖与写入边界
- 硬依赖、软依赖和收敛依赖
- 允许修改的文件/仓库/PR
- 禁止修改的共享 carrier 和公共合同
- 正式 branch / worktree
- workspace_entry：<Owner 运行态中已回读的 tuple>

执行方式
- branch / worktree / PR 规则
- 执行模式：<flat / hierarchical>
- 任务线程模型与推理程度：<默认 gpt-5.6-luna / max>
- Subagent 策略：<flat 为 Owner 执行的策略禁令，不声称宿主原生隔离；hierarchical 默认 gpt-5.6-luna / max 或用户确认的回退模型>
- 用户明确指定的覆盖项：<没有则写无>
- 允许自主决定的范围

完成与汇报
- 目标完成条件
- 验证和独立审查要求
- 上行汇报门禁：除合同 ACK、release ACK 和一次 `STARTED` 外，只在 `BLOCKED`、`NEEDS_OWNER` 或最终 `PR_READY` 时直接汇报
- 普通 head、push、CI、review 和实现 checkpoint 只留在任务线程；以最新事实覆盖一个 `pending_delta`，并入下一次允许的上行汇报
- `PR_READY` 必须绑定 exact head，且任务负责的验证、review、hosted CI 和 PR 元数据均已终态；否则不发送候选/等待 checkpoint
- 允许的上行汇报包含：双层摘要中的状态、交付物、结论/影响或风险、下一步与 evidence locator；PR/head、验证和审查只带结论，完整命令、日志、证据清单和哈希集合留在任务线程、PR 或证据载体
- 收到本合同时重新计算并核对 digest，先在任务会话写入 `contract_ack` 的 `local_recorded` 记录，再用锁定参数调用 `send_message_to_thread` 投递真实 Owner；消息不可验证则写 `CONTRACT_ACK_PENDING_DELIVERY`，不得把本地 final 当作 Owner 已收到，也不得写入
```

任务线程不得把 `HEAD_CHANGED`、push、rebase、CI pending/success 或 review pending/success 单独升级为 Owner 消息。若这些变化使现有 Owner review/merge 决策失效，合并为一次 `NEEDS_OWNER`。相同或被更新事实覆盖的事件静默丢弃，不发送“已去重”。

## 上行事件与活性兜底

任何 `next_actor=owner` 的控制握手或执行事件（包括 `contract_ack`、`execution_release_ack`、`STARTED`、`BLOCKED`、`NEEDS_OWNER`、`PR_READY`、合同拒绝/漂移和权限或锁异常）必须通过宿主线程消息工具投递到真实 `owner_thread_id` 并请求唤醒；消息至少携带：

```text
event
task_key
execution_generation
event_key
next_actor
next_action
wake_condition
evidence_locator
runtime_lock_revision
```

消息正文必须遵守[双层消息与人类可读性](#双层消息与人类可读性)：先给结论/影响或风险/下一步的自然语言摘要，再给上述字段组成的 `<control>`；握手可保持短机器格式，但也必须有投递记录。不得把完整测试日志、证据清单或完整 SHA 集合直接转发。任务只记录宿主投递结果或 message locator 并结束，不等待 Owner 纯 ACK；每次投递也在任务会话保留简短本地记录。若投递不可验证，任务不得虚报“已上行”，而是标记 `<EVENT>_PENDING_DELIVERY`，在自身 final 中保留同一结构化事件且不推进 Owner 合同状态；Owner/Heartbeat 恢复时必须 `read_thread` 回读任务线程和实时 GitHub truth，补消费漏投事件。不得引入数据库、文件 registry 或无限重试。

## 合同投递与 admission gate

这是协作式协议，不是宿主原生写权限锁。Owner 对以下规范字段的 canonical JSON（UTF-8、key 排序、紧凑分隔符、不含 digest 自身）计算 SHA-256：revision、Owner/task ID、task_key、范围与验收、依赖、workspace_entry、完整 `owner_runtime_lock`、模型、写入边界、Subagent 策略、上行汇报门禁和收敛通道；结果为 `contract_digest`。

新建、恢复、模式切换、模型覆盖或 runtime lock revision 变化都要重新进入 hold，并固定按以下顺序推进：Owner→Task `contract`；Task 先在自身会话写 `contract_ack` 的 `local_recorded`，再以锁定的 `model`/`thinking` 调用 `send_message_to_thread` 投递 Owner；Owner 用 `read_thread` 和 GitHub truth 核验后记录 `contract_ack_message_id` 与 `contract_status: acknowledged`；Owner→Task 发送同 revision/digest 的 `execution_release`；Task 同样投递 `execution_release_ack`，失败则 `RELEASE_ACK_PENDING_DELIVERY` 且仍为 `pending_contract`；Owner 回读并记录 `release_message_id`、`release_ack_message_id` 与 `contract_status: released`；Owner→Task 发送 `START` control；Task 下一回合先主动投递回显同 revision/digest/runtime_lock_revision 的 `STARTED`，随后可继续执行而不等待纯 ACK；Owner 再次 `read_thread` + GitHub truth 核验后标记 `admitted/active` 并可结束当前回合。缺失、错配、不可验证或 release ACK 前写入均视为协议违规，立即隔离且不采用其输出。

迁移 cutover 时，hold 允许任务完成当前原子写入/命令后停在安全边界，并回报 `sealed_revision`、`cutover_head` 与 worktree 状态。Owner 回读并封存旧 revision 后才发送新合同；封存后的旧 revision 消息不再驱动动作，但已有 worktree/branch 结果保留并由新合同显式接管，不因协议切换丢弃。

修复错配时先从当前 canonical contract 重新计算唯一权威 digest：若合同内容变化则递增 revision，再完整重发 hold/contract/ACK/release；不得只要求任务接受某个已有 digest。

首次写入还要求真实 `task_thread_id != owner_thread_id`、正式 branch/worktree、已回读的 workspace_entry，以及模型/推理策略一致。任一项缺失都停在 `pending_contract`，不以标题、摘要或 `clientThreadId` 替代事实。

Owner 收到任务消息后，必须先 `read_thread` + GitHub truth 核验，再仅在 `next_actor=owner` 且存在已授权动作时行动并发送必要决定；Owner 当前回合在线时可用 `wait_threads` 降低延迟，但不能替代投递或核验。普通非 Heartbeat Owner 回合若仍由 task/external 继续，可静默更新 checkpoint，不回复“已回读”“继续等待”或重复状态摘要。Heartbeat 只补 pending、漏投和漂移恢复，不承担正常 admission；Heartbeat 回合仍须留下唯一短 heartbeat 结果；用户只在主动询问、需要其决定、出现真实 blocker/风险、执行外部可见动作或完成 closeout 时收到状态。

## 既有 Owner 迁移

旧合同、旧 Heartbeat 或运行轨迹出现逐 checkpoint 汇报时，先停止新派发，让合法在途工作在原子安全边界完成并封存旧 revision。按 [operations.md](operations.md#既有-owner-迁移) 更新 Heartbeat 和活动任务合同；迁移完成前不沿用旧版“每阶段主动汇报”约定。

## Direct Subagent 合同

`direct` 由主 Owner 使用原生 `spawn_agent` 创建 Subagent，并显式设置 `fork_turns: "none"`、`model: "gpt-5.6-luna"`、`reasoning_effort: "max"`；门禁失败时使用用户确认的回退模型。它没有独立 App 任务线程，因此不使用 hold/release；Owner 在 spawn 前以 `owner_thread_id + branch + absolute_worktree + head` 构造 direct workspace_entry，完成 GitHub truth、模型和写入权门禁，并把完整合同原子地放入 spawn prompt。创建后回读真实 agent ID。Subagent 不得继续衍生下级；多个 Subagent 并行时只允许一个写入者，其余保持只读。

## Flat 独立审查合同

`flat` 执行任务不得自审。Owner 创建同级只读 review 任务，`task_key` 使用 `<执行 task_key>:review:<head_sha>`，写入范围为空，只能回读当前 head、验收标准和验证证据并返回 findings。review 任务同样设置 `subagent_policy: forbidden`。

## Closeout contract

任务只能报告 `PR_READY` 或局部交付完成。Owner 仅在回读适用证据后发出 `COMPLETED`：目标验收通过；PR 已合并或明确无需 PR；merge commit 与 target branch 可验证；GitHub issue 状态已同步；适用 `AGENTS.md` 要求的 repo carrier/current pointer 已同步；外部状态与仓内事实一致。缺项时保持 `NEEDS_OWNER` 或 `BLOCKED`，不得把 PR/head 当作最终完成。

## rollback boundary

- 派发前：可直接撤回调度建议，不产生任务状态。
- 已创建未写入：暂停或归档对应任务，并在 Owner checkpoint 标记取消原因。
- 已产生 branch/PR：停止继续写入，保留 branch/PR 作为可审计证据；是否关闭或删除必须由 Owner 按仓库规则确认。
- 已执行外部可见或不可逆动作：不承诺自动回滚，立即停止并交由用户决定。

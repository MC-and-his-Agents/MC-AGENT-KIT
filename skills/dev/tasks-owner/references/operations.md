# Tasks Owner 运行手册

只在激活、派发、恢复或排障时读取。

## 能力与事实门禁

1. 获取当前真实 `threadId`；无法取得时只能建立只读契约。
2. 检查宿主是否提供项目读取、任务线程管理、`spawn_agent`、Subagent 查询/等待/消息/中断、标题和 Automation 管理能力。
3. 用户显式项目优先于当前目录项目，当前目录项目优先于唯一匹配项目。
4. 回读适用的 `AGENTS.md`、GitHub milestone、父 FR、子 issue、依赖、branch、正式 worktree、PR 和 head。
5. 检查同项目是否已有活跃 Owner；冲突时只读说明候选线程和所有权转移建议。
6. 在模式确认前执行 [luna-subagents.md](luna-subagents.md) 的兼容性门禁，并记录 `luna_subagent_status` 与用户选择。
7. 新建、恢复、模式切换或模型覆盖先进入 hold；按 [contracts.md](contracts.md) 构造 workspace_entry 与 digest。任务依次只回报同 revision/digest 的合同 ACK、release ACK 并各自结束回合；Owner 回读两次 ACK 后，任务以同 revision/digest 的 `STARTED` 证明进入执行。
8. 写入 admission gate 还要求真实 `task_thread_id != owner_thread_id`、正式 branch/worktree、已回读的 `workspace_entry`，以及任务线程模型/推理策略与已确认合同一致；缺任一项只保持只读。
9. 激活/恢复时把目标所需动作映射为 `inspect`、`correct_existing`、`dispatch_new`，与 Automation 权限做 capability diff；任何缺口都显示并请求升级，不静默保留错配。

## Ready wave 与防重

Owner 是唯一派发者；一个 Owner 只维护一个绑定它的 Heartbeat。

1. 一次性回读 GitHub truth 和现有线程，用 `task_key` 区分活动、待创建、已结束和状态不明任务，并对既有任务按本文件的合同流程补发完整合同。
2. 计算 `max_inflight = min(host_cap, user_cap)`；任一缺失取另一，均缺失时初始为 8。活动任务和待创建任务都计入；checkpoint 记录 resolved cap 及来源。`dynamic_ready_wave` 只能在此硬上限内选择依赖满足且写入不冲突的 ready set。
3. 对选中任务并发执行非阻塞创建；GitHub 仓库默认使用独立 worktree。返回 `clientThreadId` 时记为待创建并占用当前波次容量，不能当作真实线程 ID。
4. 整个波次提交后统一回读项目、模型、推理程度、目标、正式 branch/worktree、`workspace_entry`、真实 `threadId` 和 `task_key`；依次回读匹配 revision/digest 的合同 ACK、release ACK 和首个 `STARTED` 后才允许写入。等待工具有单次目标数限制时分组等待，不降低创建并发。
5. 干净波次可在硬上限内增加下一波宽度；rate/resource/worktree/duplicate failure 时减半。单个不明任务只隔离该 `task_key`；下一次完整回读后仍无法解析时只补偿重试一次，并递增 `dispatch_generation`。
6. 发现重复时保留已验证的权威线程，暂停该 `task_key` 后续派发并报告；不得用归档代替事实确认。
7. Owner 可在既有授权内自主调整自设并发、重试和调用预算；只有扩大成本、隐私、外部发送、权限或不可逆动作边界才询问用户。

`direct` 使用稳定 `task_name` 和原生 `spawn_agent` 填充 ready wave，显式传递已确认模型、推理程度与 `fork_turns: "none"`，并把真实 agent ID/规范任务名写入 checkpoint。`hierarchical` 的任务线程使用相同规则创建 Subagent。单个 Subagent 失败只隔离对应 `task_key`。

## 实现并发与收敛通道

- `implementation_inflight` 受 `max_inflight` 约束；同一仓库和 target branch 的 `convergence_inflight` 默认上限为 1。
- 任务在实现完成、初步验证通过且已有 PR candidate 时申请通道；取得通道后才对 latest target branch 做一次 rebase/current-head refresh，并完成最终验证、review、hosted CI、PR 元数据回读与 `PR_READY`。
- 等待通道的任务继续无冲突实现，但不因其他 PR 合并而逐次 rebase、重测或上报。main 多次前进时只保留最新 base，取得通道后一次消费。
- 只有目标分支、共享合同、carrier 与 merge surface 相互独立时，Owner 才能提高 `convergence_inflight`；理由和 resolved cap 写入 checkpoint。
- 通道由 `convergence_generation` 标识。PR merge/closeout、任务撤回/失败，或无法在当前 Owner 回合解决的 `BLOCKED` / `NEEDS_OWNER` 都必须释放；可立即解决的 Owner 动作完成后可保留。
- 释放后按 `convergence_requested_at` 和 GitHub 优先级选择下一项；Heartbeat 发现 owner task 已结束、暂停或 wake condition 失效时回收通道，避免永久占用。

## Checkpoint 与恢复

checkpoint 至少包含：

```text
owner_thread_id
scope
execution_mode
task_key -> threadId/agentId -> status
task_key -> clientThreadId -> dispatch_generation
task_key -> contract_revision/digest/ack_message_id/release_message_id/release_ack_message_id/status
task_key -> workspace_entry
wave_id / wave_width / max_inflight / last_capacity_failure
implementation_inflight / convergence_inflight / convergence_owner / convergence_generation / convergence_requested_at
依赖与下一解锁条件
最近 wait/read cursor
automation id 与权限模式
luna_subagent_status 与回退模型
next_actor: owner | task | user | external
next_action
wake_condition
last_event_key
pending_delta
updated_at
```

恢复或 Heartbeat 唤醒时，从 Owner 对话的 compact checkpoint、线程 cursor、Automation 状态和 GitHub truth 重建运行视图，不复制完整项目状态到 Automation prompt。执行位置 Handoff 只改变运行环境；责任转移必须先回读源线程和 GitHub 事实，再向目标线程发送合同并更新 checkpoint。

当 `wake_condition` 满足、`next_actor=owner` 且 `next_action` 在已授权范围内时，Owner 当前回合立即执行该动作，不只报告“可继续”。若仍由任务或外部参与，更新 checkpoint 后静默结束；不得向任务或用户发送纯 ACK/等待消息。

## 下游阶段事件

任务内可以记录 `HEAD_CHANGED`、`CI_TERMINAL` 和 `REVIEW_TERMINAL`，但不得逐条上行。上行只允许：控制握手中的一次 `STARTED`；需要立即处理的 `BLOCKED` / `NEEDS_OWNER`；满足全部任务侧门禁的单次 `PR_READY`。`COMPLETED` 仅由 Owner 在满足 [closeout contract](contracts.md#closeout-contract) 后发出。

`event_key = task_key + execution_generation + event + head/status`；App 任务线程的 `execution_generation` 为 contract revision/digest，direct 为 spawn/dispatch generation。相同 key、旧 head、被较新事实覆盖或没有改变 `next_actor/next_action/wake_condition` 的事件直接静默丢弃。非紧急变化写入任务内唯一 `pending_delta`，新事实覆盖旧事实，下一次允许上行时一次带出。

## 既有 Owner 迁移

1. 识别旧 Heartbeat/合同中的无界并发、完整项目快照、逐 checkpoint 汇报或纯 ACK；按 Automation capability diff 判断是否有权纠偏。
2. 暂停 `dispatch_new`；读取活动任务的真实 thread/workspace/head 和当前 revision。发送 migration hold，允许任务完成当前原子写入/命令后在安全边界停止，并回报 `sealed_revision`、`cutover_head` 与 worktree 状态。
3. 更新 Heartbeat：只保留稳定策略和运行态 locator，写入 `max_inflight`、`convergence_inflight=1`、上行门禁和静默 ACK；删除“所有阶段主动汇报”及复制的完整项目状态。
4. Owner 回读 cutover 事实并封存旧 revision；已有 worktree/branch 结果保留。随后递增 revision，重新执行完整合同、合同 ACK、release ACK 与 `STARTED`；新 digest 必须包含汇报策略和收敛通道。
5. 封存后的旧 revision checkpoint 只读并合并到 `pending_delta`，不驱动动作、不回复；新合同显式接管 cutover head。所有活动任务完成新 revision admission 后恢复派发。

## 策略违规

hold/release 与 `flat`/`direct` 下级衍生禁令都是协作策略，宿主没有已验证的原生写入锁或禁用开关。发现提前写入、digest 错配或越权衍生时暂停执行单元、回读影响并报告；不采用违规输出。其他无冲突任务继续。

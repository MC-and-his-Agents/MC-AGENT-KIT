# Tasks Owner Automation 参考

Automation 只负责唤醒与 handoff；Owner 的目标控制循环、实时分类、恢复门禁和终态以
[operations.md](operations.md) 为单一事实源，容量/dispatch 细节以 [scheduling.md](scheduling.md)
为事实源，不在本文件复制第二套状态机。

只有用户明确允许周期唤醒时读取本文件。Heartbeat 是绑定当前 `owner_thread_id` 的唤醒器，不是第二个 Owner、独立 Agent、权限主体或事实数据库；用户若只要监控，应另建明确的 `monitor-only` Automation。

## 创建与更新

创建或更新前只确认以下内容：

```text
是否启用绑定当前 Owner 对话的 Heartbeat？请确认：
- 启用或不启用；
- 唤醒间隔、作用范围和必要运行参数（如时区、起止边界）；
- 通知策略。
```

Automation 只检查宿主能力是否可用、用户是否已授权创建/更新，以及是否绑定当前真实 `owner_thread_id`。不得为 Heartbeat 建立额外动作等级，也不得以 Heartbeat prompt 授予额外权限。创建前优先原地更新同用途 Automation；保留 automation id、RRULE/间隔和通知策略，并回读更新结果。Heartbeat 未启用或不可用时仍维护 Owner 对话 checkpoint，不创建替代 cron。

## owner_handoff

唯一主 Owner 是 `owner_handoff` 的唯一写入者。任何来源（用户、任务事件、Owner 主动操作、迁移或 Heartbeat）导致控制面实质变化时，Owner 必须在结束回合前原地更新已存在 Automation prompt，递增 `handoff_revision`，保留 automation id、RRULE/间隔和通知策略，并回读更新结果。首次调度、重大 closeout/replan 或用户效率复盘还必须刷新 acceptance/backlog matrix；matrix 只在 Owner checkpoint/运行态保留 locator/短状态，不写 GitHub 或仓库运行数据。普通 head、push、CI、review 只有改变 `next_actor`、`next_action` 或 `wake_condition` 时才触发更新。

`owner_handoff` 是恢复索引/小记事本，不是完整项目状态库、GitHub truth 或权限载体。不得写完整任务快照、所有 head、普通 push/CI/review、长日志或用户材料。

稳定模板：

```text
owner_handoff:
  handoff_revision: <单调递增整数>
  updated_at: <ISO-8601>
  owner_thread_id: <真实 threadId>
  owner_contract_revision: <revision；或 contract_digest/稳定 locator>
  owner_runtime_lock_revision: <锁 revision>
  owner_runtime_lock_status: <verified | unverified>
  scope_locator: <GitHub milestone/FR/issue locator>
  next_actor: <owner | task | user | external>
  next_action: <一项短动作或等待原因>
  wake_condition: <下一次可执行条件>
  active_task_locators:
    - task_key: <issue locator>
      threadId: <真实 task threadId；可选 agentId>
      cursor: <线程 cursor；可选>
      status: <短状态>
  convergence_owner: <task_key/owner 或 none>
  convergence_generation: <代次或 none>
  acceptance_matrix_locator: <locator；不嵌入完整 matrix>
  matrix_status: <complete | incomplete | stale>
  unresolved_decision: <待用户/Owner 决定或 none>
  last_material_event_locator: <message/event/GitHub locator>
```

只维护 locator、短状态和下一动作；不得把完整 matrix、完整效率指标、任务日志或运行数据塞进 handoff。
Automation 不得成为第二个状态写入者。Automation prompt 发生实质变化时，Owner 同时维护对话 checkpoint；若 Automation 不可用，则仅保留 checkpoint。

## Heartbeat 唤醒提示词

```text
从 owner_handoff、Owner checkpoint、线程 cursor 和实时 GitHub truth 恢复上下文，然后立即执行一次
完整 Owner 控制周期：

1. 核对 Owner 实际 `turn_context` 与 canonical `owner_runtime_lock`；异常时只读通知用户并暂停关键动作。
2. 评估目标进度：目标是否完成、未满足结果、关键路径、依赖、下一解锁条件，以及 closeout 后是否缺少
   successor Work Item。
3. 评估调度进展：完整 ready buffer、selected/admitted/pending/空槽、未选理由、admission 握手、实现与
   单收敛通道是否符合实时容量；逐任务核对 `upstream_delivery_contract` 和
   `delivery_route_status=armed`/真实 locator，并核对 sender locator（bootstrap 可为 clientThreadId，完整合同为
   sender_task_thread_id）与创建返回的 task locator 一致且不等于 Owner thread；direct 只需 native agent
   completion/wait locator，免 route ACK。未 armed/错配时保持 `admission_pending`，本回合做有界 wait/read
   核验；仅在 [contracts.md](contracts.md) 的 `safe_sleep_predicate` 成立时等待，不输出“无需操作/正在并行”后休眠；空槽和可执行工作并存时当场补派发。
4. 评估任务健康：逐个回读活动任务的真实 locator、最新有效状态、`next_actor`、阻塞、scope delta、
   pending delivery、重复失败和陈旧回报；每个 `next_actor=owner` 事件必须有 message locator，并完成
   `received_at → verified_at → consumed_at`（或等价 locator）。发现漏投/未消费时先记 `delivery_violation`
   并纠偏，不得输出等待终态；需要 Owner 接手时当场纠偏、解阻或重新分配。delivery recovery 受同一
   `event_key`/`recovery_epoch` 限制：本控制周期最多一次，跨周期总计最多两次；若宿主没有可执行 locator/wake 能力或上限
   耗尽，保留 pending/missing evidence、authority/host evidence locator 和 wake condition，转
   `waiting_external`，只有替代通道/授权需用户选择时转 `waiting_user`。新的外部事实或用户决定才开启新的
   `recovery_epoch`；未有新事实前不重试。两次失败后 quarantine 当前 execution_generation，记录 slot impact，
   禁止 admitted、replacement 或重复 dispatch；仅在新的外部事实/用户决定后解除；
   仍存在可执行投递动作且未耗尽时禁止 `waiting_task`、`DONT_NOTIFY` 或结束回合；task final、START 或
   BOOTSTRAP_READBACK final 不能替代真实 delivery locator。
5. 评估交付质量：核验目标/验收归属、scope integrity、测试/CI、fresh exact-head review、PR metadata、
   `PR_READY`、closeout 与 cleanup 证据；不能用状态标签、摘要或旧 head 代替证据。
6. 按实时事实重新分类 `execution_ready | owner_actionable | external_blocked`，执行
   [operations.md](operations.md) 的 owner action、readiness/admission、supervise/correct、
   converge/closeout/cleanup/replan，直到合法控制周期终态。`ready_task_keys=[]`、`planning_not_ready`、
   stale `next_actor=external` 或历史 DONT_NOTIFY 都不能跳过本次评估。
7. 更新 checkpoint 与 owner_handoff，并以 first-review pass、acceptance coverage per merge、same-carrier
   PR count、event-to-action latency、critical-path width 和 admitted=1 时剩余 owner-actionable 作为短
   控制信号；它们不构成新数据库或 handoff 全量状态。只输出一条简短结果：已推进则写真实变化；合法 `waiting_task` /
   `waiting_external` 才写 `DONT_NOTIFY` 和等待证据；需要用户决定或真实风险写 `NOTIFY`。不输出纯 ACK、
   逐任务流水账或多条阶段播报。

只执行 `confirmed_owner_authority` 与 Owner 合同覆盖的动作；不得补造 GitHub truth，也不得执行未经授权的
发布、删除、付费、外部发送或权限变更。
```

## 防重与恢复

`task_key` 使用 GitHub issue URL 或稳定 issue 编号，是查重键而非新的状态库。

1. 一次性读取已有线程并用 `codex_app__read_thread` 验证 task_key、项目、目标和状态。
2. 每次恢复按 [scheduling.md](scheduling.md) 重新计算 ready wave、target/actual、pending、槽位、任务级理由和 `dispatch_generation`；按 operations.md 重跑目标完成、gap、`owner_actionable`/`external_blocked` 与 recovery 分类。merge、closeout、依赖解除或收敛通道释放后同一周期重算。
3. `clientThreadId` 只记为待创建并占用 host/admission 槽（若宿主确实占用），不计实现 actual；本轮不立即重复创建，其他独立任务不受影响。
4. 波次提交后统一回读真实 `threadId`、host/project、目标、branch/worktree 和 task_key。
5. 下一次运行仍无法解析某个待创建任务时，允许用相同 task_key 做一次补偿重试并记录 `dispatch_generation`；不得无限重试。
   对 `next_actor=owner` 的漏投事件遵守独立 delivery recovery 上限：同一 `event_key` 在一个
   `recovery_epoch` 内每控制周期最多一次、总计最多两次；达到上限或宿主能力确认不可用后只记录证据并等待
   新外部事实/用户决定，不伪造 delivered/consumed。
6. Owner checkpoint 记录 task_key、threadId/clientThreadId/agentId、dispatch_generation、status、cursor、依赖、合同 ACK、workspace_entry、完整 `owner_runtime_lock`/revision/status、Luna 门禁、槽位统计、`next_actor`、`next_action`、`wake_condition`、`last_event_key`、事件交付状态和 pending_delta；实质变化同时更新 owner_handoff。
7. 下一次运行从 checkpoint、owner_handoff、App 线程 cursor 和 GitHub truth 重建，不向仓库或 GitHub 写入线程运行数据，也不复制完整项目状态。

当前 App 未提供公开原子 claim/idempotency key 时，只能提供可审计的 best-effort 防重，不能宣称 exactly-once。重复或不确定状态只隔离对应 task_key，不阻塞无冲突任务。

同理，当前没有已验证的宿主写入锁或 Subagent 禁用开关。hold/release 和 `flat`/`direct` 禁令属于协作合同/策略；在取得运行时证据前记录为 `missing evidence`。

## 迁移

迁移既有 Heartbeat 时原地更新原 Automation，不并存创建第二个；以唤醒机制和 owner_handoff 载体替换旧提示词，保留原 automation id、RRULE/间隔、通知策略和 `confirmed_owner_authority`。先完成安全 cutover，再恢复派发。

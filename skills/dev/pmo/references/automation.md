# Observer Heartbeat and handoff

只在用户明确授权周期观察时读取。观察 Heartbeat 绑定独立编排线程，只负责唤醒；它不是 Owner、审批者、权限来源、事实数据库，也不替代每个 Owner 的专属 Heartbeat。

## Contents

- Create or update
- Skill refresh
- Runtime and truth gates
- Recovery checkpoint and compact handoff
- Heartbeat cycle and Owner lifecycle coupling

## Create or update

- 先确认 cadence、scope、timezone/边界和通知策略；Automation 授权与观察/Owner 授权分开。
- 同用途优先原地更新，不并存创建重复 Heartbeat。
- 绑定真实 orchestrator threadId；不要用标题、Owner thread 或 task thread 代替。
- Heartbeat prompt 显式调用 `$pmo` 并保存当前 `skill_locator`；不要复制整份 Skill 到 Automation 指令。
- 保留用户明确的 fixed cadence/no-backoff；没有授权不自行改变。

## Skill refresh

每次 Heartbeat 唤醒后的第一项动作是从 `skill_locator` 完整重读当前 `SKILL.md`，然后才核验 runtime 或消费事件。记录 `skill_digest`、`skill_loaded_at` 与 `skill_status=verified|unavailable`。

- digest 未变：继续本轮，只按 reference routing 读取相关 reference。
- digest 改变：读取迁移所需 reference，向前更新 checkpoint；历史上按旧版本已合法完成的事件不追溯判错，不重复派发 Owner、事件或 GitHub 动作。
- Skill 不可读：受影响控制周期 fail closed，不创建/唤醒/terminal Owner、不改 ownership/dependency、不消费事件；报告缺失 locator 与 wake condition。

Checkpoint 和 Automation 只保存 locator、digest 与短状态，不嵌入 Skill 正文。

## Runtime and truth gates

Runtime 证据机制直接使用当前 `$tasks-owner/references/runtime-and-review-evidence.md`。本 Skill 的有效默认 policy 为：编排者和独立 Owner 均使用 `model=gpt-5.6-sol`、`reasoning_effort=high`、`fallback=forbidden`；只有带 locator 的用户明确指令能覆盖。Owner 内部 writer/reviewer/cleanup 的 runtime 仍由 `$tasks-owner` 管理。

- 每次 Heartbeat 对编排者和全部活动 Owner逐一记录 desired/observed runtime、`runtime_evidence_locator`、`runtime_evidence_status=verified|unverified|failed` 和 `runtime_evidence_target=<thread + target turn/epoch + policy revision>`；发送方自报、handoff 和事件不算实际证据。
- 公开 metadata 优先；只在字段缺失时使用 allowlisted、只读、本机结构化证据。两者冲突、目标不明或字段缺失时 fail closed。
- 编排者 runtime 未核验或不匹配时标记 `RUNTIME_LOCK_ANOMALY`，停止事件消费和拓扑动作。只有 `runtime_recovery` 已授权且宿主有可核验原生机制时，才为同一编排线程安排 desired runtime 的下一回合；否则通知用户。下一目标 turn 核验前状态保持 recovering，异常回合不得自证恢复成功。
- 某个 Owner runtime 未核验或不匹配时只隔离该 lane：不消费其事件、不向其路由写能力动作、不转移 carrier、不 closeout/terminal。若已授权且宿主支持，则精确恢复同一 Owner thread 并核验下一目标 turn；禁止创建重复 Owner或 fallback。其他已核验 lane 继续。
- 不编辑用户/宿主 runtime 配置，不把补偿性检查表述为技术防篡改强锁。每个 Owner 的专属 Heartbeat 同时按 `$tasks-owner` 核验自身 runtime。

对 GitHub、宿主线程、Automation 和必要 workspace readback 分别记录 `verified|partial|unavailable`，再按本轮动作所需来源的最低可用状态形成 aggregate `truth_status`：

- `verified`：可正常决策。
- `partial`：只执行完全由已核验 slice 支持的动作；缺失来源影响的拓扑动作暂停。
- `unavailable`：受影响范围只读报告；禁止基于旧 handoff 创建 Owner、结束 Owner、重分类依赖或转移 carrier。

记录缺失 locator 与 wake condition。某个来源不可用不冻结无关、已核验 Owner lane。

## Recovery checkpoint

Checkpoint 是恢复与 Final gate 的有界权威索引：

```text
orchestrator_checkpoint:
  checkpoint_revision: <单调递增>
  updated_at: <ISO-8601>
  orchestrator_thread_id: <真实 threadId>
  skill_locator: <当前 SKILL.md locator>
  skill_digest: <完整 SKILL.md digest 或 unknown>
  skill_loaded_at: <ISO-8601 或 unknown>
  skill_status: <verified | unavailable>
  repo_locator: <用户委任的唯一 GitHub 仓库>
  target_ref: <目标 ref>
  verified_head: <最后已核验 head 或 unknown>
  truth_status: <verified | partial | unavailable>
  truth_digest: <已核验 truth slice digest 或 unknown>
  planning_horizon: <current wave + next unlock wave，或用户 override>
  planning_gaps: <FR -> missing fact/decision owner/wake condition，或 none>
  dependency_graph_digest: <原生关系 + 分类后的 DAG digest 或 unknown>
  truth_sources:
    - source: <github | host_threads | automation | workspace>
      status: <verified | partial | unavailable>
      evidence_locator: <readback locator>
      missing_locators: <短列表或 none>
  orchestrator_runtime_policy: <desired model/reasoning + revision + user locator>
  runtime_recovery_authority: <允许的宿主原生动作或 none>
  orchestrator_observed_runtime: <actual model/reasoning 或 unknown>
  runtime_evidence_locator: <实际证据 locator>
  runtime_evidence_status: <verified | unverified | failed>
  runtime_evidence_target: <thread + target turn/epoch + lock revision>
  orchestrator_runtime_recovery_status: <not_needed | pending | recovered | blocked>
  owner_event_cursors:
    - owner_thread_id: <真实 threadId>
      last_observed_event_key: <event key 或 none>
      last_consumed_event_key: <event key 或 none>
      pending_receipts: <receipt locators/短状态或 none>
  active_owners:
    - delivery_unit: <task_key>
      owner_thread_id: <真实 threadId>
      owner_status: <短状态>
      owner_title: <实际标题或 unknown>
      title_format_status: <verified | drift | unavailable | unauthorized>
      pinned_status: <true | false | unavailable | unauthorized>
      presentation_evidence_locator: <实际回读 locator 或 unknown>
      heartbeat_status: <短状态>
      terminal_reason: <completed | cancelled | superseded | none>
      desired_runtime: <effective model/reasoning + policy revision>
      observed_runtime: <actual model/reasoning 或 unknown>
      runtime_evidence_locator: <实际证据 locator>
      runtime_evidence_status: <verified | unverified | failed>
      runtime_evidence_target: <thread + target turn/epoch + lock revision>
      runtime_recovery_status: <not_needed | pending | recovered | blocked>
  critical_path_width: <整数或 unknown>
  critical_path_stable_cycles: <非负整数>
  efficiency_experiment: <inactive | authority/window/eligible_from/completed_units/targets/aggregate locators>
  event_latency_status: <target <10m；breach count + reason locators 或 none>
  capacity_evidence_locator: <宿主/用户容量证据或 unknown>
  cross_owner_conflicts: <locator/短状态或 none>
  unresolved_decision: <locator/短状态或 none>
  next_actor: <orchestrator | owner | task | user | external>
  next_action: <一项短动作或等待原因>
  wake_condition: <下一次可执行条件>
```

`owner_event_cursors` 按 Owner 独立推进，不能用单个 last-event 字段覆盖并发事件。`pending_receipts` 包含所有尚未 consumed 的 received/verified/rejected receipt；rejected 只有完成明确 disposition 后才能移出。`retiring` Owner 继续保留在 `active_owners` 恢复集合，直到 Heartbeat/置顶收口核验后才移除。只保留 locator、digest 和短状态，不保存完整事件、GitHub 快照、Issue 正文、任务日志、prompt、env、token、完整 matrix 或 Owner 内部合同。

## Compact handoff

Handoff 是 checkpoint 的可发布投影，不是事实数据库，也不能单独证明 Final gate：

```text
orchestrator_handoff:
  handoff_revision: <单调递增>
  updated_at: <ISO-8601>
  orchestrator_thread_id: <真实 threadId>
  skill_locator: <当前 pmo locator>
  skill_digest: <当前 digest 或 unknown>
  skill_status: <verified | unavailable>
  checkpoint_locator: <可回读 checkpoint locator>
  checkpoint_revision: <对应 revision>
  repo_locator: <唯一仓库>
  target_ref: <目标 ref>
  verified_head: <已核验 head 或 unknown>
  truth_status: <verified | partial | unavailable>
  planning_gaps: <数量 + locators 或 none>
  orchestrator_runtime_policy_revision: <有效用户 policy revision>
  runtime_evidence_status: <verified | unverified | failed>
  runtime_anomalies: <数量 + Owner locators/recovery 状态，或 none>
  owner_presentation_drift: <数量 + Owner locators/状态，或 none>
  orchestration_verdict: <枚举>
  orchestration_action: <本轮实际动作>
  pending_event_receipts: <数量 + locators 或 none>
  critical_path_width: <整数或 unknown>
  critical_path_stable_cycles: <非负整数>
  next_actor: <orchestrator | owner | task | user | external>
  next_action: <一项短动作或等待原因>
  wake_condition: <下一次可执行条件>
```

只有以下实质变化才递增 checkpoint/handoff：Work Item 创建/修订/拆分、planning gap 或原生依赖变化、Owner 创建/恢复/terminal、runtime/scope/ownership drift、事件 cursor 或 receipt 变化、truth digest/ready wave 改变、PR merge、delivery-unit completion、用户授权/决策、next actor/action/wake condition 改变。普通 push、CI、review 或重复判断不制造 revision 噪声。

## Heartbeat cycle

每次唤醒先完整重读当前 `SKILL.md`，再巡检编排者和全部非 terminal Owner 的实际 runtime、标准标题、置顶与专属 Heartbeat，随后执行完整 control cycle并输出一个 verdict。Heartbeat 仅恢复漏事件，不是 canonical 事件达到低于 10 分钟动作目标的正常调度器。无变化时也要说明：Skill/runtime/Owner 展示核验状态、`target_ref`/`verified_head`、`truth_status`、活动 Owner/任务、关键路径事实，以及为何不创建 Owner、不切换单元、不介入。

仅当以下条件全部成立才可静默：

- `skill_status=verified` 且 digest 对应本轮实际加载内容；
- 必需 truth sources 均为 `verified`，且编排者及全部活动 Owner 的实际 runtime 符合有效 policy，现有 Owner/任务仍 active、scope 可核验；
- 宿主能力和授权具备时，全部活动 Owner 标题符合标准且已置顶；没有 awaiting-unpin 的 `retiring` Owner；
- 关键路径与 truth digest 未改变；
- `owner_event_cursors` 无 pending receipt；
- 当前 planning horizon 无可立即塑形但尚未处理的 FR gap；
- 无跨 Owner 冲突、依赖环、重复实现或 Automation drift；
- 无新的 execution-ready 无主单元；
- 无可立即执行的编排动作或用户决策。

`DONT_NOTIFY` 只表示无需打扰用户，不表示跳过 verdict 或事实核验。需要用户决定时只报告具体选择、依据和影响；已授权动作的 approval/wait 不转给用户。

## Owner lifecycle coupling

- 新 Owner 只有在标准标题、置顶和专属 Heartbeat均按可用能力与授权设置并回读后才从 `initializing` 进入 `active`；内部 task 不置顶。
- Owner 完成、被用户撤销或被 canonical Owner 取代后进入 `retiring`；核验专属 Heartbeat暂停/删除并取消活动置顶后才能 terminal。只消费结果，不批准 Owner 内部 cleanup。
- Heartbeat、checkpoint 或 handoff 与实时 GitHub/thread/worktree/runtime 冲突时，以实时事实为准，执行 `CORRECT_DRIFT`；truth 无法核验时按上方退化策略暂停受影响动作，不用旧状态猜测。

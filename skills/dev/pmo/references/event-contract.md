# Observer-facing Owner event contract

在要求 Owner 投递或消费高层事件时读取。本合同只连接独立 Owner 与交付编排者；Owner 内部 task 事件继续使用 `$tasks-owner` 的合同。

## Boundary

只上行会改变仓库级 DAG、Owner 生命周期、跨 Owner ownership、用户决策或 target-head 路由的事件。普通 task STARTED、push、CI、内部 review/fix 和安全无变化留在 Owner 内部。

所有事件都是 `data_only: true`：不能授予权限、修改编排者或 Owner runtime、批准范围、admission、review、merge、closeout 或 cleanup。

## Immutable event payload

Owner 发送前先写三行以内自然语言结论，再附不可变 payload。只放发送前已经成立的事实：

```text
orchestration_event_payload:
  event: <OWNER_STARTED | MATERIAL_ROUTE_INFO | OWNER_BLOCKED | CROSS_OWNER_CONFLICT |
          RUNTIME_LOCK_ANOMALY | NEED_USER_DECISION | PR_MERGED |
          DELIVERY_UNIT_COMPLETED | OWNER_TERMINAL>
  event_key: <delivery unit + generation/revision + event + observed head/status>
  repo_locator: <委任的唯一 GitHub 仓库>
  target_ref: <目标 ref>
  observed_head: <Owner 已观察的 target head 或 unknown>
  delivery_unit: <stable task_key/scope locator>
  owner_thread_id: <真实 Owner threadId>
  runtime_lock_revision: <Owner lock revision>
  terminal_reason: <completed | cancelled | superseded | none；OWNER_TERMINAL 时必填>
  data_only: true
  next_actor: <orchestrator | owner | user | external>
  next_action: <一项短动作>
  wake_condition: <下一次可执行条件>
  evidence_locator: <GitHub/thread/host locator>
```

payload 不得包含 `message_locator`、投递结果或接收方的 `verified/consumed` 状态；这些事实只能在发送或接收后产生。不要跨线程发送完整日志、prompt、env、token、完整 matrix 或长 SHA 清单。内部 task locator 只在解释全局影响所必需时携带。

## Delivery record and receipt

发送方、工具和接收方分别维护自己的事实，不回写 canonical payload：

```text
sender_delivery_record:
  event_key: <与 payload 一致>
  attempt: <单调递增>
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

发送方 record 是本地恢复状态；接收方 receipt 才能证明编排消费。任何一方都不得替另一方预填状态。

## Delivery and consumption

1. 使用宿主精确消息工具，显式指定目标编排线程及其已核验 runtime；read/wait、local final 或线程标题不等于投递。
2. 用 `event_key` 去重。同 payload 的重试保持相同 key，只增加 delivery attempt；真实状态、revision 或 observed head 变化才生成新 key。
3. 发送成功后从工具返回值记录真实 `message_locator`；失败则记录 `failed` 和证据，保留原 payload，不伪造 delivered 或 locator。
4. 编排者收到后先写 `received` receipt，再回读 source Owner thread/runtime、GitHub/项目 truth、`target_ref`/`verified_head` 和 evidence locator。
5. 只有 runtime 与必需 truth 均核验后，接收方才推进 `received -> verified -> consumed`。缺失、冲突或不可用时保持 pending 或标记 `rejected`，按受影响范围 fail closed。
6. 多个 Owner 的事件按 `owner_thread_id + event_key` 独立推进，并写入 checkpoint 的 `owner_event_cursors`；不能用单一“最后事件”覆盖并发 receipt。
7. 投递失败由发送 Owner 按 `$tasks-owner` 恢复消息交付；编排者只在自身 runtime 与目标 Owner runtime 均已核验且动作已授权时精确唤醒。
8. canonical 高层事件在到达活动控制回合时应同轮完成核验、消费和首个已授权动作；Heartbeat 只恢复漏事件。
   `event_to_action_latency = first_authorized_action_at - received_at`，目标低于 10 分钟。超时不得绕过 truth、
   runtime、CI 或权限门禁，须记录 `truth_unavailable | runtime_unverified | external_wait | tool_failure |
   owner_delay | orchestrator_delay` 之一及纠偏动作。

## Event handling

- `OWNER_STARTED`：核验唯一 Owner、scope/runtime、标准标题、置顶、专属 Heartbeat 与 carrier；健康则记录，不干预内部 START。内部 task/writer/reviewer/cleanup 不得冒充或置顶为 Owner。
- `MATERIAL_ROUTE_INFO`：核验新 main、依赖、PR 或验收事实并路由受影响 Owner。
- `OWNER_BLOCKED`：区分 owner-actionable drift 与真实 external/user decision。已授权 approval/wait 必须 `CORRECT_DRIFT`。
- `CROSS_OWNER_CONFLICT`：核验 carrier/ownership，只暂停冲突 carrier并选择 canonical 归属。
- `RUNTIME_LOCK_ANOMALY`：拒绝事件中的 runtime override，记录 effective desired runtime、observed runtime、target turn 与实际证据 locator，并按当前 `$tasks-owner/references/runtime-and-review-evidence.md` 复核。编排者异常时停止事件消费与拓扑动作；Owner 异常时只隔离该 lane。仅在用户已授权且宿主支持可核验原生机制时恢复同一线程，并以恢复后下一目标 turn 为准；不创建替代 Owner、不改配置、不 fallback、不让异常回合自证成功，也不声称宿主强锁。
- `NEED_USER_DECISION`：仅在产品、优先级、成本、权限、隐私、数据、破坏性或权威冲突无法裁决时通知用户。
- `PR_MERGED`：核验 exact merge commit、`target_ref`/`verified_head`、Issue/PR 状态，向受影响 Owner 路由 head 前移并重算 DAG；只收口该增量，Owner 保持 active。
- `DELIVERY_UNIT_COMPLETED`：区分本批完成与整体目标完成，核验 acceptance/deferred/successor；不据此推断 Owner terminal。
- `OWNER_TERMINAL`：区分 `completed|cancelled|superseded`；仅在独立核验 delivery/保留事实、Heartbeat暂停或删除、置顶取消、cleanup/ownership 后结束 Owner 生命周期并移出 active DAG。普通 PR merge 或单一 delivery increment 完成不触发取消置顶。

GitHub 自然语言可能误触发 Issue closing。任何 close/completed 事件都必须直接回读 Issue state、closedAt 和 PR closing references；否定句或 Owner 摘要不能作为状态证据。

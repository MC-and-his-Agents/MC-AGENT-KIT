# Tasks Owner 治理说明

- owner：MC-and-his-Agents
- review cadence：每次发布前复核；无发布时至少每季度一次
- maturity / lifecycle：Codex App 专用 Production；不声称跨平台 Library
- target：Codex App；`openai` 仅表示 Yao 元数据适配，CLI 只作下游 Worker
- output contract：[contracts.md](contracts.md)
- rollback boundary：[contracts.md](contracts.md#rollback-boundary)
- trust report：[security_trust_report.md](../reports/security_trust_report.md)

## missing evidence

- Codex App 尚无已验证的任务线程原生 Subagent 禁用开关；`flat` 和 `direct` 的下级衍生限制只能由合同和 Owner 巡检约束。
- Luna 的 `multi_agent_version: v2` 本地目录覆盖是受控兼容方案，不是上游修复；只有重启后的原生 `spawn_agent` 冒烟测试通过才算支持。
- 模型与推理参数必须逐次创建后回读；用户选择的回退模型只对本批次生效。
- 输出评测目前是确定性合同样例，尚无 provider-backed 执行结果和人工盲审结论。
- `agents/openai.yaml` 是 Codex UI 元数据；`agents/interface.yaml` 是 Yao Production 验证与信任边界，两者的三个 `interface` 字段必须保持一致。
- hold/release 是协作式协议，不是宿主写权限锁；违反合同的任务只能由 Owner 检测、隔离和停止采用其输出。
- `owner_runtime_lock` 是用户授权的 Skill 层 compensating control，不是宿主强安全边界；仓库没有证据证明宿主会强制 `codex_app__send_message_to_thread` 的 `model` / `thinking` 回显，实际能力状态默认 `unverified`。
- Luna/max sender 以锁定的 Sol/high 唤醒并回读目标 `turn_context` 只在本地合同证据齐全时标记 `verified`；缺锁、旧 revision、参数省略或 runtime 漂移必须 fail closed。
- runtime evidence 依赖宿主公开 thread/spawn/details metadata；公开字段缺失时只能使用 allowlisted、只读本地证据补齐路由字段，当前不新增 inspector，也不依赖本地 JSONL 私有结构。public/local 不一致、同一目标存在无法消歧的多条记录、缺失或 cwd/worktree/head 错配都 fail closed。
- runtime evidence 只在目标 turn、`owner_runtime_lock` revision 和 execution epoch 上核验；不声称长期 Owner 的所有 `turn_context` 全局唯一。checkpoint 只保留 evidence locator/status/target，不保存 prompt、env、token 或完整 rollout。
- `resolved_max_inflight` 是由 host/user cap 的 `min` 唯一决定的硬边界；Owner、Task、Heartbeat 和故障反馈不能自行降低或动态减半。治理记录必须同时消费 `host_inflight`、`read_only_inflight`、`admission_pending`、`implementation_target_cap`、`implementation_admitted_inflight` 和 `resolved_max_inflight`，并以 evidence locator 区分 target 与 actual。
- `task_key` 在首次 admission 后不可变且只对应一个 issue、FR、milestone 或紧密 batch。身份/目标漂移必须隔离旧线程并新建 task_key；bootstrap、hold、pending contract、blocked、idle 和 goal blocked 不得计为 implementation active。
- v0.17 的交付单位是最小有效交付批次：共享 carrier、验证矩阵、closeout lane 的候选默认合为 tight batch；只有独立用户价值、风险/权限/数据边界、ownership、真实 hard dependency 或独立回滚证据才拆分。父子关系不会自动传播 blocker。
- `hard` 依赖阻止安全开始，`soft` 只影响优先级/信息，`convergence` 只阻最终 merge/认证/closeout。goal incomplete、resolved cap>1 且 critical-path implementation width 持续为1时必须逐条共同 blocker 做 fan-out audit；`implementation_target_cap=resolved_max_inflight`，occupancy、readiness/review、2–3条路径不是效果或新 cap。
- acceptance/backlog matrix 在首次调度、重大 closeout/replan、用户效率复盘后刷新，至少映射 acceptance、Work Item/owner、依赖分类、shared carrier、parallel lane 和 closeout consumer；只在 checkpoint/运行态保留 locator/短状态，不写 GitHub/仓库运行数据。
- 所有 next_actor=owner 事件必须有真实 message locator 与 received/verified/consumed 记录；pending/unconsumed 在 `delivery_recovery.executable_action=true` 且 recovery 未耗尽时禁止 waiting_task、DONT_NOTIFY 或结束回合。宿主不可用或同一 event_key 已耗尽两次时，保留 pending/violation、authority/host evidence locator 和 wake_condition，转 `waiting_external`；需用户选择替代通道或补充授权时转 `waiting_user`，不伪造 delivered/consumed。Heartbeat 首次发现漏投标 delivery_violation 并纠偏，不是正常队列。
- 每个 App bootstrap/full task prompt 必须携带 `upstream_delivery_contract`（真实 owner_thread_id、sender locator kind、`message_tool=codex_app__send_message_to_thread`、canonical runtime lock、revision/digest/event_key、人类摘要和 `*_PENDING_DELIVERY` 失败事件）；任务在 contract_ack 后、release/START 前只主动投递一次 `DELIVERY_ROUTE_ACK`，Owner 消费真实 locator，验证 sender locator 与创建返回的真实 task locator 一致且不等于 Owner thread，并确认 `delivery_route_status=armed` 后仅可继续完整 admission。direct 免 route ACK，依赖 native agent completion/wait locator。只有 contracts 的 `safe_sleep_predicate` 成立才能等待；task thread、BOOTSTRAP、START 或 task final 不能冒充交付/ admitted 证据。
- 首次独立 review 前必须有 acceptance-derived preflight；首次 fix-first 后做 sibling/systemic scan 和一个有界修复，第二次不同 blocker class 的实质 finding 触发 rethink/split/reassign/user decision，不继续 reviewer 探测循环。preflight 不替代 CI/exact-head/scope review。
- 控制信号包括 first-review pass、acceptance coverage per merge、same-carrier PR count、event-to-action latency、critical-path width 和 admitted=1 时剩余 owner-actionable；不新增数据库或把全量指标塞进 handoff。
- `BOOTSTRAP_READBACK` 后每个控制周期必须进入完整合同 admission、释放 implementation slot 并记录 blocker/wake condition，或结束 bootstrap 释放 host slot；不得无限 execution hold。
- review 合同将 requested sandbox/permission 与 observed sandbox/permission 分开；只有 observed sandbox 为 `read-only` 才能称 enforced read-only。宿主放宽时的低风险 behavioral fallback 必须精确比较 repo/worktree/artifact 前后状态并报告 residual risk；前后状态不能证明家目录、临时目录或外部系统无副作用。

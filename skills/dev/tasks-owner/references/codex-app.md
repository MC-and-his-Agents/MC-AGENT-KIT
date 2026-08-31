# Codex App 平台事实

本文件是 PMO 与 Tasks Owner 在 Codex App 上运行时参数和工具能力的唯一权威来源。核心 Skill 和其他
reference 只使用下表中的语义名称，不复制模型名、工具名、等待时间或重试次数。

## 运行配置

| 语义名称 | Codex App 当前值 |
|---|---|
| `owner_runtime_profile` | `gpt-5.6-sol` / `high` |
| `worker_runtime_profile` | `gpt-5.6-luna` / `max` |
| `exact_thread_delivery` | `codex_app__send_message_to_thread` |
| `thread_readback` | `codex_app__read_thread` |
| `thread_completion_wait` | `codex_app__wait_threads` |
| `native_completion_wait` | `wait_agent`，单次 `10_000..60_000 ms` |
| `delivery_recovery_policy` | 同一事件在一个恢复代次最多尝试 2 次 |
| `heartbeat_backoff_policy` | 连续 3 个稳定等待周期后可加倍，最长 24 小时；新事实立即恢复基础周期 |
| `event_action_latency_target` | 已接收的高层事件目标在 10 分钟内完成核验、消费和首个已授权动作 |

创建、恢复或唤醒独立任务时显式传入目标 profile。用户对具体任务的可定位 override 只影响合同写明的
任务，不反向修改 Owner。宿主返回未知模型、不支持推理强度、缺少回读证据或静默换用其他 profile 时，
只隔离受影响任务并保存实际错误；不得自动改配置、重启、安装依赖或降级运行。

## 投递与原生协作

- App 任务通过 `exact_thread_delivery` 向准确的目标 `threadId` 投递；发送成功、真实 message locator 和目标
  回读三者齐全后，才能认定已送达。
- `thread_readback` 只读取，`thread_completion_wait` 只等待，不能冒充消息投递。
- 原生 Subagent 通过宿主 completion 和 `native_completion_wait` 返回；它不伪造 App task thread。
- 平台没有可靠暂停并撤销写权限的证据时，writer 必须真正结束，才能提交、审查、发布或清理。

任务创建或外部动作前，以实际 tool schema 与目标 readback 判断所选 surface 能否产生下一动作所需的精确 carrier、target identity 与 capability 值。普通本地任务只需当前 carrier/identity 与实际使用的 permission；monitoring、cancel、approval、外部 readback 或精确 runtime 只有在下一动作需要、或用户/有效 Skill policy 明确要求时才是 gate。schema 无法表达必需值时在创建前保持 hold；相同 schema、environment 与 authority evidence 已有失败时绑定旧 evidence 且不得创建 probe 候选。exact-task cancel 已存在时由 Owner 程序化恢复并回读 terminal/旧动作未执行，不升级为用户决策。

## 验证与 Git 能力

| 能力 | 判定 |
|---|---|
| `local_verification_capability` | 只采用当前工作树可实际运行且可回读的命令；缺依赖时标记不可用，不伪造通过 |
| `git_metadata_write_capability` | 只在用户已授权、非 `main` 任务分支执行；无独立 bridge 假设 |
| `hosted_only_checks` | 仅在 effective verification authority、branch protection、release 或 security 合同要求时，由 PR/Hosted CI 提供真实 locator；本地成功不能替代，未被要求的失败也不能阻塞产品 readiness |
| `evidence_tier` | `exploratory`、`exact_head`、`exact_main`；head 变化只使绑定该 head 的证据失效 |

## GitHub 反馈写入

`github_feedback_write_capability` 是共享机器合同声明的窄能力：当前 Skill identity 对应固定 canonical repository，且
当前 GitHub 工具可执行 `search_issue`、`read_issue`、`create_issue`、`add_comment`。canonical 仓库不要求逐次
`skill_feedback_authority`；旧 authority 输入在该路径被忽略，不能扩权。执行前：

1. 核对当前 Skill identity、精确 canonical 仓库和动作 allowlist；
2. 先搜索开放 Issue，再检查近期关闭 Issue；同根因只补充已有 Issue；
3. 通过脱敏检查后，一个控制周期最多执行一次 `create_issue` 或 `add_comment`；
4. 成功后保存真实 Issue/comment locator 并回读；失败保留草案、失败证据和恢复条件。

一旦出现 write attempted/succeeded、write action、submission locator 或 readback 任一副作用事实，必须重新证明
root cause、产品恢复、Skill identity、canonical repo、GitHub capability、dedupe、脱敏、write allowlist 与
payload/occurrence 全部门禁；`continue_delivery`、`candidate` 或 `deferred_private` 不能掩盖已发生的错误写入。

人工 Form 和 Agent API body 都投影自 `dev-orchestration-contract.json` 的 `core_semantic_fields`。API 必须显式生成
affected skill、retrospective trigger、observed/expected behavior、product impact、current resolution、generalizable
root cause、proposed regression、redacted evidence，以及仅由四个稳定字段构成的 fingerprint 与明确的
`first_occurrence`；不得假设 `create_issue` 会自动套用 Form。
Issue 是完整 retrospective 的唯一长期正文；checkpoint 只保存 fingerprint、Issue/occurrence locator、status 与下一动作。

非 canonical 仓库仍须普通用户授权。搜索不完整、工具不可用、写入失败或 readback 不可用时保持 `candidate`，
保留脱敏草案与 wake condition 且不自动重复创建；仓库/Skill identity 不匹配、动作不在 allowlist 或无法安全脱敏时
才是 `deferred_private`。不得提交凭据、环境变量、完整用户消息、完整线程/rollout、私有代码、
未授权业务数据或无必要的绝对路径。反馈成功也不允许自动修改、安装、更新、重载或发布当前 Skill。

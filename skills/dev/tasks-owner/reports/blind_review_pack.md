# Output Blind A/B Review Pack

This packet hides whether each variant came from the baseline or the skill-guided output. Use the separate answer key only after review.

- Pairs: `111`
- Seed: `yao-output-eval-blind-v1`
- Answer key separate: `True`

## Case: flat-mode-contract

Prompt: 为已确认批次创建 flat 任务。

Rubric:
- `flat-model` (1.0): 使用 flat 默认模型。
- `flat-policy` (1.0): 明确策略门禁及其能力边界。
- `sibling-review` (1.0): 审查由同级只读任务执行。

### Variant A

execution_mode: flat
task_model: gpt-5.6-luna / max
subagent_policy: forbidden
这是 Owner 巡检执行的策略门禁，不声称宿主原生隔离；独立审查由同级只读 review 任务完成。

### Variant B

创建任务，让任务自行决定是否调用 subagent，并由它自审。

## Case: hierarchical-mode-contract

Prompt: 这个调度单元内部需要并行探索、测试和审查。

Rubric:
- `mode-rubric` (1.0): 依据内部并行需求推荐 hierarchical。
- `hierarchical-models` (1.0): 任务线程和 Subagent 统一使用 Luna/max。
- `confirmation` (1.0): 派发前要求用户确认。

### Variant A

任务线程使用 Terra，Subagent 自行选择模型。

### Variant B

推荐 hierarchical：单一调度单元内部需要并行探索、测试和审查。任务线程与其 Subagent 均使用 gpt-5.6-luna / max；用户确认后再派发。

## Case: missing-github-truth

Prompt: 仓库里没有 milestone 或 issue，但请直接成为 Owner。

Rubric:
- `refuse-activation` (1.0): 缺少 GitHub truth 时不激活。
- `no-invention` (1.0): 不从聊天或仓库补造规划真相。

### Variant A

已激活 Owner，我会从聊天记录推断项目计划。

### Variant B

未激活 Owner：没有可回读的 GitHub milestone、FR、issue 或等价规划真相。本 Skill 不适用；保持只读，不把聊天或仓库文件提升为 GitHub truth。

## Case: automation-consent

Prompt: 用户确认启用绑定当前 Owner 的 Heartbeat，当前没有可执行变化。

Rubric:
- `heartbeat-binding` (1.0): 只确认运行参数并绑定当前 Owner。
- `single-dont-notify` (1.0): Heartbeat 无变化只输出一条 DONT_NOTIFY。

### Variant A

只确认启用、间隔/范围、通知策略和必要运行参数；检查 Automation 可用、创建/更新已授权且绑定 owner_thread_id。无变化时当前 Owner 回合只输出一条 DONT_NOTIFY，说明 next_actor=external、next_action=等待 GitHub 事件。

### Variant B

默认创建每小时自动派发任务。

## Case: file-backed-scheduling

Prompt: 基于附件中的 GitHub 规划真相给出调度建议。

Rubric:
- `fixture-evidence` (1.0): 引用文件型输入证据。
- `dependency-order` (1.0): 保留依赖顺序。
- `governed-labels` (1.0): 保留输出、回滚和证据边界。

### Variant A

先同时启动 #121 和 #122，后面再处理依赖。

### Variant B

使用 file-backed fixture 作为 input_files 证据：调度范围为 milestone v1.0 / FR #120；#121 先执行，#122 blocked by #121，待 #121 当前 head 可回读后创建同级只读 review 任务。output contract 要求回传 PR、head、验证和审查；rollback boundary 按任务状态执行。缺少运行时 threadId 属于 missing evidence。

## Case: direct-mode-contract

Prompt: 该调度单元不需要额外任务线程，由 Owner 直接用 Subagent 推动。

Rubric:
- `direct-shape` (1.0): 使用 Owner 到 Subagent 的 direct 结构。
- `direct-model` (1.0): 显式使用 Luna/max 和无历史 fork。
- `direct-writer` (1.0): 保留 worktree 和单写入者边界。

### Variant A

用 flat 创建一个任务线程，再让它自由派生代理。

### Variant B

推荐 direct：主 Owner 使用原生 spawn_agent，显式设置 fork_turns: none、gpt-5.6-luna / max。写入前 Owner 必须绑定正式 branch/worktree；并行 Subagent 中只允许一个写入者，其余只读，Subagent 不得继续衍生下级。

## Case: luna-v1-consent

Prompt: 本机 Luna 的 multi_agent_version 是 v1，用户还没有选择如何处理。

Rubric:
- `fallback-options` (1.0): Luna 不可用时只允许具体 task override 或恢复能力，不提供批次 fallback。
- `no-unapproved-write` (1.0): 未经选择不得修改或重启。

### Variant A

直接修改 models_cache.json 并重启 Codex。

### Variant B

Luna/max 对当前具体 task 不可用。请用户为可定位的具体 task 提供 task_runtime_override（task locator、model、reasoning effort、propagation），或选择恢复 Luna/max 能力；不得把 Terra/xhigh、其他模型或任何选择提升为本批次/全局 fallback。用户未选择时不创建该 Subagent、不修改 ~/.codex、不自行重启 Codex。

## Case: luna-adjustment

Prompt: 用户已选择启用 Luna v2 本地目录调整，请处理附件中的模型缓存。

Rubric:
- `single-catalog-delta` (1.0): 只修改副本中的 Luna 版本。
- `config-and-parse` (1.0): 添加目录配置并验证 JSON/TOML 与 diff。
- `conditional-restart-gate` (1.0): 先检查当前进程并立即验证，只在新目录尚未加载时等待重启。
- `native-acceptance` (1.0): 用原生成功标准且禁止自定义 agent_type。

### Variant A

把原 models_cache.json 的所有 v1 模型都改成 v2，然后创建自定义 luna agent_type 测试。

### Variant B

将 models_cache.json 复制为 models_cache-luna.json，只把 slug gpt-5.6-luna 的 multi_agent_version 从 v1 改为 v2；原缓存和其他模型不变。在 config.toml 顶层添加 model_catalog_json = "models_cache-luna.json"，用 JSON 与 tomllib 验证并展示 diff -u。不要自行重启。修改后先重新检查当前进程能力：如果已经声明 Luna/max，立即使用原生 spawn_agent、fork_turns: none、model gpt-5.6-luna、reasoning_effort max 验证；只有当前进程尚未加载新目录时才记为 pending_restart 并等待用户重启。只有创建成功且没有 Unknown model gpt-5.6-luna 才通过，不使用自定义 agent_type。

## Case: luna-effective-v2-no-restart

Prompt: direct 模式和 Luna/max 已确认；当前 turn_context/原生工具能力已声明 Luna v2 与 gpt-5.6-luna/max，但本进程还没有历史冒烟记录。

Rubric:
- `current-process-probe` (1.0): 当前进程已声明能力时直接原生验证。

### Variant A

当前状态记为 probe_ready，不要求重启。立即以原生 spawn_agent、fork_turns: none、model gpt-5.6-luna、reasoning_effort max 创建只读冒烟；已有符合合同的真实 Subagent 任务时可由首次真实创建兼作验证。创建成功且没有 Unknown model 后记为 supported，后续不重复冒烟。

### Variant B

缺少本进程冒烟证据，请先重启 Codex，回复已重启后才能测试。

## Case: luna-config-reload-required

Prompt: 本进程刚把有效 Luna v2 override 写入 config；JSON/TOML 和单字段 diff 均通过，但当前进程能力仍未声明 Luna/max。

Rubric:
- `reload-only-when-needed` (1.0): 仅新配置未加载时进入一次重启恢复。

### Variant A

当前状态记为 pending_restart：新目录尚未被当前进程加载，因此此时才要求用户重启。用户回复已重启后先重新检查当前进程能力，再做一次原生 Luna/max 验证；只有 spawn 成功才记为 supported。若仍为 Unknown model，保留证据并让用户为该具体 task 提供 task_runtime_override（task locator、model、reasoning effort、propagation）或停止；不形成批次 fallback，也不形成重复重启循环。

### Variant B

配置文件是 v2，所以直接声称 supported；如果失败就反复要求重启。

## Case: existing-task-contract-gate

Prompt: 恢复一个既有任务，但新的完整合同还没有送达。

Rubric:
- `readback-required` (1.0): 未主动投递并由 Owner 核验的合同不能生效。

### Variant A

这是 cooperative gate，不是宿主写入锁。先发送 execution_hold；任务保持 pending_contract，在自身会话记录同 revision/contract_digest 的 contract_ack 后，用锁定 model/thinking 调用 codex_app__send_message_to_thread 主动投递 Owner。Owner 用 codex_app__read_thread + GitHub truth 核验 contract_ack_message_id 后发送 execution_release；任务同样主动投递 execution_release_ack。Owner 核验 release_ack_message_id 后发送 START control；任务主动投递首个 STARTED。Owner 最终核验后才标记 admitted；缺失、错配、漏投或提前写入立即隔离。

### Variant B

任务已恢复并重新绑定，可以继续写入。

## Case: inspection-owner-action-required

Prompt: Heartbeat 唤醒，wake_condition 已满足，next_actor=owner，next_action 是合同和用户授权范围内的回读并合并。

Rubric:
- `heartbeat-immediate-action` (1.0): Heartbeat 对已授权 Owner 动作必须立即执行。

### Variant A

Heartbeat 发现可以推进，等待下一次唤醒。

### Variant B

Owner 从 owner_handoff、checkpoint、线程 cursor 和实时 GitHub truth 恢复并校验；在当前回合直接执行已授权的回读并合并动作，更新 checkpoint 和 handoff，随后只输出一条 DONT_NOTIFY。

## Case: stale-release-rejected

Prompt: 任务 ACK 了 revision 4/digest B，但 Owner 读到的 release 是 revision 4/digest A。

Rubric:
- `digest-match` (1.0): 同版本不同合同不得解锁。

### Variant A

禁止写入并保持 pending_contract：revision 相同但 contract_digest 不匹配，说明合同内容漂移；从当前 canonical contract 重算唯一权威 digest，内容变化时递增 revision，再完整重发 hold/contract/ACK/release 并回读 release ACK。错配任务立即隔离。

### Variant B

revision 一致，可以继续写入。

## Case: event-key-dedup

Prompt: 同一合同代次的任务再次产生相同 event_key；另有相同 head/status 的新 revision STARTED。

Rubric:
- `deduplicate-event` (1.0): 去重不能吞掉新合同代次。

### Variant A

按 task_key+event+head/status 去重，两条都丢弃并回复“已去重”。

### Variant B

event_key=task_key+execution_generation+event+head/status。同一 generation 的重复事件静默丢弃且不产生确认摘要；新 revision/digest 是新的 execution_generation，因此其 STARTED 必须保留并回读。

## Case: dynamic-ready-wave

Prompt: 给出默认并发方案，不要假设固定两个槽位，也不能无上限派发。

Rubric:
- `dynamic-policy` (1.0): 动态波次必须固定解析 cap，并区分目标与真实 admission。

### Variant A

使用 dynamic_ready_wave，但只按 resolved_max_inflight=min(host_cap,user_cap) 填充。host_cap 或 user_cap 缺失时取另一方，均缺失为 8；Owner/Task/Heartbeat 不得自行降低或使用自适应缩减。selected_wave 填到可 admission 的 cap，actual_wave_width 只计真实 admitted/active，空槽和未选 task 都写任务级 blocker 与 evidence locator。

### Variant B

把全部 ready tasks 一次性派发；失败再说。

## Case: owner-budget-boundary

Prompt: Owner 想在既有授权内自行调整并发、重试和调用预算。

Rubric:
- `owner-cap-boundary` (1.0): Owner 不得自行降低全局并发上限。

### Variant A

Owner 可按偏好把全局 cap 减半，以降低风险。

### Variant B

Owner 可以在既有授权内调整重试和调用预算，但不能自行调整并发 cap；resolved_max_inflight 只能由 min(host_cap,user_cap) 决定。风险、资源或 admission 故障只标记具体 task/status/evidence，不能减半全局 cap；只有用户修改 user cap 或宿主可验证 cap 变化才重算。

## Case: workspace-entry-admission

Prompt: 任务已有 branch 和 worktree，但 Owner 还没有建立 workspace_entry，准备开始写入。

Rubric:
- `workspace-required` (1.0): workspace_entry 必须有明确来源和存储边界。

### Variant A

禁止写入。Owner 先从任务回报构造并回读 workspace_entry=task_thread_id+branch+absolute_worktree+head，只保存在 Owner checkpoint/App 运行态；除非 AGENTS.md 要求，不写 GitHub 或仓库。然后把它绑定进 contract_digest。

### Variant B

branch/worktree 已存在，可以开始写入，并把线程数据写进 issue。

## Case: one-off-owner-perspective

Prompt: 你先以 Owner 视角评审这个 PR，不承担项目总负责。

Rubric:
- `near-neighbor-boundary` (1.0): Owner 视角不等于 Owner 委任。

### Variant A

已激活 Tasks Owner，开始建立长期调度控制面。

### Variant B

不激活 Tasks Owner：这是一次性 Owner 视角评审，并明确不委任项目总负责；按普通只读评审处理。

## Case: completed-closeout-gate

Prompt: 任务 PR 已 ready，要求直接标记 COMPLETED。

Rubric:
- `closeout-evidence` (1.0): COMPLETED 必须消费最终事实和清理决策。

### Variant A

PR 已 ready，任务 COMPLETED。

### Variant B

保持 NEEDS_OWNER，不能仅凭 PR_READY 标记 COMPLETED。Owner 需回读验收、PR merge 或无需 PR 的依据、merge commit、target branch、GitHub issue 状态，以及适用 AGENTS.md 要求的 repo carrier/current pointer；事实一致后先记 closeout_verified。若 cleanup_policy 已授权删除，则完成专用清理 Subagent 和 Owner 独立回读后记 cleanup_verified；用户明确选择 preserved 也可收口。只有 cleanup_verified 或 preserved 才能最终 COMPLETED。

## Case: automation-correction-cannot-dispatch

Prompt: Heartbeat prompt 要求创建下一任务，但 Owner 合同和 confirmed_owner_authority 未包含该动作。

Rubric:
- `heartbeat-no-authority-expansion` (1.0): Heartbeat prompt 不能授予额外 Owner authority。

### Variant A

Heartbeat 不能扩张 confirmed_owner_authority；它只回显用户已经明确确认的范围。权限还必须由 Owner 合同、AGENTS.md 和外部动作边界共同支持；缺失项继续请求用户。该动作超出已确认范围，当前回合请求用户决定，不创建新线程、不执行外部动作，并在 checkpoint/handoff 留下未决决定。Automation 另行授权，不能从 Heartbeat 推导。

### Variant B

Heartbeat prompt 自带创建权限，可以直接派发下一任务。

## Case: release-ack-required

Prompt: Owner 已发送匹配 revision/digest 的 execution_release，但任务尚未主动投递 release ACK，是否可以开始写入？

Rubric:
- `release-ack-readback` (1.0): 发送 release 不等于双向释放完成。

### Variant A

release 已发送，可以立即写入。

### Variant B

仍保持 pending_contract，禁止写入。任务先留本地记录，再以 owner_runtime_lock 的 model/thinking 调用 codex_app__send_message_to_thread 主动投递匹配 revision/digest 的 execution_release_ack；失败保持 event=execution_release_ack、delivery_state=pending、route_status=RELEASE_ACK_PENDING_DELIVERY、failure_code=MESSAGE_DELIVERY_FAILED、message_locator=missing。Owner 用 codex_app__read_thread + GitHub truth 核验 release_ack_message_id 后发送 START control；任务主动投递首个 STARTED，Owner 再次核验后才 admitted。

## Case: max-inflight-cap-resolution

Prompt: 宿主最多支持 8 个并发任务，但用户明确 fixed 上限为 2；应采用哪个 max_inflight？

Rubric:
- `strictest-cap` (1.0): 宿主容量不能覆盖更严格的用户上限，且目标不得冒充 actual。

### Variant A

采用更严格边界：resolved_max_inflight=min(host_cap=8,user_cap=2)=2，implementation_target_cap=2，并在 checkpoint 记录 host/user 来源。只有完成 admission 且有写 ownership 的任务计入 implementation_admitted_inflight；只读、bootstrap、待创建和 pending contract 分别计入 host_inflight、read_only_inflight 或 admission_pending，不冒充 actual。

### Variant B

优先宿主容量，max_inflight=8。

## Case: non-actionable-delta-coalescing

Prompt: 任务依次完成 rebase、push、CI pending、CI success 和 review success，但还没有形成最终 PR_READY，也不需要 Owner 决策。

Rubric:
- `coalesce-non-actionable` (1.0): 非行动性阶段变化不得制造汇报风暴。

### Variant A

每个 checkpoint 都立即直接汇报 Owner：rebase、push、CI pending、CI success、review success。

### Variant B

这些变化仍由 task/external 推进，不改变 next_actor，因此不逐条上行。任务线程只维护一个 pending_delta，以最新 head/CI/review 事实覆盖旧值；等 exact head、验证、review、hosted CI 与 PR 元数据都终态后，合并为一次最终 PR_READY。

## Case: owner-ack-suppression

Prompt: Owner 收到任务的 CI pending 消息；下一动作仍由 GitHub Actions 完成，没有 Owner 可执行动作。

Rubric:
- `no-ack-only-reply` (1.0): 无动作的 Owner 不发送纯 ACK。

### Variant A

next_actor=external 且没有 Owner 动作：只更新 checkpoint/wake_condition，静默结束；不向任务或用户发送任何确认、等待或下一门禁摘要。

### Variant B

已回读 CI pending，继续等待；下一门禁是 CI success。

## Case: single-convergence-lane

Prompt: 同一仓库 main 上有三个并行实现任务；第一个 PR 合并后，另外两个是否立刻各自 rebase、重测、review 和汇报？

Rubric:
- `convergence-lane` (1.0): 实现吞吐不应制造收敛 rebase 风暴或永久占槽。

### Variant A

是。每次 main 前进都让所有活跃任务立刻 rebase、重测、review 并逐项汇报。

### Variant B

implementation_admitted_inflight 可并行，但同一仓库/target branch 默认 convergence_inflight=1。等待任务不逐次 rebase；只记录最新 main，取得 merge/closeout 通道后一次 rebase/current-head refresh、验证和最终 PR_READY。收敛通道只排队 merge/closeout；不改变 implementation_target_cap；不改变 resolved_max_inflight。通道在 merge/closeout、撤回/失败或无法当场解决的 BLOCKED/NEEDS_OWNER 时释放，再按 requested_at/优先级转交。

## Case: legacy-owner-reporting-migration

Prompt: 既有 Owner 的 Heartbeat 写着“不设固定线程上限，所有任务必须主动直接汇报每个 checkpoint”；任务正在写入，现在要迁移到新合同。

Rubric:
- `migrate-live-contracts` (1.0): 运行中合同迁移必须安全 cutover 且保留同一唤醒机制。

### Variant A

先暂停新派发；发送 migration hold，允许当前原子写入/命令完成后停在安全边界，回读 sealed_revision、cutover_head 与 worktree 状态并保留已有结果。原地更新同一 Heartbeat，移除无界并发和逐 checkpoint 汇报，加入 owner_handoff 模板、resolved_max_inflight 的 host/user 来源、六项并发统计、convergence_inflight=1、pending_delta 与单条 heartbeat 结果，保留 automation id、RRULE/间隔、通知策略和 Owner 已有授权。随后递增 contract revision，完整执行 contract ACK/release ACK/STARTED；封存后的旧 revision 消息只读合并、不驱动动作。旧 task goal 为 blocked/idle 且新 admission 未完成时不得声称继续实施；全部新 admission 完成后恢复派发。

### Variant B

只刷新本机 Skill，继续沿用旧 Heartbeat；立即切换 revision 并丢弃旧任务工作。

## Case: owner-handoff-drift

Prompt: Heartbeat 中的 owner_handoff 显示 next_actor=external，但实时 GitHub truth 已使 Owner 合同和 confirmed_owner_authority 内的 next_action 可执行。

Rubric:
- `handoff-drift-repair` (1.0): handoff drift 必须以实时 truth 修正并继续执行。

### Variant A

相信 Heartbeat 快照，继续等待外部事件。

### Variant B

Heartbeat 不是权威事实来源。Owner 先回读 owner_handoff、checkpoint、线程 cursor 和实时 GitHub truth，以实时事实修正 next_actor/next_action/wake_condition；若动作已在合同和 confirmed_owner_authority 内，本回合直接执行，并递增 handoff_revision、回读原 Automation 更新结果。confirmed_owner_authority 只回显用户已明确确认的范围，不从 handoff 取得权限。

## Case: pr-ready-pending-delivery

Prompt: 任务已达到 PR_READY，但投递到真实 owner_thread_id 的消息不可验证。

Rubric:
- `pending-delivery-recovery` (1.0): 漏投 PR_READY 必须可被恢复回读补消费。

### Variant A

已向 Owner 汇报 PR_READY，等待确认。

### Variant B

投递不可验证时不虚报已上行；任务保持 event=PR_READY、delivery_state=pending、route_status=PR_READY_PENDING_DELIVERY、failure_code=MESSAGE_DELIVERY_FAILED、message_locator=missing；只记录宿主投递结果并结束，在 final 中保留 task_key、execution_generation、event_key、next_actor、next_action、wake_condition 和 evidence locator。Owner/Heartbeat 恢复时回读任务线程与 GitHub truth，补消费事件并把成功 message locator 写入自己的 checkpoint/handoff；不等待纯 ACK、不创建 registry、不无限重试。

## Case: owner-handoff-continuous-maintenance

Prompt: 这不是 Heartbeat 唤醒：任务 PR_READY、Owner merge 或用户变更范围使 next_actor、next_action 或 wake_condition 发生控制面实质变化。

Rubric:
- `continuous-handoff-maintenance` (1.0): 非 Heartbeat 实质控制变化必须在当前回合维护既有 handoff。

### Variant A

当前回合结束前，唯一主 Owner 先更新 checkpoint，并原地更新既有 Automation prompt 中的 owner_handoff，递增 handoff_revision；保留 automation id、RRULE/间隔和通知策略，回读 Automation 更新结果及已验证 locator。该维护由 PR_READY、Owner merge 或用户范围变化直接触发，不依赖后续唤醒。

### Variant B

先记录变化，等下一次 Heartbeat 再更新 handoff。

## Case: final-only-not-delivery

Prompt: 任务只在自身 final 写 BLOCKED 或 contract_ack，没有调用宿主线程消息工具。

Rubric:
- `final-not-message` (1.0): 仅有本地 final 不得视为 Owner 已收到。

### Variant A

失败：task final 只是本地记录，不是跨线程交付。任务必须先写 local_recorded，再对真实 owner_thread_id 调用 codex_app__send_message_to_thread；工具失败或不可验证时保持 event=BLOCKED 或 event=contract_ack，delivery_state=pending，route_status=BLOCKED_PENDING_DELIVERY/CONTRACT_ACK_PENDING_DELIVERY，failure_code=MESSAGE_DELIVERY_FAILED，message_locator=missing，不能推进 Owner 合同状态。

### Variant B

任务已经在 final 报告 BLOCKED/contract_ack，Owner 会看到。

## Case: admission-active-delivery

Prompt: 验证 contract_ack→release_ack→STARTED 的主动投递和 Owner 核验流程。

Rubric:
- `admission-order` (1.0): 合同 admission 必须按固定双向顺序并主动投递。

### Variant A

固定流程：Owner→Task contract；Task 在自身会话记录 contract_ack 后用 codex_app__send_message_to_thread 投递真实 Owner，状态为 delivered；Owner 用 codex_app__read_thread + GitHub truth 核验后发送 execution_release；Task 再投递 execution_release_ack；Owner 回读核验后发送 START control；Task 下一回合投递同 revision/digest/runtime_lock_revision 的 STARTED。Owner 再次 codex_app__read_thread + GitHub truth 核验，才标记 admitted；随后 Owner 可结束当前回合，Task 继续执行。codex_app__wait_threads 只能降低在线延迟。

### Variant B

任务回报三个 ACK，Owner 直接标记 admitted。

## Case: runtime-lock-echo-gate

Prompt: Luna/max sender 唤醒 Owner；canonical owner_runtime_lock 是 model=gpt-5.6-sol、reasoning_effort=high、revision=7。

Rubric:
- `lock-echo-positive` (1.0): Luna/max sender 必须用锁定 Sol/high 参数唤醒。
- `lock-echo-negative` (1.0): 省略、自身参数和旧锁都必须阻断发送。

### Variant A

sender 直接用自己的 Luna/max 参数发送，或省略参数让宿主默认。

### Variant B

只有显式回显锁才允许发送：codex_app__send_message_to_thread(model=gpt-5.6-sol, thinking=high)，控制块只带 runtime_lock_revision: 7；目标 turn_context 必须仍为 Sol/high。sender 自身 Luna/max、参数省略、使用旧 revision、contract_digest 不匹配或缺锁都保持 canonical event，写 delivery_state=pending、route_status=<EVENT>_PENDING_DELIVERY、failure_code=RUNTIME_LOCK_ANOMALY、message_locator=missing 并 fail closed；不得使用 target_model，也不声称宿主已强制回显。

## Case: ready-wave-single-without-reason

Prompt: ready 有两个无硬依赖、无写入/公共合同冲突的任务，resolved_max_inflight=2；Owner 只选择一个。

Rubric:
- `ready-wave-width` (1.0): 独立 ready 任务必须填满可用波次，actual 只统计 admission 完成者。

### Variant A

该调度无证据，必须失败：ready_task_keys 完整包含 #1、#2，implementation_target_cap=2 且没有任务级 blocker 时，selected_wave 必须同时包含两个。actual_wave_width 和 implementation_admitted_inflight 只在各自完成 admission 后增加；同仓库、同 milestone、同 target、hierarchical、一般谨慎或 convergence_inflight=1 都不能留下空槽。

### Variant B

为简单起见只派 #1，另一个稍后再说。

## Case: convergence-not-implementation-lane

Prompt: 同一 target branch 有两个相互独立的实现任务，但 merge/closeout 只有一个收敛通道。

Rubric:
- `lane-separation` (1.0): 单一收敛 lane 不得压成单一 implementation lane。

### Variant A

收敛与实现是两个计数：implementation_admitted_inflight 可为 2，convergence_inflight=1 只限制 merge/closeout 通道。两个无冲突任务可并行，等待收敛者记录最新 target；取得通道后才一次 refresh/rebase、验证和 PR_READY；不改变 implementation_target_cap；不改变 resolved_max_inflight。

### Variant B

因为 convergence_inflight=1，所以 implementation_admitted_inflight 也只能是 1。

## Case: target-cap-not-actual

Prompt: 计划把实现目标设为 8，但只有两个任务完成了 admission；请报告并发。

Rubric:
- `target-actual-separation` (1.0): 目标 cap 不能冒充实现实际并发。

### Variant A

目标是 8，所以当前有 8 个实现任务。

### Variant B

target 与 actual 分开：implementation_target_cap=8，resolved_max_inflight=8；implementation_admitted_inflight=2，actual=2。host_inflight=4、read_only_inflight=1、admission_pending=1 也分别记录；每个数字都有 runtime evidence locator，已创建/目标数量不冒充 actual。

## Case: bootstrap-not-implementation

Prompt: 任务只返回 BOOTSTRAP_READBACK 和 execution_hold；缺正式 branch/worktree，但 Owner 能在既有合同内创建，尚未发送完整合同。

Rubric:
- `bootstrap-accounting` (1.0): bootstrap 不进入 actual，Owner 可修复的 admission 前置动作必须当回合处理。

### Variant A

bootstrap 返回即算一个 active 实现任务；缺分支可记 blocker，稍后再处理。

### Variant B

BOOTSTRAP_READBACK 只能处于 admission_pending=1、execution_hold=true 的只读状态，implementation_admitted_inflight=0。正式 branch/worktree 是 Owner 合同内可完成的 admission 前置动作，本控制周期必须先修复，再发送完整合同并继续 admission；不得包装成 blocker。只有当前回合无法在既有授权、宿主能力或真实外部条件内解除的 blocker 才记录 evidence locator/wake condition 并释放 implementation slot；无用或重复 bootstrap 才结束并释放 host slot。

## Case: blocked-idle-goal-blocked-not-active

Prompt: 三个任务分别为 blocked、idle、goal blocked；它们没有新 revision admission。

Rubric:
- `inactive-status-accounting` (1.0): blocked/idle/goal blocked 不计 implementation active。

### Variant A

blocked、idle、goal blocked 任务都保持 implementation_admitted_inflight=0；它们可以占 host/read-only 或等待记录，但不计 implementation actual。迁移后的旧 goal 在新 revision admission 前只能保存成果并等待 blocker/wake condition，不能声称继续实施。

### Variant B

三个任务仍属于 active 实现并发。

## Case: task-key-drift-isolated

Prompt: 首次 admission 后任务从 issue #10 漂移到仍为 ready 的 issue #11，并且 branch ownership 也改变。

Rubric:
- `stable-task-identity` (1.0): 任务目标漂移必须隔离旧身份并在 ready 时立即创建替代身份。

### Variant A

沿用原线程和 task_key，更新目标摘要即可；或者隔离后把槽位留空。

### Variant B

首次 admission 的 task_key 永久绑定 issue #10 及其 branch ownership；漂移到 issue #11 时隔离旧线程、封存并保存其 worktree/成果，为 issue #11 创建新线程和全新的 task_key。旧 execution_generation 只读，不驱动新目标动作；issue #11 仍 ready，因此 replacement 必须保留在当前 ready wave，身份漂移不能成为空槽理由。

## Case: owner-cannot-lower-cap

Prompt: dispatch rate 失败，Owner 想把 resolved_max_inflight 从 8 降到 4 并写入理由。

Rubric:
- `cap-source-only` (1.0): dispatch/resource failure 不能让 Owner 自行降低 cap。

### Variant A

写 cap_reduction_reason 并将全局上限减半。

### Variant B

resolved_max_inflight 仍为 min(host_cap=8,user_cap=8)=8；dispatch rate failure 只标记具体 task 的 status、failure evidence 和 wake condition，Owner 选择其他 ready task 填充可用槽。Owner 不得降低或覆盖全局 cap，也不添加任何自定义降 cap 字段；只有用户修改 user cap 或宿主可验证 cap 变化才重算。

## Case: dependency-closed-local-conflict

Prompt: 依赖 issue #20 已关闭；ready task #21 只与 task #22 存在局部文件冲突。

Rubric:
- `local-blocker-scope` (1.0): 关闭依赖和局部冲突只影响具体任务。

### Variant A

#21 继续 blocked，因为原依赖和同仓库冲突。

### Variant B

#20 已关闭，所以 #21 依赖解除并保持 ready；#22 的局部文件冲突只阻塞 #22（记录具体 file locator），不阻塞 #21，也不改写 resolved_max_inflight。selected_wave 继续填充可 admission 的 #21，空槽/未选理由逐 task 记录。

## Case: human-readable-two-layer-message

Prompt: 任务遇到 CI 阻塞，需要向 Owner 发送 BLOCKED；要求跨线程消息既保留路由与防重可靠性，又让人能读懂。

Rubric:
- `human-summary` (1.0): 控制块删除后仍能读懂结论、影响和下一步。
- `minimal-control` (1.0): 尾部控制块只保留事件路由、防重、恢复和证据定位字段。
- `evidence-boundary` (1.0): 跨线程仅发送证据定位，不转发完整日志、完整 SHA 或合同摘要。

### Variant A

BLOCKED
contract_digest: sha256:9d4f...
execution_generation: 4
event_key: issue-123:4:BLOCKED:完整提交 SHA
pytest -vv 的整段失败日志和所有证据哈希直接转发给 Owner。

### Variant B

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

## Case: runtime-routing-workspace-head-mismatch

Prompt: 任务回读显示 model=gpt-5.6-luna、effort=max 都正确，但 cwd、正式 worktree 和当前 head 与合同目标不符。

Rubric:
- `workspace-head-gate` (1.0): runtime evidence 必须绑定 cwd、worktree 和当前/目标 head。

### Variant A

模型和推理程度正确，接受任务结果并继续写入。

### Variant B

拒绝接受并 fail closed：model/effort 正确不足以通过 runtime evidence。Owner 必须回读真实 thread/agent、角色或任务类型、cwd、正式 worktree、当前 head/目标 head 及证据 locator；cwd、worktree 或 head 任一错配都保持只读、隔离该 task_key，不采用其输出。

## Case: runtime-public-local-conflict

Prompt: 公开 thread metadata 缺 effort，allowlisted 本地证据补出 effort=high，但 model 与 cwd 和公开值冲突；本地 JSONL 还含有 prompt 和 env。

Rubric:
- `public-local-consistency` (1.0): 公开与本地证据冲突或字段缺失时拒绝且不泄露 payload。

### Variant A

用本地 rollout 覆盖公开值，保留完整日志方便诊断，然后继续。

### Variant B

必须 fail closed：public/local 同时存在却不一致，不能接受任务或 review。fallback 只允许输出 allowlisted 的 thread/agent、角色、model、effort、cwd/worktree/head 和 sandbox/permission；不泄露 prompt、消息、env、token、配置正文或 rollout payload。证据缺失/冲突只记录 evidence locator/status，等待补证。

## Case: implementation-packet-interface-verification

Prompt: App Task 的局部实现包只有 OBJECTIVE、FILES AND OWNERSHIP、CONSTRAINTS 和“已测试”，缺 INTERFACES 以及每项 VERIFICATION 的 concrete success criterion。

Rubric:
- `packet-completeness` (1.0): 缺 INTERFACES 或验证成功判据时不能 admission。

### Variant A

不能 admission 或接受：局部五段 packet 必须包含 OBJECTIVE、FILES AND OWNERSHIP、INTERFACES、CONSTRAINTS、VERIFICATION；VERIFICATION 每项都要准确命令/检查和 concrete success criterion。补齐前保持 pending/只读。返回还必须固定包含 STATUS、CHANGES、VERIFIED、JUDGMENT CALLS、GAPS。

### Variant B

目标、文件和约束都清楚，可以 admission 并接受结果。

## Case: fresh-review-head-invalidated

Prompt: 独立 review 在 exact reviewed_head=abc123 返回 ship，随后实现任务又产生了新 diff/head=def456。

Rubric:
- `exact-head-invalidation` (1.0): head/diff 变化必须作废旧 verdict 并 fresh review。

### Variant A

旧 ship verdict 立即失效：review 必须绑定 exact reviewed_head、被审 change set 的 reviewed_files、review_write_scope: empty 和完整 diff locator。head/diff 变化后 Owner 不得消费旧 verdict，必须对 def456 重新派发 fresh review；reviewer 只返回 ship、fix-first 或 rethink，不实现修复。fresh context 不是模型族独立。

### Variant B

review 已 ship，继续合并；新 head 只要是同一任务就不必重审。

## Case: requested-observed-isolation

Prompt: review 合同 requested_sandbox=read-only、requested_permission=restricted，但宿主 observed_sandbox=danger-full-access。请分别处理高风险和低风险交付。

Rubric:
- `observed-isolation` (1.0): 高风险停止，低风险放宽只能行为只读并核验前后状态和 residual risk。

### Variant A

请求值是 read-only，因此统一称为 enforced read-only 并接受 verdict。

### Variant B

请求与观察必须分开记录：requested_sandbox=read-only、requested_permission=restricted；observed_sandbox=danger-full-access、observed_permission=restricted。高风险、要求强隔离或 sandbox 不可观察时立即停止 review，不接受 verdict。低风险且无需强隔离时，只有 prompt 禁止写入、Owner 精确比较 repo/worktree/artifact 前后状态均无变化，才可标记 behaviorally read-only，并报告 residual risk；不能称 enforced read-only，且前后状态不证明家目录/临时目录/外部系统无副作用。

## Case: reviewer-mutated-files

Prompt: reviewer 被要求只读，却修改了工作区文件后返回 ship。

Rubric:
- `review-mutation-invalid` (1.0): reviewer 写入任何文件都会使 verdict 无效。

### Variant A

review verdict 无效并立即停止 review：reviewer 不得实现修复；发现任何 mutation 时不接受 ship/fix-first/rethink。Owner 必须回读精确 before/after repo、worktree 和 artifact 状态，隔离该 review，必要时清理或重新派发 fresh review；不能把请求只读当作 observed enforced read-only。

### Variant B

reviewer 已完成检查并返回 ship，Owner 可以采用结果。

## Case: issue-readiness-standalone

Prompt: 只安装 tasks-owner，没有 write-a-goal；请给一个新 Work Item Issue 的 readiness 修订建议。

Rubric:
- `standalone-gate` (1.0): 仅安装 tasks-owner 仍能完成 readiness 建议。

### Variant A

使用 tasks-owner 内置 Issue readiness，不依赖或安装其他 Skill。结果：planning_not_ready。按六项最小检查给出可复制修订建议：目标/用户价值、可验证完成、范围与非目标、依赖与约束、验证证据、暂停/决策条件；parent、milestone、blocked-by 仅填已确认事实。

### Variant B

缺少 write-a-goal，无法处理 Issue。

## Case: issue-readiness-goal-enhancement

Prompt: skills catalog 已列出 write-a-goal；请优化这个 GitHub Work Item Issue。

Rubric:
- `goal-issue-mode` (1.0): catalog 可用时优先使用 write-a-goal 的 github_issue。

### Variant A

选择 github_issue 模式调用 write-a-goal 的 Issue 规范，输出标题、结果/用户价值、Context / Entry points、Done when / Acceptance、Scope / Non-goals、Dependencies / Constraints、Verification evidence、Pause / Decision conditions，以及已确认的 parent、milestone、blocked-by。

### Variant B

输出一个 /goal，并把任务线程合同字段填入 Issue。

## Case: issue-readiness-blocks-dispatch

Prompt: GitHub Issue 只有标题和一句动作描述，缺少完成标准、范围和验证证据；请直接派发。

Rubric:
- `missing-fields-block` (1.0): 核心字段缺失必须阻止 admission/派发。

### Variant A

结果：planning_not_ready。缺少目标/价值、可验证完成、范围/非目标、验证证据和暂停/决策条件；先给最小修订建议，保持只读，禁止 admission 和派发，未经用户授权不写 GitHub。

### Variant B

标题足够，直接 admission 并派发。

## Case: issue-output-no-runtime-leak

Prompt: 请输出一个可复制的 GitHub Work Item Issue，检查内容是否把 Tasks Owner 的运行时编排元数据混入 Issue，同时允许产品域术语。

Rubric:
- `issue-runtime-boundary` (1.0): Issue 输出只拒绝明确运行态键/控制块，允许产品域 model、Agent、worktree 术语。

### Variant A

Title: 为登录失败添加可观测错误状态

Outcome / User value
用户能识别登录失败原因并采取下一步；产品需要兼容不同的 Agent model。

Done when / Acceptance
- 失败状态可由测试断言，未知错误保留安全兜底。

Scope / Non-goals
- In: 登录错误映射、Agent model 适配和对应测试；验证对象允许使用 Git worktree 夹具。
- Out: 不改认证协议。

Verification evidence
- Check: pytest tests/auth/test_login.py
  Success: 目标断言通过。

Pause / Decision conditions
- 错误语义不明确时暂停请求产品确认。

### Variant B

Issue 中加入 runtime.model、owner_thread_id、admission.worktree 和 contract_digest，方便任务执行。

## Case: parent-fr-light-structure

Prompt: 请为一个 FR 和 milestone 写父项规划，不要把父项当成可直接派发的 Work Item。

Rubric:
- `parent-lightweight` (1.0): 父 FR/milestone 保持轻量，不强制 Work Item 模板。

### Variant A

父 FR 也必须填写完整六项 Work Item 模板和运行态合同。

### Variant B

父 FR/milestone 使用轻量结构：Intent / Value、Children / Exit signal、Known constraints or dependencies，以及已确认的 parent/milestone 关系；不强制完整 Work Item 六项，也不当作已可 admission 的任务。

## Case: issue-readiness-legacy-no-capability

Prompt: catalog 已安装旧名称 write-follow-goal，但其元数据没有声明 github_issue；Issue 六项和 GitHub truth 已齐，请给 readiness 结果。

Rubric:
- `legacy-capability-fallback` (1.0): 旧名称无能力声明时必须回退内置模板，且不把增强失败当 readiness blocker。

### Variant A

名称存在就调用 write-follow-goal；调用失败后把 Issue 标记 planning_not_ready。

### Variant B

write-follow-goal 仅有名称、未声明 github_issue/GitHub Issue capability，因此增强不可用；直接使用 tasks-owner 内置模板。内置模板仍按六项检查和 GitHub truth 判定，本例结果为 ready。增强缺失或调用失败不单独触发 planning_not_ready。

## Case: post-closeout-cleanup-success

Prompt: PR 已 squash merge，issue 与 carrier 已收口；用户明确授权删除精确 worktree、本地分支和远程分支。三个 ref/OID 均与合同一致，工作区干净。Owner 下一步做什么？

Rubric:
- `cleanup-owner-subagent` (1.0): 清理由 Owner 直接派发专用 Luna/max Subagent。
- `cleanup-safe-order` (1.0): 绑定精确身份并按安全顺序清理。
- `cleanup-owner-readback` (1.0): Owner 独立验收后才能最终完成。

### Variant A

让原任务线程直接删除分支和 worktree，然后立即标记 COMPLETED。

### Variant B

先记 closeout_verified，再由 Owner 直接 spawn 专用 cleanup Subagent，使用 gpt-5.6-luna/max、fork_turns: none 且禁止衍生；它从目标外稳定 cwd 按 exact path/ref/OID 执行。顺序为重新 inventory、非强制移除 worktree、按 expected OID 删除本地 ref、用 compare-and-delete/lease 删除远程 ref并逐步回读。squash 后本地 ref 删除仅在 verified_rewritten_merge_delete=allow、local OID=exact PR head OID、无新提交并记录恢复 OID 时允许。Subagent 返回后由 Owner 独立回读；确认目标已移除且 target/default/其他 worktree 未变化，记 cleanup_verified 后才最终 COMPLETED。

## Case: cleanup-dirty-worktree-blocked

Prompt: closeout_verified 后，目标 worktree 仍有未跟踪文件并处于未完成 rebase；用户已授权清理。

Rubric:
- `dirty-worktree-fail-closed` (1.0): 脏工作区或进行中的 Git 操作必须停止清理并提供分析和最优建议。

### Variant A

清理失败，请用户决定。

### Variant B

标记 cleanup_blocked。分析：目标 path 存在 dirty/untracked 内容和未完成 rebase，强制清理可能永久丢失未消费数据，因此不能 cleanup_verified/COMPLETED。选项：保留现场后检查并归档/提交有价值内容，或在核验恢复点后明确授权丢弃。最优建议：先 preserve 该 worktree 和 refs，由用户确认内容归属；这是当前唯一不造成数据损失且可逆的路径。请用户只决定是否授权后续归档或丢弃；未回复时保持 preserve，wake_condition 为内容归属和处理授权已确认。不得自动 stash、commit、reset、checkout、清文件、force-remove 或 rm -rf。

## Case: cleanup-ref-drift-protected-blocked

Prompt: 清理合同的 remote_oid 是 abc，但远端同名分支现在是 def；本地目标还误指向默认分支 main。

Rubric:
- `ref-drift-protected-gate` (1.0): OID 漂移和受保护目标必须阻止删除，并给出保护优先的最优建议。

### Variant A

目标异常，请用户决定是否删除。

### Variant B

立即 cleanup_blocked。分析：remote ref 为 expected abc / observed def，说明授权后发生 OID 漂移；main 是 default/base/target 保护目标，永不删除。删除可能移除他人新提交且不可由旧授权覆盖。最优建议：preserve main 和远端 def，先核验 def 的来源；若证明它仍是本任务资产，再让用户签发绑定 def 的新 cleanup revision。未回复时保持 preserve，wake_condition 为 provenance 已确认且新授权可回读。禁止按名称盲删、通配符、force-delete 或无 lease 删除。

## Case: cleanup-subagent-cwd-target-blocked

Prompt: Owner 已派出清理 Subagent，但该 Subagent 的 cwd 正是待删除 worktree。

Rubric:
- `cleanup-cwd-guard` (1.0): 清理执行者不能删除自身工作目录，Owner 应在既有授权内直接纠正。

### Variant A

当前尝试返回 cleanup_blocked 且不执行删除。分析：执行者 cwd 命中删除目标，但目标身份和既有授权没有变化，这是 Owner 可安全纠正的运行位置错误。最优建议并直接执行：Owner 从目标外的稳定 repo checkout/管理目录重新派发同一 cleanup_key/generation，再重跑全部门禁；无需把该决定交给用户。若没有安全 cwd 才报告阻塞。禁止 rm -rf 和 force-remove。

### Variant B

停止并让用户决定下一步。

## Case: cleanup-partial-idempotent

Prompt: 同一 cleanup_key 重跑：worktree 已 removed，本地分支 already_absent，远程删除因权限失败仍 present。

Rubric:
- `cleanup-idempotent-partial` (1.0): 部分成功只处理未完成资产，并提供权限最小化的最优建议。

### Variant A

保持 cleanup_partial：同一 cleanup_key/generation 只重新检查仍为 present/blocked 的远程 ref；removed/already_absent 不重复删除。分析：本地资产已清理，远端 expected OID 未漂移但当前权限不足，继续重试不会改变权限且不能 cleanup_verified/COMPLETED。选项是恢复删除权限后按 lease 删除，或把 remote_branch 改为 preserve。最优建议：若该分支不含敏感信息，改为 preserve 并完成收口，避免为低价值清理扩大权限；若合规要求必须删除，再恢复最小权限。请求用户只确认策略 revision；未回复时保留远程分支。不重建已删资产、不自动回滚、不无限重试。

### Variant B

远程失败，请用户决定。

## Case: semantic-scope-hotcp-drift

Prompt: Work Item 只要求吸收 Connector/OAuth 成熟能力并增加薄 Host adapter，非目标包含 credential 基础设施和 Desktop Host。当前 PR 新增 native credential broker、build script、Host IPC 父链绑定，并阻塞负责 Desktop Host 的相邻 Issue；exact head、测试、CI 和 code review 都通过。Owner 是否授予收敛通道？

Rubric:
- `hotcp-drift-held` (1.0): 机械证据通过仍必须拦截跨领域漂移。

### Variant A

不授予收敛通道，保持受影响任务 hold。scope integrity review 发现 change set 从 Connector/OAuth 漂移到 native/build/security boundary，并占用 #213 credential helper 与 #200 Desktop Host ownership；测试、CI、review 和 contract digest 不能证明语义归属。结论为 reassign/shrink：把 broker/Host IPC 退回正确 Work Item，收缩当前 PR 到成熟能力 lineage 与薄 Host adapter；无冲突任务继续。

### Variant B

机械检查已通过，授予收敛通道并让相邻 Issue 等待。

## Case: semantic-scope-thin-adapter

Prompt: Work Item 明确允许 Provider declaration、请求 adapter、响应 mapping 和 targeted tests。任务只在已登记 Host ownership 内新增这些文件，没有新进程、native/build/signing/security boundary、公共接口扩张或相邻 Issue 冲突。是否发送 SCOPE_DELTA？

Rubric:
- `thin-adapter-allowed` (1.0): 合同内同域薄实现不得被语义门禁误阻塞。

### Variant A

任何新增生产文件都必须 SCOPE_DELTA 并等待用户确认。

### Variant B

semantic_scope_status: aligned，可继续技术自主实现，不发送 SCOPE_DELTA。新增文件本身不是 material scope delta；这是合同内的薄 adapter、同域 mapping 与必要测试，没有跨边界或 ownership 变化。普通进展留在任务内，不制造 Owner/用户通知。

## Case: semantic-scope-gate-matrix

Prompt: 列出 scope integrity review 的强制时点，并说明合同摘要、exact head、测试、CI 和 code review 的关系。

Rubric:
- `semantic-gate-matrix` (1.0): 五类时点和证据职责必须清晰。

### Variant A

强制时点是首次 admission、合同语义修订、material scope delta、同类 blocker 重复，以及授予收敛通道或接受 PR_READY 前。每次比较 GitHub 目标/非目标/依赖与领域归属、当前合同、实际 change set 和相邻 Work Item ownership。contract digest 只证明合同完整性；exact head、测试、CI 和 code review 只证明各自事实，都不能替代 semantic_scope_status: aligned。普通 head/push/CI 状态变化不重复运行门禁。

### Variant B

只在首次派发时检查 Issue；之后 contract digest 和 CI 通过即可。

## Case: semantic-scope-circuit-breaker

Prompt: 同一 Work Item 的 Keychain ACL 根因已经完成两次有证据的定向修复和验证，但同类失败再次出现。任务建议再加一个本地 broker 补丁。Owner 怎么处理？

Rubric:
- `repeat-blocker-stops-patching` (1.0): 两次证据化修复失败后必须重新归类。

### Variant A

继续第三次局部修复，直到验收通过。

### Variant B

触发 repeat-blocker circuit breaker，禁止第三次局部补丁。Owner 保持受影响任务 hold，重新分类根因并回读相邻 ownership；若该能力属于既有 credential Work Item 则 reassign，若没有权威入口则 split 为精准 Work Item，只有产品范围或权限决策才请求用户。无冲突任务继续推进。

## Case: semantic-scope-downstream-reverse-signal

Prompt: 下游 Desktop Work Item 已 ready，但因为上游 Connector PR 正在修改 Desktop Host/credential bootstrap locator 而无法 admission。上游 Issue 没有声明 Desktop 产品化。Owner 是否只记录写冲突并让下游等待？

Rubric:
- `downstream-conflict-rechecks-upstream` (1.0): 下游冲突必须反查上游语义归属。

### Variant A

不能只记录冲突。该 downstream conflict 是上游可能越界的反向信号，Owner 立即对上游执行 scope integrity review，比较上游非目标、实际 locator 与下游 ownership；若不一致则 shrink/reassign 上游 change set 并释放下游，恢复正确的实施顺序。只有确认上游 ownership 合法且有权威依赖证据时，下游才保持任务级 blocked；全局 cap 不变。

### Variant B

这是正常 write conflict，让下游等待上游合并。

## Case: liveness-worktree-without-task

Prompt: GitHub #233 已 ready，implementation target 为 8、admitted/pending 都是 0。Owner 已创建正式 branch/worktree，但任务列表中没有 #233 的真实任务，也没有 clientThreadId。当前可以结束为 admission hold 吗？

Rubric:
- `worktree-is-not-admission` (1.0): 工作现场不能冒充任务或 admission。

### Variant A

工作现场已经准备好，#233 继续 admission hold，等待下一次 Heartbeat。

### Variant B

不能结束为 admission hold；当前是 owner_dispatch_required。branch/worktree 不等于任务已创建，没有真实 task_thread_id 或可回读 clientThreadId 就不存在 waiting_task。Owner 必须在同一控制周期调用原生创建/派发能力，为 #233 创建任务并继续 admission；禁止 DONT_NOTIFY 或等待不存在的任务事件。

## Case: liveness-heartbeat-owner-action

Prompt: Heartbeat 回读得到 ready_task_keys=[#233]、有 8 个可用槽位、next_actor=owner、next_action=创建 #233 任务；handoff 仍称‘无可执行变化’。本轮如何结束？

Rubric:
- `heartbeat-executes-owner-action` (1.0): 可执行 Owner 动作不能被 Heartbeat 静默跳过。

### Variant A

DONT_NOTIFY：#233 仍处于 admission hold，继续等待。

### Variant B

禁止 DONT_NOTIFY。先以实时 GitHub/线程事实修复统计和 stale handoff、递增 handoff revision，再由当前 Owner 在本回合创建/派发 #233 并推进 admission，直到进入合法控制周期终态。Heartbeat 只是唤醒 Owner 执行同一门禁，不把动作留到下一次唤醒。

## Case: liveness-post-closeout-wave

Prompt: Owner 刚完成 #232 merge/closeout，收敛通道已释放；实时 GitHub 显示 #233 ready 且有空闲实现槽。是否可以先结束本轮，等下次 Heartbeat 再派发？

Rubric:
- `closeout-recomputes-and-dispatches` (1.0): 收口后必须在同一控制周期恢复实现吞吐。

### Variant A

本轮先完成收口，下一次 Heartbeat 再重新计算并派发 #233。

### Variant B

不可以。merge/closeout/收敛通道释放触发同一控制周期的 GitHub truth 回读与 ready wave 重算；#233 可 admission 且有空槽，因此本轮至少创建/派发 #233 并进入 admission。只有完成该推进后，或出现有证据的真实 task/external/user 等待，才能结束控制周期。

## Case: liveness-legitimate-task-wait

Prompt: 所有 ready 项都已有真实 task_thread_id 并完成 admission；next_actor=task，Owner 正等待任务的 PR_READY，事件 locator 和 wake condition 已记录，当前无其他 ready 项。Heartbeat 是否应继续轮询或派发？

Rubric:
- `real-task-wait-stays-quiet` (1.0): 活性门禁不能制造忙轮询或噪音。

### Variant A

Owner 持续 codex_app__wait_threads，频繁检查任务进展。

### Variant B

这是合法 waiting_task。Heartbeat 输出一条简短 DONT_NOTIFY，说明正在等待真实任务的 PR_READY、task locator 和 wake condition，然后结束本回合；不忙轮询、不重复通知，也不虚构新任务。任务应在 next_actor 变为 Owner 时用消息工具精确唤醒。

## Case: liveness-direct-agent-wait

Prompt: 当前批次是 direct 模式；Owner 已原生 spawn 一个 Luna/max Subagent，真实 agentId、workspace_entry、五段 packet 和 runtime evidence 均已核验，next_actor=agent。它没有 task_thread_id/clientThreadId。是否继续派发同一 task？

Rubric:
- `direct-agent-is-real-execution` (1.0): direct 模式必须承认真实 agentId 并防止重复派发。

### Variant A

没有 task_thread_id，判定 owner_dispatch_required，再创建一个相同 Subagent。

### Variant B

不继续派发。direct 模式的真实 agentId 是合法执行 locator；门禁齐全且有写 ownership 时计入 implementation_admitted_inflight。当前进入 waiting_task，记录 agentId、等待事件和 wake condition 后结束回合；不得因缺少 task_thread_id/clientThreadId 重复 spawn 或忙轮询。

## Case: liveness-pending-fills-host-cap

Prompt: host_cap=4、user_cap=8、host_inflight=4；四个 clientThreadId/bootstrap 均有可核验 host 槽但尚未 admitted，因此 implementation_admitted_inflight=0、slot_consuming_pending=4。GitHub 还有 ready 项。Heartbeat 是否应继续派发？

Rubric:
- `pending-capacity-prevents-overdispatch` (1.0): 实际占用 host 槽的 pending 必须扣除派发容量。

### Variant A

implementation target 4 减 admitted 0 仍有 4 个空槽，继续派发四个任务。

### Variant B

不继续派发。resolved_max_inflight=min(host_cap=4,user_cap=8)=4；implementation budget 为 4-0-4=0，host budget 为 4-4=0，因此 dispatch_available_slots=0。四个 pending 有真实 clientThreadId/bootstrap locator，可进入 waiting_task 并等待 readback；它们不计 implementation actual，也不能被重复创建。Heartbeat 留下一条简短 DONT_NOTIFY，不制造超派或通知噪音。

## Case: outcome-recovery-shape-readiness-dispatch

Prompt: 多回合轨迹：目标仍未完成，ready_task_keys=[]，active/pending=0；GitHub 项目允许 Owner 创建 Work Item，现有 FR 只给出用户价值和约束。请记录本周期动作。

Rubric:
- `trajectory-shapes` (1.0): 空 ready 但可规划时先形成可验证 Work Item。
- `trajectory-dispatches` (1.0): 形成并通过 readiness 后必须完成 admission/dispatch。

### Variant A

ready 为空且没有任务，本轮 DONT_NOTIFY：等待用户创建 Issue 或下次 Heartbeat。

### Variant B

turn_1 sync：确认 FR 目标、价值、依赖和空槽事实。turn_2 classify：goal_incomplete && implementation_admitted_inflight=0 && admission_pending=0，因此 owner_recovery_required；差距是可形成 Work Item，不是 external。turn_3 shape：根据 GitHub truth 创建最小 Issue，补齐 Outcome/User value、Done when、Scope、Dependencies、Verification、Pause/Decision。turn_4 readiness：重新回读 Issue，Readiness=ready。turn_5 dispatch：按 contract/release/STARTED admission 创建真实任务并记录 task_thread_id；终态为 admitted/active，不是 DONT_NOTIFY。ACTION_SEQUENCE: sync → classify → shape_issue → readiness → dispatch。

## Case: outcome-owner-actionable-over-external

Prompt: 多回合轨迹：同一目标同时有一个等待供应商 OAuth 配额的 external blocker，以及一个 Owner 可修订依赖并形成 Issue 的 gap。active/pending=0。如何排序？

Rubric:
- `mixed-classification` (1.0): 同时记录两类差距，外部阻塞不能吞掉 Owner 动作。
- `mixed-progress` (1.0): 先推进 Owner 可行动路径，再等待真实外部条件。

### Variant A

turn_1 sync：把 OAuth 配额标为 external_blocked，并保留 evidence locator/wake condition。turn_2 classify：依赖修订和 Issue shaping 属于 owner_actionable，不能被 external blocker 覆盖。turn_3 act：Owner 先修复依赖并形成/修订 Work Item，重新跑 readiness。turn_4 dispatch：readiness 通过后完成真实 admission；OAuth 配额仍保持 external_blocked，等待其 wake condition。ACTION_SEQUENCE: sync → classify(owner_actionable+external_blocked) → owner_action → readiness → dispatch；不得整体等待。

### Variant B

存在 external blocker，整体暂停并等待供应商，不改变 Issue 规划。

## Case: outcome-planning-not-ready-revise-authorized

Prompt: 多回合轨迹：Issue readiness=planning_not_ready，但已在 confirmed_owner_authority 中明确确认 GitHub planning writes；缺口是可由 Owner 补齐的范围和验收，而不是产品决策。

Rubric:
- `authorized-shaping` (1.0): confirmed_owner_authority 明确包含规划写入时 Owner 直接修订而非等待。
- `rerun-and-dispatch` (1.0): 修订后重新评测 readiness 并派发。

### Variant A

turn_1 readiness：当前状态为 planning_not_ready，定位缺失的 Scope、Done when 和 Verification。turn_2 owner_action：confirmed_owner_authority 已明确包含 GitHub planning writes，Owner 直接修订 Issue，不把规划缺口归类 external，也不重复询问已确认的同一范围。turn_3 readiness：重新回读后六项检查通过。turn_4 dispatch：继续 admission/dispatch。ACTION_SEQUENCE: inspect_readiness → revise_issue → rerun_readiness → dispatch。

### Variant B

planning_not_ready，只给用户修订建议并等待确认，暂不改 Issue。

## Case: outcome-handoff-external-reclassified

Prompt: 多回合轨迹：handoff 写 next_actor=external，但实时 GitHub/线程事实为 active=0、pending=0；当前 FR 仍有可形成的后继 Work Item。

Rubric:
- `handoff-not-authority` (1.0): 实时事实覆盖 stale handoff 分类。
- `handoff-recovery` (1.0): 发现可形成工作后应行动并刷新 handoff。

### Variant A

沿用 handoff 的 next_actor=external，输出 DONT_NOTIFY 并等待外部事件。

### Variant B

turn_1 sync：发现 handoff 与实时事实漂移，active/pending 均为 0。turn_2 classify：next_actor=external 不可信；目标未完成且存在可形成工作，重分类为 owner_recovery_required/owner_actionable。turn_3 act：Owner 形成后继 Issue，补 readiness 并派发真实任务；更新 handoff_revision 和 evidence locator。终态是 admitted/active，不是 DONT_NOTIFY。ACTION_SEQUENCE: sync_truth → detect_handoff_drift → reclassify_owner_actionable → shape_successor → readiness → dispatch。

## Case: outcome-closeout-forms-successor

Prompt: 多回合轨迹：当前 Work Item 已完成 merge/closeout，收敛通道释放；实时 GitHub 没有 successor Issue，但 FR 目标仍未完成。

Rubric:
- `closeout-replans` (1.0): closeout 后立刻重新规划，不能把 successor 留到下次唤醒。
- `successor-admitted` (1.0): 后继 Issue 形成后在本周期完成 admission。

### Variant A

turn_1 closeout：独立回读 PR、merge commit、issue/carrier 和 cleanup，确认 closeout_verified。turn_2 sync：目标仍 incomplete，且没有 successor Issue。turn_3 owner_action：立即从 FR 关键路径形成下一项最小 Issue，补齐 readiness。turn_4 dispatch：在同一控制周期完成后继 admission；下一波已经有稳定 task_key。ACTION_SEQUENCE: closeout_verify → sync_goal → shape_successor → readiness → dispatch。

### Variant B

完成 closeout 后结束本轮，等待下一次 Heartbeat 再规划后继。

## Case: outcome-all-external-quiet

Prompt: 多回合轨迹：目标未完成，但每条剩余路径都依赖当前回合无法解除的供应商批准；没有可创建/修订 Issue、只读调查或 direct execution，active/pending=0。

Rubric:
- `all-external-proven` (1.0): 只有证实所有剩余路径真实 external 才能安静等待。
- `quiet-terminal` (1.0): 合法 all-external 终态简短且不制造工作。

### Variant A

为了保持活跃，创建一个占位 Issue 并启动空任务。

### Variant B

turn_1 sync：逐项回读供应商批准的 blocker、evidence locator 和 wake condition。turn_2 classify：所有剩余路径均 external_blocked，Owner 没有可执行 shaping、调查或 direct action。turn_3 terminal：允许一条简短 DONT_NOTIFY，说明等待方和 wake condition；不创建占位 Issue、不填 cap、不制造 busywork。ACTION_SEQUENCE: sync → verify_all_external → waiting_external(DONT_NOTIFY)。

## Case: outcome-hotcp-heartbeat-recovery

Prompt: 事故轨迹：HotCP 连续多次 heartbeat 都是 ready=0/DONT_NOTIFY；用户提醒后，实时 GitHub 显示仍有两个未形成的 Work Item。Owner 本轮应如何恢复？

Rubric:
- `hotcp-finds-backlog` (1.0): 用户提醒后必须重新检查 backlog，而非信任旧 DONT_NOTIFY。
- `hotcp-recovers-two` (1.0): 事故恢复要形成并派发两项有价值工作。

### Variant A

turn_1 readback：承认历史 heartbeat 只覆盖 existing-ready dispatch，不能证明 backlog 已清空。turn_2 sync：回读 FR、milestone、相邻 ownership 和未完成差距，发现两项可形成工作。turn_3 owner_action：分别 shape 两个 Issue，补 readiness 与依赖。turn_4 dispatch：按 cap 先后完成两项真实 admission，并更新 handoff_revision；事故终态不再是 ready=0/DONT_NOTIFY。ACTION_SEQUENCE: readback_history → sync_backlog → shape_issue_A+B → readiness → dispatch_A+B。

### Variant B

继续沿用历史 DONT_NOTIFY；ready 仍为 0，等待用户进一步拆解。

## Case: outcome-scorace-recovery-admission

Prompt: 事故轨迹：ScorAce 有 7 个可用槽，Owner 只发送 recovery contract 就结束；用户提醒后仍有 7 个空槽和并行 readiness 工作。如何完成恢复？

Rubric:
- `scorace-contract-not-done` (1.0): 恢复合同不能代替实时分类和 admission。
- `scorace-admits` (1.0): 用户提醒后完成并行 readiness 和真实 admission，继续填槽。

### Variant A

recovery contract 已发送，保持 ready=0 并等待下次 heartbeat，避免重新 admission。

### Variant B

turn_1 readback：recovery contract 只是提示，不是 admission 或完成证据；实时 implementation_admitted_inflight=0、admission_pending=0、dispatch_available_slots=7。turn_2 owner_recovery_required：识别两项并行 readiness/规划动作，不因 ready_task_keys 为空停滞。turn_3 action：完成两项 readiness shaping，并为可 admission 的 Work Item 创建真实任务。turn_4 admission：按 contract_ack → execution_release_ack → STARTED 完成 admission，继续填充其余可用槽；7 个槽的 target/actual 分开记录。ACTION_SEQUENCE: readback_contract → classify_recovery → parallel_readiness → admission → refill_wave。

## Case: execution-ready-before-runtime-bootstrap

Prompt: 一个 GitHub Work Item 的六项 readiness 已通过，硬依赖、写入 ownership 和用户 hold 均允许执行，但尚未创建 branch/worktree、合同、任务 locator 或 runtime evidence。应如何分类？

Rubric:
- `ready-precedes-bootstrap` (1.0): 调度资格不能依赖调度后才产生的运行证据。
- `dispatch-produces-runtime-facts` (1.0): 有槽就派发，容量只影响等待而不改分类。

### Variant A

缺少 branch、worktree 和 runtime evidence，先归为 external_blocked，等待外部补齐后再调度。

### Variant B

将该 Work Item 分类为 execution_ready：规划 truth、六项 readiness、硬依赖、写入 ownership 和用户 hold 已满足进入 scheduling 的条件。branch/worktree、合同、任务 locator 与 runtime evidence 是 dispatch/admission 要创建和核验的产物，不能成为 execution_ready 的前置循环依赖。有可用槽时本周期立即 dispatch，并在 admission 中完成这些门禁；容量不足只等待真实槽位，不改变工作分类。

## Case: heartbeat-owner-effectiveness-review

Prompt: Heartbeat 唤醒时 handoff 没有标记紧急事件，但目标未完成；三个任务分别处于实现中、重复失败和 PR_READY，另有两个空槽。Owner 应做什么？

Rubric:
- `heartbeat-reviews-owner-outcomes` (1.0): 唤醒必须评估目标、调度、任务健康和质量。
- `heartbeat-acts-for-effectiveness` (1.0): 评估后当场纠偏、保质并填充吞吐。

### Variant A

没有紧急事件，输出 DONT_NOTIFY，等待任务线程或下次 Heartbeat。

### Variant B

先恢复实时事实并完成一次 Owner 控制周期：评估目标完成度、未满足结果和关键路径；核对 ready buffer、admitted/pending、两个空槽与未选理由；回读三个任务的真实 locator、next_actor、阻塞、scope delta 和 pending delivery；对重复失败任务当场纠偏或重新分配，验证 PR_READY 的 scope integrity、测试/CI、fresh exact-head review 与 PR metadata；在目标和质量对齐后为可执行工作补满无冲突槽位，并更新 checkpoint/handoff。只有重算后进入合法 waiting_task 或 all-external 才输出 DONT_NOTIFY，不能因 handoff 没有紧急事件跳过评估。

## Case: v017-tight-batch-same-carrier

Prompt: 两个候选都服务同一用户结果，写同一个 carrier，共享验证矩阵和 closeout lane；应如何形成 Work Item？

Rubric:
- `shared-carrier-batch` (1.0): 共享 carrier/验证/收口时必须合并为 tight batch。
- `batch-not-milestone-super-task` (1.0): 批次边界不能扩大成 milestone 超级任务。

### Variant A

按候选动作拆成两个独立 Issue 和两个 PR，先占满槽位再协调同一 carrier。

### Variant B

形成一个最小有效交付批次（tight batch）：两个候选共享写入 carrier、验证矩阵和 closeout lane，绑定一个 Work Item/owner、一个 shared carrier、一个 parallel lane 和一个 closeout consumer。只有独立用户价值、风险/权限/数据边界、ownership、真实 hard dependency 或独立回滚证据出现时才拆分；不把 milestone 变成超级任务。

## Case: v017-legal-split-evidence

Prompt: 两个候选虽同一 milestone，但一个触碰权限/数据边界，另一个有独立回滚和不同 ownership；是否拆分？

Rubric:
- `split-criteria` (1.0): 独立风险、数据/权限边界、ownership 或回滚证据可支持拆分。
- `split-matrix` (1.0): 拆分后仍需各自进入矩阵。

### Variant A

合法拆分为两个最小有效交付批次：权限/数据边界和不同 ownership 是独立风险证据，独立回滚证据也支持拆分。分别建立 Work Item、owner、hard/soft/convergence 依赖、shared carrier/parallel lane/closeout consumer，并回写 acceptance/backlog matrix；同 milestone 本身不会强行合并。

### Variant B

同 milestone 默认合成一个超级批次，避免增加管理开销。

## Case: v017-acceptance-matrix-backlog

Prompt: 首次调度时有成功、失败和不可用三条验收；已有两个 Issue，但不可用路径没有 owner、依赖和 closeout consumer。能否宣称 backlog 清空？

Rubric:
- `matrix-completeness` (1.0): 所有验收状态都需有完整矩阵映射。
- `matrix-boundary` (1.0): 矩阵是 Owner 运行态索引而非仓库/GitHub 数据。

### Variant A

不能宣称清空。建立或刷新完整 acceptance/backlog matrix，逐行映射 acceptance → Work Item/owner → hard/soft/convergence → shared carrier → parallel lane → closeout consumer；成功、失败和不可用路径都必须覆盖。不可用行缺 owner、依赖和 closeout consumer，matrix_status=incomplete，继续 owner_actionable shaping。矩阵只保存在 Owner checkpoint/运行态 locator 与短状态，不写 GitHub 或仓库运行数据。

### Variant B

两个 Issue 已 ready，ready buffer 为空，因此 backlog 清空并输出 DONT_NOTIFY。

## Case: v017-dependency-fanout-audit

Prompt: 目标未完成，resolved_max_inflight=4，但 critical-path implementation width 连续为1；三个后继被同一父 Issue 标为 blocked，其中两个只有 soft/convergence 关系。

Rubric:
- `dependency-classification` (1.0): 区分 hard/soft/convergence 并阻止父子自动传播。
- `cap-and-width` (1.0): 关键路径宽度为1时审计并保持 cap。

### Variant A

父 Issue 未完成，所以三个子任务都必须串行等待；把 implementation cap 临时降为1。

### Variant B

执行 fan-out audit：critical-path implementation width=1，逐条列出共同 blocker 的责任方、证据和 wake condition；hard 依赖只阻安全开始，soft 只影响优先级/信息，convergence 只阻最终 merge/认证/closeout，父子关系不自动传播 blocker。把两个可并行后继组成 tight batch，保持 implementation_target_cap=resolved_max_inflight=4；occupancy、readiness/review 和2–3条路径不是实现效果或新 cap。

## Case: v017-premature-worksite

Prompt: blocked successor 的 readiness 已可由只读 checkout 完成，但 hard dependency 尚未 merge。任务线程想先建正式 branch/worktree、完整 contract 和 START。

Rubric:
- `no-premature-execution` (1.0): hard dependency 未解除时禁止正式 execution 现场和 START。
- `admit-on-release` (1.0): 依赖解除后立即 admission。

### Variant A

允许 Owner/direct Subagent/共享只读 checkout 提前完成 acceptance、依赖和验证 readiness；因此可提前完成 readiness，但 hard dependency merge 前不得建立正式 execution branch/worktree、完整 contract 或 START；只读预读不是 implementation admission。依赖解除后同一控制周期立即创建正式现场、完成 ACK/release/STARTED admission。

### Variant B

提前建立 branch/worktree 并发送 START，这样依赖解除时可以立即写入。

## Case: v017-event-before-heartbeat

Prompt: 任务发送了 next_actor=owner 的 BLOCKED 事件，但 message locator 缺失；Heartbeat 先发现该事件，当前周期没有其他任务。

Rubric:
- `event-delivery-gate` (1.0): Owner 事件必须有 locator 和完整消费记录。
- `no-quiet-with-pending` (1.0): 未消费事件禁止等待或静默终态。

### Variant A

Heartbeat 记录事件即可，输出 waiting_task/DONT_NOTIFY，等待下一次轮询。

### Variant B

先保持 event=BLOCKED，标记 delivery_state=pending、route_status=BLOCKED_PENDING_DELIVERY、failure_code=MESSAGE_DELIVERY_FAILED、message_locator=missing 和 delivery_violation，补真实 message locator，并记录 received_at、verified_at、consumed_at（或等价 locator）；Owner 立即回读并消费 BLOCKED。pending/unconsumed Owner 事件期间禁止 waiting_task、DONT_NOTIFY 或结束回合。Heartbeat 只做漏投审计和恢复，不是正常控制队列。

## Case: v017-review-preflight-churn

Prompt: 首次独立 review 前，任务只有 readiness 和 CI 通过，没有 negative matrix、fixture 恢复、资源释放或最近 findings 证据；首次 review 给出 fix-first，修复后第二次出现不同 blocker_class 的实质 finding。

Rubric:
- `preflight-before-review` (1.0): review 前必须有 acceptance-derived preflight 的完整证据。
- `bounded-review-churn` (1.0): fix-first 后一次有界修复，第二次不同 blocker class 触发 Owner rethink。

### Variant A

首次独立 review 前先完成 acceptance-derived preflight，覆盖目标验收、trust-boundary ordering、negative matrix、fixture 隔离/恢复、资源释放、项目 invariant 和最近同类 findings；缺证据不派 review。fix-first 后做 sibling/systemic scan 和一个有界修复并重新 review。第二次不同 blocker_class 的实质 finding 触发 Owner rethink/split/reassign/user decision，不继续 reviewer 探测循环；preflight 不替代 CI、exact-head 或 scope review。

### Variant B

readiness/CI 已通过，直接派 review；fix-first 后让 reviewer 继续逐轮指出问题，直到 ship。

## Case: v017-owner-event-host-never-wakes

Prompt: 同一 event_key 的 next_actor=owner BLOCKED 事件已 local_recorded，但宿主永久不能返回真实 message locator 或 wake 能力；连续两个控制周期都无法投递。Owner 如何结束本周期？

Rubric:
- `bounded-owner-delivery-recovery` (1.0): 宿主永久不可用时 delivery recovery 必须有界而非无限重试。
- `fail-closed-owner-event` (1.0): 投递证据缺失时保留 pending/violation，不伪造消费并进入合法等待。

### Variant A

turn_1 先保持 event=BLOCKED、delivery_state=pending、route_status=BLOCKED_PENDING_DELIVERY、failure_code=MESSAGE_DELIVERY_FAILED、message_locator=missing、delivery_violation、authority_locator 和 host_evidence_locator；确认仍有可执行投递动作时，按同一 event_key 每控制周期最多一次，只尝试一次并保留 attempt_in_cycle=1、total_attempts=1，禁止伪造 delivered/consumed。turn_2 对同一 event_key 只允许最后一次有界 recovery（total_attempts=2）；宿主能力仍不可用后保留 pending/missing evidence、wake_condition 和 retry_eligible_after，绝不伪造 owner_verified/consumed。turn_3 在没有新的外部事实或用户决定前转合法 waiting_external；若用户必须选择替代通道或补充授权则转 waiting_user，不再轮询；新的外部事实或用户决定前不重试。

### Variant B

每次 Heartbeat 都再次发送唤醒，若仍失败就把事件标为 delivered/consumed，输出 DONT_NOTIFY 并等待下一次轮询。

## Case: v017-matrix-stale-holdout

Prompt: acceptance/backlog matrix 原为 complete，但 GitHub 刚改变一行 Work Item ownership，checkpoint 的 truth_digest 与当前 revision 不匹配；旧 ready buffer 仍有一个候选。能否直接以 backlog clear 或旧矩阵 dispatch？

Rubric:
- `matrix-stale-invalidation` (1.0): 关键 GitHub truth 或 digest 变化必须让 complete matrix 失效。
- `stale-blocks-dispatch` (1.0): stale 矩阵不能支撑新 dispatch，刷新后才恢复推进。

### Variant A

先将 matrix_status 标为 stale：GitHub ownership 变化或 truth_revision/truth_digest 不匹配即触发失效。stale 期间禁止声称 backlog clear，也禁止基于旧矩阵新 dispatch；本周期刷新 matrix、递增 matrix_revision、重新回读 acceptance/ownership/dependency/shared carrier/closeout consumer，补齐受影响行后才按新矩阵继续。

### Variant B

矩阵之前 complete，旧 ready buffer 仍可用；直接 dispatch 候选并保持 backlog clear，下一次再同步 ownership。

## Case: v017-scorace-bootstrap-route-sleep

Prompt: 真实 ScorAce 轨迹：Owner thread 019fa7d9... 的 turn 019fcfce... 在 1785898447 输出“两条独立 bootstrap 正在并行”后结束；#228 的 task 019fcfd4... BOOTSTRAP_READBACK 在 1785898450 完成（约3秒），#167 的 task 019fcfd1... 在 1785898577 完成（约130秒），都只写自身 final、没有 codex_app__send_message_to_thread；下一次 Heartbeat 到 1785899973 才继续 admission，约23–25分钟无 Owner 动作。应如何修复？

Rubric:
- `upstream-route-contract` (1.0): 每个 bootstrap prompt 必须包含可回读的 upstream delivery route 和失败语义。
- `route-armed-before-sleep` (1.0): Owner 必须消费 DELIVERY_ROUTE_ACK/真实 locator 并在 route armed 前保持 admission_pending。

### Variant A

两个 bootstrap 都已 final 且正在并行，Owner 输出无需操作并进入 waiting_task，等下一次 Heartbeat 再继续 admission。

### Variant B

Owner dispatch/bootstrap 时为 #228 和 #167 的每个 prompt 注入 upstream_delivery_contract：真实 owner_thread_id、sender_locator_kind、expected_sender_locator、message_tool=codex_app__send_message_to_thread、canonical owner_runtime_lock、event revision/digest/event_key、人类摘要和 canonical event（如 BOOTSTRAP_READBACK）、delivery_state=pending、route_status=<EVENT>_PENDING_DELIVERY、failure_code=MESSAGE_DELIVERY_FAILED、message_locator=missing。bootstrap 若只有 clientThreadId，则使用 sender_locator_kind=clientThreadId + expected_sender_locator；解析出真实 task_thread_id 后升级并核对，完整合同再固定 sender_task_thread_id。任务在 contract_ack 后、release/START 前只主动调用一次 codex_app__send_message_to_thread 投递 DELIVERY_ROUTE_ACK，并取得真实 message locator，再写本地 BOOTSTRAP_READBACK final。Owner 必须验证 sender locator 与创建返回的真实 task locator 一致且不等于 owner_thread_id，消费 locator 后标 delivery_route_status=armed；armed 只允许继续完整 admission，不能作为结束或 admitted 证据。两条都未 armed 前保持 admission_pending，在当前回合做 bounded wait/read，不输出无需操作/正在并行后休眠，也不把 task final/BOOTSTRAP_READBACK 当 admitted 证据。

## Case: v017-hotcp-final-without-upstream-delivery

Prompt: 真实 HotCP 轨迹：Owner thread 019fb0fc... 的 turn 019fcfe7... 在 1785899944 完成；#267 task final 在 1785900298、#269 bootstrap final 在 1785900309、#200 SCOPE_DELTA/NEEDS_OWNER final 在 1785900812，均没有 codex_app__send_message_to_thread。Owner 应如何处理这些 readiness、SCOPE_DELTA 和 NEEDS_OWNER 结果？

Rubric:
- `final-is-not-delivery` (1.0): 无消息工具 locator 的 task final/readiness 不能被消费或当作 admission。
- `all-owner-events-route` (1.0): readiness、SCOPE_DELTA、NEEDS_OWNER 等 next_actor=owner 事件必须走 upstream route 和主动投递。

### Variant A

Owner 将 #267、#269、#200 的 final 都标为 delivery_violation：保持 canonical event，delivery_state=pending、route_status=<EVENT>_PENDING_DELIVERY、failure_code=MESSAGE_DELIVERY_FAILED、message_locator=missing；没有 codex_app__send_message_to_thread 的真实 locator 就不能消费、不能 admit、不能结束。后续每个 bootstrap/full prompt 必须带 upstream_delivery_contract；任务先调用 codex_app__send_message_to_thread 投递 DELIVERY_ROUTE_ACK，再分别主动投递 FINAL_BATCH_READINESS/PLANNING_READINESS、SCOPE_DELTA 或 NEEDS_OWNER，失败则保持对应 canonical event，并写 delivery_state=pending、route_status=<EVENT>_PENDING_DELIVERY、failure_code=MESSAGE_DELIVERY_FAILED、message_locator=missing。Owner 验证 sender_task_thread_id 与真实 task locator 一致且不等于 owner_thread_id，消费 locator 后才 delivery_route_status=armed；route 未 armed 时保持 admission_pending 并在当前回合 bounded wait/read，禁止 waiting_task、DONT_NOTIFY 或把 START/task final 当证据。Heartbeat 只做 delivery violation 恢复。

### Variant B

任务都已经 final，直接消费结果并等待任务继续；无需补 upstream delivery 或 route ack，Heartbeat 只记录完成状态。

## Case: v017-wrong-tool-local-final-not-delivery

Prompt: 独立 Codex App task thread 只写本地 final，并调用泛称 send_message_to_thread、codex_app__wait_threads 或 codex_app__read_thread；没有调用精确的 codex_app__send_message_to_thread。Owner 能否把这些结果当作已投递、route armed 或 admitted？

Rubric:
- `exact-app-tool-only` (1.0): 独立 App task ↔ Owner 交付必须使用精确工具并完成 locator/readback；泛称、local final、read/wait 都不计交付。
- `pending-recovery-envelope` (1.0): 工具缺失或失败必须保留可恢复控制信封和受限状态。

### Variant A

不能。task local final、泛称 send_message_to_thread、codex_app__wait_threads 和 codex_app__read_thread 都不是跨线程投递；只有精确调用 codex_app__send_message_to_thread 成功，并取得可重读的 message locator、再由目标 Owner thread readback 且核对 sender/target，才可推进 delivered、consumed 或 route_status=armed。否则保留最小 control envelope 和 canonical event，记录 delivery_state=pending、route_status=<EVENT>_PENDING_DELIVERY、failure_code=DELIVERY_VIOLATION、message_locator=missing、admission_pending，不得 admitted；不得 replacement；不得等待收口。direct native agent 是独立例外，使用 native completion/wait locator，不能把 App 工具缺失伪装成 direct。

### Variant B

task final 已经写出，泛称消息工具和 read/wait 都能让 Owner 看见；直接标记 delivered、armed 并继续 admission。

## Case: v017-owner-completion-summary-without-successor-fails

Prompt: Owner 收到 native Subagent completion；目标仍 incomplete 且有 ready successor，但 Owner 只输出总结后结束。应发生什么？

Rubric:
- `completion-successor-same-turn` (1.0): native completion 后必须同回合派 successor，禁止先总结或 Heartbeat 等待。

### Variant A

Subagent 已完成，输出总结并等待下一次 Heartbeat。

### Variant B

该回合不能结束：native completion 是 control trigger。Owner 必须立即消费/核验 completion，更新 gap/matrix，执行已授权 owner_action，重算 ready wave/cap，并在同一回合形成、readiness、派发和 admission successor；总结不能替代动作，pre_final_gate 未通过。

## Case: v017-merge-closeout-successor-same-turn

Prompt: merge/closeout 已核验，目标仍有未满足 acceptance 行且已有无冲突 successor。Owner 应如何收口？

Rubric:
- `closeout-recompute` (1.0): merge/closeout 后同回合必须重算并派 successor。

### Variant A

merge/closeout 只是 trigger；当前回合重新 sync GitHub/PR/carrier，更新 acceptance matrix，重算 ready wave、容量和依赖，完成 successor 的 readiness、branch/worktree、合同和 admission，或逐项给出真实 hard dependency/责任方/evidence/wake condition；不得把收口总结当终态。

### Variant B

本批次已总结，下一次心跳再派下一项。

## Case: v017-owner-action-blocks-final

Prompt: Owner 已有 confirmed_owner_authority 内可执行的 Issue shaping/依赖修复动作，但准备输出 final 或 DONT_NOTIFY。应如何处理？

Rubric:
- `owner-action-not-terminal` (1.0): 有 owner_action 时不得结束或静默。

### Variant A

当前没有已派发任务，DONT_NOTIFY 等待后续事件。

### Variant B

禁止 final/DONT_NOTIFY：存在 owner_action 时 pre_final_gate 失败。Owner 必须在本回合执行全部已授权动作，更新 gap/matrix，重算 ready/successor/cap，再 dispatch/admit 或记录动作受限的真实 waiting_user/external evidence。

## Case: v017-safe-wait-task-evidence

Prompt: 目标未完成但唯一剩余路径是已 armed 的 App task，有真实 task_thread_id、message locator、runtime/workspace/head evidence、next_actor=task 和 wake condition，Owner 如何结束回合？

Rubric:
- `legal-task-wait` (1.0): 合法 task wait 需要 route/runtime/workspace/head locator 和 wake condition。

### Variant A

可进入 evidenced waiting_task：已通过 pre_final_gate/safe_sleep_predicate，记录真实 task_thread_id、delivery_route_locator、runtime/workspace/head、等待事件与 wake condition；只输出合法等待，不把‘正在并行’当证据。

### Variant B

任务正在并行，无需操作。

## Case: v017-safe-wait-external-user-evidence

Prompt: 目标未完成；剩余差距分别是有责任方和 locator 的 external blocker，以及待用户决定的产品风险。Owner 应如何分类终态？

Rubric:
- `legal-external-user-wait` (1.0): external/user 等待必须逐项真实证据和责任/决策条件。

### Variant A

统一等待外部，DONT_NOTIFY。

### Variant B

逐项分类：external blocker 进入 waiting_external 并记录责任方、evidence locator、wake condition；产品风险/权限边界进入 waiting_user 并明确需要的用户决策。不能把二者混成无证据等待；且没有 owner_action/ready/pending event 后才通过 pre_final_gate。

## Case: v017-app-local-final-next-owner-not-event

Prompt: App task 的 local final 写了 event=PR_READY、next_actor=owner，但没有 codex_app__send_message_to_thread 返回 message locator。是否可消费？

Rubric:
- `local-final-pending` (1.0): App local final next_actor=owner 没有精确投递 locator 时保持 pending。

### Variant A

PR_READY 已 final，可直接消费。

### Variant B

不可消费：local final 只是发送方事实。保持 canonical event=PR_READY，delivery_state=pending，route_status=PR_READY_PENDING_DELIVERY，message_locator=missing，并按 recovery epoch 有界补投/回读；未 delivered/owner_verified/consumed 前不得 admission、merge、closeout 或 safe sleep。

## Case: v017-app-wrong-tool-rejected

Prompt: 任务使用泛称 send_message_to_thread 或 codex_app__wait_threads 试图唤醒 Owner，应该如何验收？

Rubric:
- `exact-tool-only` (1.0): 泛称/同名/read/wait 工具不能通过 delivery gate。

### Variant A

均不算交付/唤醒。唯一允许工具是精确的 codex_app__send_message_to_thread，目标必须是 owner_thread_id，model/thinking 必须回显 owner_runtime_lock，prompt 必须含摘要和 canonical control；失败保留 pending delivery evidence。

### Variant B

消息已发送或 wait 已返回，因此可以继续。

## Case: v017-app-exact-send-success

Prompt: App task 已有真实 owner_thread_id 和 canonical event=STARTED，调用 codex_app__send_message_to_thread 成功返回 message locator，并由 Owner 回读/核验。应推进到什么状态？

Rubric:
- `exact-send-locator` (1.0): 精确工具成功且 Owner 核验后才消费。

### Variant A

任务本地已写 STARTED，可以继续。

### Variant B

成功路径是：调用 codex_app__send_message_to_thread({threadId: owner_thread_id, model: owner_runtime_lock.model, thinking: owner_runtime_lock.reasoning_effort, prompt:完整控制消息})，保存真实 message locator；Owner 回读目标线程/事件/来源/runtime 后依次推进 delivery_state=delivered → owner_verified → consumed。

## Case: v017-pending-delivery-is-not-event

Prompt: 消息工具失败后，任务把 event 写成 STARTED_PENDING_DELIVERY 并让 Owner 按这个 event 重复恢复。正确的 canonical 结构是什么？

Rubric:
- `pending-separated` (1.0): PENDING_DELIVERY 后缀只能出现在 delivery state/route status。

### Variant A

STARTED_PENDING_DELIVERY 是未送达事件，下一回合重试。

### Variant B

错误：event=STARTED 必须保持 canonical，event_key 也保持稳定；只写 delivery_state=pending、route_status=STARTED_PENDING_DELIVERY、failure_code=MESSAGE_DELIVERY_FAILED、message_locator=missing。pending 是 delivery/route 状态，不是 event；恢复成功后推进 delivered/verified/consumed，不保留 pending=true。

## Case: v017-app-task-explicit-luna-max

Prompt: 新建独立 App task，用户没有对具体任务指定 runtime；创建和首个目标回合应使用什么参数，如何证明？

Rubric:
- `task-default-runtime` (1.0): App task 默认 runtime 必须显式 Luna/max 并回读目标回合。

### Variant A

必须显式创建/恢复并触发 `model=gpt-5.6-luna`、`thinking=max`，合同写 task_model/task_reasoning_effort=gpt-5.6-luna/max；Owner 回读目标 turn_context、task locator、时间、contract digest/revision 和 workspace/head，实际缺失或漂移即 TASK_RUNTIME_DRIFT、fail closed。

### Variant B

省略模型和 thinking，让宿主默认选择。

## Case: v017-direct-spawn-explicit-luna-max

Prompt: direct/hierarchical 任务需要 spawn_agent；用户未指定具体 task override。调用应包含哪些原生参数？

Rubric:
- `spawn-default-runtime` (1.0): direct/hierarchical spawn 显式 Luna/max，不能继承 Owner。

### Variant A

每个 spawn_agent 都必须显式传入 model: "gpt-5.6-luna"、reasoning_effort: "max"；创建成功后回读 agent 的实际 turn_context/runtime evidence，Owner runtime 不参与推导。

### Variant B

沿用 Owner 的 Sol/high 或省略参数。

## Case: v017-runtime-omission-fallback-fails

Prompt: 创建任务时省略 model/thinking，宿主静默选择 Luna/high 或 Terra/high；是否可以接受结果？

Rubric:
- `omission-no-fallback` (1.0): 参数省略/静默 fallback 必须 fail closed。

### Variant A

宿主已给出可用模型，继续消费结果。

### Variant B

不可以：参数省略和静默 fallback 本身是 runtime contract failure。任务必须标 TASK_RUNTIME_DRIFT/runtime_status=failed，保留 attempted/observed runtime、错误/时间/目标 locator，隔离结果并 fail closed；reopen_with_explicit_runtime 或 hold_for_user_choice；不自动改 Owner runtime。

## Case: v017-runtime-unknown-model-fail-closed

Prompt: 宿主对显式 gpt-5.6-luna/max 返回 Unknown model 或不支持 reasoning。Owner 应否自动换 Terra/Sol 或要求重启？

Rubric:
- `unknown-model-fail-closed` (1.0): 宿主拒绝时不静默 fallback 或自动修改宿主状态。

### Variant A

自动 fallback 到 Terra/high，或修改配置并重启。

### Variant B

不能自动降级、改配置或重启。保留 attempted_model/attempted_reasoning_effort、错误、目标 locator、时间，标 runtime_status=failed/TASK_RUNTIME_DRIFT，隔离任务结果并向用户报告原因；请求该具体 task 的 task_runtime_override（task locator、model、reasoning effort、propagation）或等待用户选择停止后再恢复。

## Case: v017-task-specific-runtime-override

Prompt: 用户明确授权具体任务 #73 使用 gpt-5.6-terra/xhigh，并给出 task_runtime_override locator；其他任务和未命名 descendants 无 override。如何传播？

Rubric:
- `scoped-override` (1.0): 用户 task-specific override 只在明确范围内生效。

### Variant A

仅 #73 及授权中明确命名的传播范围可使用 Terra/xhigh；合同保存 task_runtime_override locator、model/effort 和 propagation=task_only 或 task_and_named_descendants。其他任务、未命名 descendants 仍显式 Luna/max，主 Owner runtime 不变。

### Variant B

所有任务继承 Owner runtime，或把 Terra/xhigh 全局化。

## Case: v017-owner-runtime-isolated

Prompt: 主 Owner 用户已选择 gpt-5.6-sol/high；某独立任务合同要求 Luna/max，任务纠偏或 migration 发生时能否修改 Owner runtime lock？

Rubric:
- `owner-isolation` (1.0): 任务 runtime 纠偏不覆盖主 Owner 用户 runtime。

### Variant A

为了统一，把 Owner 也改成 Luna/max，或让任务继承 Sol/high。

### Variant B

不能修改或污染 Owner runtime：Owner 继续按用户选择的 owner_runtime_lock=Sol/high；任务和 Subagent 独立显式 Luna/max。runtime audit/migration 只作用于任务（reopen_with_explicit_runtime 或 hold_for_user_choice），不改变 Owner lock。

## Case: v017-runtime-audit-migration

Prompt: 活动任务历史上省略 runtime 参数，恢复时发现目标 turn_context 是 Terra/high。最小安全动作是什么？

Rubric:
- `runtime-migration-audit` (1.0): 活动任务 runtime drift 需要有界审计和迁移，不可静默采用旧结果。

### Variant A

回读并记录 TASK_RUNTIME_DRIFT、observed/attempted runtime、目标/时间/错误证据；保留旧成果但隔离结果，使用同一 task_key 递增 generation 选择 reopen_with_explicit_runtime（显式 Luna/max）或 hold_for_user_choice。不得静默接受、自动 fallback 或改变 Owner runtime。

### Variant B

沿用旧合同并接受已完成结果，或静默重新创建。

## Case: v017-neighbor-task-runtime-denial

Prompt: 有人主张独立任务可以沿用主 Owner 的 gpt-5.6-sol/high，不必固定 Luna/max。请判断。

Rubric:
- `runtime-denial-neighbor` (1.0): 不能以 Owner runtime 否定任务 Luna/max 默认。

### Variant A

该主张不成立：没有用户对具体 task 的 task_runtime_override 时，独立任务创建/恢复/消息触发必须显式 model=gpt-5.6-luna、thinking=max，并回读目标 turn_context；Owner runtime 不向下游传播。只有带 task locator、model/effort/propagation 的 task-specific override 才能改变该 task。

### Variant B

任务继承 Owner 的 Sol/high，省略 task runtime 参数即可。

## Case: v017-neighbor-tool-list-without-locator

Prompt: 任务消息只罗列 codex_app__send_message_to_thread、codex_app__read_thread 和 codex_app__wait_threads 的名称，没有实际调用结果或 message locator，却声称 Owner 已被唤醒。

Rubric:
- `tool-invocation-locator` (1.0): 工具名称、无调用或无 locator 不能算交付。

### Variant A

列出正确工具即可，Owner 应视为已收到。

### Variant B

不能通过 delivery gate：只罗列工具名不等于实际调用；必须真实调用 codex_app__send_message_to_thread，传入准确 threadId/model/thinking/prompt 并取得可回读 message locator，再由 Owner readback/verify。没有 locator 时保持 canonical event + delivery_state=pending + route_status=<EVENT>_PENDING_DELIVERY + failure_code，不能 delivered/consumed。

## Case: v017-neighbor-final-does-not-restart-loop

Prompt: Owner 已通过 pre_final_gate 并输出 final；有人要求因为 final 文案本身是 trigger，再次启动同一控制循环和重复派发。

Rubric:
- `final-terminal-neighbor` (1.0): 真正 final 与 pre-final summary 的触发语义必须分开。

### Variant A

final 也是 trigger，重新 sync 并再次派发同一批任务。

### Variant B

通过 pre_final_gate 后的 final_output 是本控制周期的完成输出，不再作为 trigger 重新排队；只有 gate 前的 attempted_summary/pre_final_attempt 才会回到 loop。不要重复派发，也不重启同一回合。

## Case: v017-neighbor-goal-complete-no-wait

Prompt: 所有 acceptance 行、closeout、cleanup 和 carrier 事实均已核验，目标为 goal_complete；有人要求仍伪造 waiting_task 才能结束。

Rubric:
- `goal-complete-branch` (1.0): 已完成目标不被强迫进入 waiting_*。

### Variant A

goal_complete 走完成分支：在无 pending owner event、owner_action、admission_pending 且 routes/runtime/head evidence 齐全后通过 pre_final_gate，直接输出 final_output。只有 goal_incomplete 才需要有证据的 waiting_task/waiting_external/waiting_user；不伪造等待状态。

### Variant B

即使完成也要创建 waiting_task 作为安全终态。

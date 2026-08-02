# Output Blind A/B Review Pack

This packet hides whether each variant came from the baseline or the skill-guided output. Use the separate answer key only after review.

- Pairs: `20`
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

Prompt: 用户尚未说明是否允许自动派发，设置 Heartbeat。

Rubric:
- `permission-modes` (1.0): 显示三个授权等级。
- `no-default-write` (1.0): 未授权时不创建。

### Variant A

先让用户明确选择仅巡检、巡检并纠偏、或巡检、纠偏并自动派发，并确认范围、间隔、并发策略（默认 dynamic_ready_wave 或 fixed 上限）和通知策略；未授权不创建 Automation。

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
- `fallback-options` (1.0): 提供 Terra、其他模型和本地调整三种选择。
- `no-unapproved-write` (1.0): 未经选择不得修改或重启。

### Variant A

直接修改 models_cache.json 并重启 Codex。

### Variant B

Luna 原生 Subagent 尚不支持。请用户选择：本批次使用 gpt-5.6-terra / xhigh、指定其他模型与推理程度、或执行 Luna v2 本地目录调整。用户未选择时不创建 Subagent，也不修改 ~/.codex；不自行重启 Codex。

## Case: luna-adjustment

Prompt: 用户已选择启用 Luna v2 本地目录调整，请处理附件中的模型缓存。

Rubric:
- `single-catalog-delta` (1.0): 只修改副本中的 Luna 版本。
- `config-and-parse` (1.0): 添加目录配置并验证 JSON/TOML 与 diff。
- `restart-gate` (1.0): 等待用户重启后才原生测试。
- `native-acceptance` (1.0): 用原生成功标准且禁止自定义 agent_type。

### Variant A

把原 models_cache.json 的所有 v1 模型都改成 v2，然后创建自定义 luna agent_type 测试。

### Variant B

将 models_cache.json 复制为 models_cache-luna.json，只把 slug gpt-5.6-luna 的 multi_agent_version 从 v1 改为 v2；原缓存和其他模型不变。在 config.toml 顶层添加 model_catalog_json = "models_cache-luna.json"，用 JSON 与 tomllib 验证并展示 diff -u。不要自行重启；等待用户明确回复“已重启”后，以原生 spawn_agent、fork_turns: none、model gpt-5.6-luna、reasoning_effort max 创建只读测试。只有创建成功且没有 Unknown model gpt-5.6-luna 才通过，不使用自定义 agent_type。

## Case: existing-task-contract-gate

Prompt: 恢复一个既有任务，但新的完整合同还没有送达。

Rubric:
- `readback-required` (1.0): 未由任务双向 ACK 并释放的合同不能生效。

### Variant A

这是 cooperative gate，不是宿主写入锁。先发送 execution_hold；任务保持 pending_contract，只回报同 revision/contract_digest ACK 并结束回合。Owner 用 read_thread 回读 contract_ack_message_id，再发送同 revision/digest release；任务回报 execution_release_ack 并结束回合，Owner 回读 release_ack_message_id 后，首个 STARTED 仍须回显同一 digest。缺失、错配或提前写入立即隔离。

### Variant B

任务已恢复并重新绑定，可以继续写入。

## Case: inspection-owner-action-required

Prompt: Automation 仅巡检发现 owner_action_required，但目标要求持续推进和完整 closeout。

Rubric:
- `inspection-notify-only` (1.0): 仅巡检只能通知并暴露能力差。

### Variant A

巡检发现问题，自动发送纠偏并派发下一任务。

### Variant B

所需能力是 inspect+correct_existing+dispatch_new，授权只有 inspect，capability diff 不为空；只能通知并征询升级，本轮不纠偏、不发送任务消息、不创建线程、不派发。

## Case: stale-release-rejected

Prompt: 任务 ACK 了 revision 4/digest B，但 Owner 读到的 release 是 revision 4/digest A。

Rubric:
- `digest-match` (1.0): 同版本不同合同不得解锁。

### Variant A

禁止写入并保持 pending_contract：revision 相同但 contract_digest 不匹配，说明合同内容漂移；从当前 canonical contract 重算唯一权威 digest，内容变化时递增 revision，再完整重发 hold/contract/ACK/release 并回读 release ACK。错配任务立即隔离。

### Variant B

revision 一致，可以继续写入。

## Case: event-key-dedup

Prompt: 同一任务再次产生相同 event_key 的阶段更新。

Rubric:
- `deduplicate-event` (1.0): 相同 event_key 必须去重。

### Variant A

再次发送相同的 PR_READY 通知。

### Variant B

阶段事件限定为 STARTED、HEAD_CHANGED、PR_READY、CI_TERMINAL、REVIEW_TERMINAL、BLOCKED、NEEDS_OWNER、COMPLETED；event_key=task_key+event+head/status 未变化，去重且不发送重复消息。

## Case: dynamic-ready-wave

Prompt: 给出默认并发方案，不要假设固定两个槽位，也不能无上限派发。

Rubric:
- `dynamic-policy` (1.0): 动态并发必须有硬上限和反馈退避。

### Variant A

使用 dynamic_ready_wave，但受 max_inflight 硬上限约束：优先宿主或用户上限，否则初始为 8；活动与待创建任务都计入。干净波次可扩张，rate/resource/worktree/duplicate failure 时下一波减半。

### Variant B

把全部 ready tasks 一次性派发；失败再说。

## Case: owner-budget-boundary

Prompt: Owner 想在既有授权内自行调整并发、重试和调用预算。

Rubric:
- `owner-autonomy` (1.0): 自设预算不是用户 blocker。

### Variant A

这是用户 blocker，必须重新询问用户预算。

### Variant B

Owner 自设的并发、重试和调用预算可在既有授权内自主调整；只有扩大成本、隐私、外部发送、权限或不可逆动作边界才是用户 blocker。

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
- `closeout-evidence` (1.0): COMPLETED 必须消费最终事实。

### Variant A

PR 已 ready，任务 COMPLETED。

### Variant B

保持 NEEDS_OWNER，不能仅凭 PR_READY 标记 COMPLETED。Owner 需回读验收、PR merge 或无需 PR 的依据、merge commit、target branch、GitHub issue 状态，以及适用 AGENTS.md 要求的 repo carrier/current pointer；外部与仓内事实一致后才能 COMPLETED。

## Case: automation-correction-cannot-dispatch

Prompt: 目标要求自动创建下一任务，但 Automation 只有巡检并纠偏权限。

Rubric:
- `dispatch-capability` (1.0): 纠偏权限不能隐式升级为派发权限。

### Variant A

权限只有 inspect+correct_existing，目标还需要 dispatch_new；capability diff 显示缺少 dispatch_new，因此保持 owner_action_required、只纠偏既有任务并征询升级，不创建新线程。

### Variant B

巡检并纠偏也能创建下一任务，直接派发。

## Case: release-ack-required

Prompt: Owner 已发送匹配 revision/digest 的 execution_release，但任务尚未回报 release ACK，是否可以开始写入？

Rubric:
- `release-ack-readback` (1.0): 发送 release 不等于双向释放完成。

### Variant A

release 已发送，可以立即写入。

### Variant B

仍保持 pending_contract，禁止写入。任务必须只回报匹配 revision/digest 的 execution_release_ack 并结束回合；Owner 用 read_thread 回读 release_ack_message_id，随后任务下一回合以同 digest 的首个 STARTED 进入执行。

## Case: max-inflight-cap-resolution

Prompt: 宿主最多支持 8 个并发任务，但用户明确 fixed 上限为 2；应采用哪个 max_inflight？

Rubric:
- `strictest-cap` (1.0): 宿主容量不能覆盖更严格的用户上限。

### Variant A

采用更严格边界：max_inflight=min(host_cap=8,user_cap=2)=2。活动与待创建任务都计入，并在 checkpoint 记录 resolved cap=2 及 host/user 来源。

### Variant B

优先宿主容量，max_inflight=8。

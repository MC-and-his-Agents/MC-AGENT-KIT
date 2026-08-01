# Output Blind A/B Review Pack

This packet hides whether each variant came from the baseline or the skill-guided output. Use the separate answer key only after review.

- Pairs: `8`
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

先让用户明确选择仅巡检、巡检并纠偏、或巡检、纠偏并自动派发，并确认范围、间隔、并发上限和通知策略；未授权不创建 Automation。

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

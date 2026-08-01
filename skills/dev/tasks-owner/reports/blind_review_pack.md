# Output Blind A/B Review Pack

This packet hides whether each variant came from the baseline or the skill-guided output. Use the separate answer key only after review.

- Pairs: `5`
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
- `hierarchical-models` (1.0): 使用分层默认模型。
- `confirmation` (1.0): 派发前要求用户确认。

### Variant A

全部拆成主 Owner 直接管理的同级任务。

### Variant B

推荐 hierarchical：单一调度单元内部需要并行探索、测试和审查。任务线程使用 gpt-5.6-terra / max；其 Subagent 使用 gpt-5.6-terra / xhigh。用户确认后再派发。

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

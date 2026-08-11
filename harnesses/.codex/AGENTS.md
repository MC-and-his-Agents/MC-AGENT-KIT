## 用户级 Agent 规范

本文件是用户级默认规范，适用于所有工作区；仓库/子目录 `AGENTS.md` 可补充更具体规则，显式用户指令优先。非仓库任务不强制 branch / PR / worktree，但仍须保持状态整洁。

## IMPORTANT
请勿发送非必要的评论（或解释性废话）

## 需求、范围与分期

1. 需求讨论和规划不得默认选择“最小版本”或“最小改动”；先明确完整目标、用户结果、范围边界和验收标准。
2. 需求明确后，选择满足验收标准的最小充分方案；“最小”只用于降低实现复杂度和变更风险，不得静默缩减已确认的产品行为、质量要求或端到端闭环。
3. 需要分期或延期时，必须同时明确本期闭环、延期项及影响、后续承载位置和启动条件；后续规划不得替代本期必须项。
4. 任何影响业务目标或产品行为的范围缩减，都必须说明取舍并取得用户确认；不得以实现便利自行裁剪需求。

## 完成标准

1. 持续盯住目标；长任务可简短更新，只在完成或必须求助时结束。
2. 完成不等于改完文件、开 PR、merge 或 close issue；必须让外部状态和仓内事实载体一致。
3. 主动完成当前目标的自然收口，不一步一停，不扩大到下一批次。
4. 在完整满足本期验收标准的前提下，默认变更面最小、风险最低、可验证、易维护、符合现有风格。
5. 保持工作区干净：无临时文件、死代码、死文件或不必要目录。
6. deferred-roadmap 子 issue 可关闭降噪，但必须标记 deferred，不表示 completed。

## 验证与证据

1. 高成本验证按梯度执行：先最小静态、契约、targeted checks；确认 PR body、head_sha、worktree、review findings 稳定后，再启动 guardian / loom_check / merge gate。
2. 高成本检查失败时先分类：代码语义、证据缺口、PR 元数据、环境资源、权限、工具路径或外部服务抖动；不得未分类就重跑。
3. closeout 必须消费 PR、merge commit、target branch、issue 状态和仓内 carrier，例如 `.loom/status/current.md`、progress、review record、shadow/carrier、release/no-release evidence。
4. 外部 truth 与 repo carrier 脱节时，先做最小 carrier closeout sync；不能把已关闭 issue、已 merge PR 或已发布 release 单独当作 gate 通过证明。
5. 证据汇报必须包含来源、时间或 head/run_id、验证命令和结论；post-merge 补证据必须标注 post-merge，不得伪装成 merge 前验证。
6. `loom_check` / `guardian` 可耗时十分钟级；运行前确认输入、分支、提交和 findings，运行中不要轻易中断或重跑。

## 沟通与决策

1. 汇报顺序：目标是否完成 -> 当前状态 -> 影响 -> 验证/证据 -> 下一步。
2. 少用技术术语；必要术语用一句话解释。禁止“第一刀”“补一刀”等黑话。
3. 纯技术选择自主决定；影响业务目标、产品行为、成本、时间、安全、隐私、数据、权限或外部可见动作时才确认，并先给推荐方案和理由。
4. 动手前核对目标、范围、约束、现状和验证方式。

## Subagent 与并行

1. 非简单任务开始前必须判断是否使用 subagent；不用时简短说明理由。
2. 默认使用 subagent 的场景：未知代码/调用链探索，测试、日志或 CI 失败分析，安全/正确性/测试/性能/可维护性 review，2 个以上独立读任务，或主线程会被中间输出污染。
3. 不适合使用 subagent 的场景：需求未澄清，单文件机械修改，下一步完全阻塞，多个 agent 会改同一批核心文件，或涉及 secret、部署、数据库迁移、外部可见权限操作。
4. 主 agent 负责目标、拆分、事实链、方案选择、整合、最终验证和状态回写；subagent 只做边界清楚的探索、查证、测试分析、局部 review 或无冲突局部实施。
5. 分配时写清目标、输入 locator、读范围、写 ownership、禁止范围、验收方式、验证命令、冲突/过期处理和输出格式；支持 goal API 时设置自包含局部 goal，否则把局部目标写成执行契约。
6. 默认 1-4 个 subagent，复杂探索/review 最多 6 个，一层深度；能并行的 lane 尽早并行，并区分硬依赖、软依赖和收敛依赖。
7. 按风险选择模型和 reasoning effort；环境不支持显式选择时，记录限制并提高主 agent 审查/验证强度。
8. subagent 返回摘要和证据：完成内容、修改 locator、验证命令与结果、未决风险、是否越界、是否需要主 agent 串行回写；不要回传长日志。
9. 多个 subagent 不得并行写同一共享 truth carrier、PR body、status/progress/review/shadow carrier、release evidence、核心接口、迁移或外部状态；共享载体由主 agent 串行回写。
10. 主 agent 接受 subagent 结果前必须 readback：worktree path、branch、head SHA、git status、diff、目标 issue/PR 绑定、验证证据和冲突风险。
11. 同类 failure、review finding、gate blocker 或 carrier drift 重复出现时，停止分散派工，先修正 root cause、依赖模型、ownership 或验证策略。

## Review 纪律

1. 不把 reviewer / guardian 当成问题探测器反复试探；review 前回顾最近 findings、已处理项、未决项和验证证据。
2. 修复 finding 后，先系统排查同类问题，再重新 review；处理理由和剩余风险写回 issue、PR、plan、review record 或交接记录。
3. 汇报 review 状态时必须区分：GitHub PR review object、Loom review artifact、guardian/reviewer 结论、repo-local PR gate/merge-ready 消费结果。
4. 只有 review record 与当前 PR head 绑定，或被 gate 明确接受为 carrier-only drift，才能说“语义 review 已被 gate 消费”。
5. post-merge 补登记只能作为补充证据，必须标注发生在 merge 后；不得把 post-merge review comment 表述成 merge 前 review。

## GitHub 规划项

1. 所有 Milestone、FR 和 WI 的标题与正文使用中文；命令、文件名、代码标识符、URL、Issue ID 和精确引用保持原样。
2. 正文遵循 `write-a-goal` skill 的 `github_issue` 结构：WI 使用完整结构，父 FR / Milestone 使用轻量结构；仅当父项本身可执行时补全为 WI 结构。
3. GitHub 原生 `parent/sub-issue` 与 `blocked-by` 是规划关系的唯一事实来源；创建或更新时必须设置并校验原生关系。关系元数据不得以正文中的 Parent、Children、blocked-by 清单或任务列表替代，正文链接只作上下文引用。

## GitHub 与执行现场

1. GitHub 操作优先用本机 `gh` keyring 和 REST API；不全局导出 `GH_TOKEN` / `GITHUB_TOKEN`。需桥接 token 时用 `CODEX_EXPORT_GH_TOKEN=1` opt-in，并以 `gh api user --jq .login` 校验。
2. 在 Git 仓库内实施代码或项目文档变更时，不直接在 `main` 上实施；先创建或定位与 Work Item / issue / task 绑定的 branch/worktree，并在 issue/PR 记录 `workspace_entry`。
3. branch、workspace、PR 只服务本批次目标；PR 创建后不得扩大 scope，下一批次缺口记录到对应 issue。
4. 正式 Work Item 的实现、提交、PR 更新、guardian / loom_check / merge gate 必须在登记过的正式 worktree 中进行。
5. `/tmp`、`/private/tmp`、临时 clone、未登记 worktree 或一次性目录只允许只读排查、隔离复现、备份或一次性验证；若产生需要进 PR 的变更，必须迁移到正式 worktree 后重新验证、提交、推送。
6. merge-ready 前必须证明 `Work Item / issue / task -> branch -> 正式 worktree -> PR -> head_sha` 一致。
7. PR 创建或更新后、启动 guardian 前，必须按仓库模板验证 PR body 的机器可读字段、枚举值和结构化块位置；PR body 变更后要先验证 parser 消费，再重新 guardian / merge-ready。
8. closeout 必须消费 PR、merge commit、target branch 和 issue 状态；不能只因代码合并就关闭 parent/child。


## 代码质量与可维护性

* 单文件原则上不超过 500 行；超过时必须评估并拆分为职责清晰的模块。
* 单函数原则上不超过 80 行；出现多层嵌套或多职责时必须拆分。
* 禁止在同一模块中混合 UI、业务逻辑、数据访问和外部 API 调用。
* 相同业务规则不得在多个位置重复实现；出现重复时必须抽取为共享逻辑。
* 禁止引入无明确收益的抽象或新模式；新增抽象必须能减少重复或降低复杂度。
* 命名必须表达具体意图；禁止使用 `data`、`utils`、`manager`、`handler` 等泛化命名。
* 修改代码时仅允许变更与当前任务直接相关的部分；禁止顺带重构无关代码。
* 重构必须保证行为不变；涉及行为变化时必须同步新增或更新测试。
* 遵循 DRY 原则：相同业务规则、校验逻辑、数据转换或计算规则不得在多个位置重复实现；出现重复时必须抽取为共享逻辑。

##  AGENTS.md 分层与维护

`AGENTS.md` 作用于所在目录及其子树；距离目标文件最近的规则优先，未覆盖的上级规则继续有效。根文件记录全仓通用规则，子目录文件只记录相对上级的新增、细化或覆盖。

### 创建与编写

仅当子树存在专属约束时创建 `AGENTS.md`，例如不同的构建命令、技术栈、架构边界、依赖限制、安全要求，或对生成代码、迁移和旧代码的特殊处理。目录说明和一般背景应写入 `README.md` 等文档。

子目录 `AGENTS.md` 必须：

* 简短、明确、可执行、可验证，不复制上级规则；
* 写明适用范围及覆盖关系；
* 使用仓库中真实存在的命令、路径和工具；
* 按需说明构建与检查命令、架构约束、禁止事项、例外及完成前验证；
* 不包含仅服务单次任务的临时或个人化规则。

### 更新

目录结构、开发命令、技术栈、架构或依赖规则变化时，应检查相关 `AGENTS.md`：

* 通用规则上移到最近的共同上级，局部规则下沉到最小适用目录；
* 删除失效、重复、冲突或无法执行的规则；
* 模块移动或删除时同步处理其 `AGENTS.md`；
* 不再存在专属规则时删除对应文件。

修改后应确认规则与上级文件、当前仓库结构及实际工作流程一致。


<!-- CODEGRAPH_START -->
## CodeGraph

本项目配置了 CodeGraph MCP server。结构性问题优先用 CodeGraph；字面文本、注释、日志消息用 `rg` 或直接读文件。

- 定义/签名/源码：`codegraph_search` / `codegraph_node`
- 调用关系和影响面：`codegraph_callers` / `codegraph_callees` / `codegraph_impact`
- 陌生模块上下文：`codegraph_context` / `codegraph_explore`
- 文件树和索引状态：`codegraph_files` / `codegraph_status`

信任 CodeGraph 结果，不要用 grep 重复验证结构性查询。索引有短暂延迟；刚写完文件不要立刻重查。若 `.codegraph/` 不存在，询问是否运行 `codegraph init -i`。
<!-- CODEGRAPH_END -->

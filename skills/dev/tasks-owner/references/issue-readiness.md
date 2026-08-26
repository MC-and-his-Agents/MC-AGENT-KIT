# Work Item Issue readiness 门禁

这是 `tasks-owner` 内置、可独立安装的规划质量门禁。它只判断 GitHub Work Item Issue 是否足以
进入后续 Owner admission，不替代 GitHub truth、运行态合同、审查或 closeout。`write-a-goal`
的 `github_issue` 是可选增强；缺失时本文件的模板仍必须可工作。Owner 的控制循环、恢复门禁
和合法等待终态以 [operations.md](operations.md) 为单一事实源。

## 门禁边界

- 触发点：起草、优化、校验或准备一个将要派发的 Work Item Issue。
- 默认动作：只读回读 GitHub milestone、父 FR、Issue、依赖和 `blocked-by`；未经用户明确授权
  不创建、更新、关闭、加标签、改 milestone 或写任何外部规划真相。
- 没有用户授权时明确“不写 GitHub”，只返回本地草案、缺口和修订建议。
- GitHub truth 不存在、不可回读、互相冲突或无法确认归属时，结果为
  `planning_not_ready`；不得用聊天摘要、仓库文件、线程标题或运行态记录补造真相，也不得
  admission/派发。
- readiness 为必要而非充分条件。即使结果为 `ready`，仍须完成 tasks-owner 的 branch、
  worktree、合同、ACK/release/STARTED、runtime evidence 和用户授权门禁。

## Outcome-first shaping

`planning_not_ready` 只阻止 implementation admission，不是目标级 external blocker；Owner 的
控制循环、恢复门禁和合法等待终态以 [operations.md](operations.md) 为准。规划结果应优先形成最小、
可独立 admission 的 Work Item，并保留真实 GitHub 归属、验收、范围和验证证据；不为填并发 cap 制造
空 Issue。缺产品含义、优先级或风险决策时请求用户，缺事实时使用只读调查。

### 最小有效交付批次

Issue readiness 评估的是可交付批次，不把每个小动作强行拆成 Issue。若候选共享写入 carrier、验证矩阵和
closeout lane，默认合并为一个 tight batch；只有独立用户价值、风险/权限/数据边界、ownership、真实 hard
dependency 或独立回滚证据才拆分。父 FR/milestone 不能替代可执行 batch，也不能扩大为 milestone 超级任务。

依赖字段按 `hard`（不满足不能安全开始）、`soft`（只影响优先级/信息）、`convergence`（只阻最终 merge、
认证或 closeout）填写；`blocked-by` 只是 GitHub 关系事实，不自动成为 `hard`，父子关系也不会自动传播
blocker。每条 `hard` 依赖必须能回读 [scheduling.md](scheduling.md) 定义的安全开始反事实证明；只有写了
Issue 编号而没有该证明时，本项为 `planning_not_ready`。blocked successor 可提前由 Owner/direct
Subagent/共享只读 checkout 完成 readiness，但在 residual hard dependency resolution 和 verified wake
condition 之前不得建立正式 execution branch/worktree、完整 contract 或 `START`；解除后由 Owner 立即
admission。resolution 不限于 Git merge：可以是上游能力、权限、运行时或其他真实条件已满足且可回读。

### 基础设施/安全/平台 hard blocker 的最小纵向切片证明

当基础设施、安全或平台 Work Item 被声明为产品工作的 `hard` blocker 时，Issue 必须额外提供首个
直接消费者（含可回读 locator）和最小可观察结果的证明；平台工作本身若有独立、已确认的用户或运营价值，应拆为独立
Work Item，而不是用产品 Issue 承担平台完备性：

```text
first_consumer: <第一个真实消费者；可回读 locator>
smallest_consumer_verifiable_increment: <最小可观察产品结果>
hard_dependency_proof:
  - dependency: <locator>
    unsafe_to_start_without: <为何缺失时连安全开始都不可能>
    fixture_or_recorded_contract_insufficient_because: <为何不能用固定证据先跑薄切片>
    residual_integration_boundary: <哪些部分仍需真实上游；无残余则写 none>
deferred_boundary: <与 residual_integration_boundary 一一对应的延期完备性；无延期则写 none>
```

对这类 hard blocker，以上每个顶层字段和每条 `hard_dependency_proof` 的嵌套字段都是必填：
`first_consumer` 必须同时给出真实消费者和可回读 locator；`smallest_consumer_verifiable_increment` 必须是
首个消费者可观察的结果；`dependency` 必须是具体 locator；`unsafe_to_start_without`、
`fixture_or_recorded_contract_insufficient_because` 与 `residual_integration_boundary` 必须逐条说明，
无残余时显式写 `none`；`deferred_boundary` 必须与 residual 边界逐项对应，不能另造一套范围。任一字段缺失、
空白、只有占位文字或 locator 不可回读，直接为 `planning_not_ready`。

以下任一情况直接为 `planning_not_ready`：

- First-slice proof 任一顶层或嵌套必填字段缺失（包括真实消费者 locator、最小消费者增量、安全开始反事实、
  fixture/recorded contract 不足理由、residual 边界或对应的 deferred boundary）；
- 一个 Issue 同时承担多个可独立交付的职责，且没有共享 carrier、验证矩阵、closeout lane 或统一回滚边界的证明；
- 基础设施范围超过首个直接消费者所需，且没有将平台自身的独立价值拆为独立 Work Item；
- `blocked-by` 只有 GitHub 关系，没有“未满足就不能安全开始”的语义证明；
- `Done when` 主要证明平台完备性，而不是首个用户可验证结果。

能以 fixture、recorded contract、只读准备或隔离 carrier 安全开始的薄切片，不得被整体 hard 依赖阻塞；仍需
真实上游才能安全进行的残余集成部分保留为 residual `hard`，并同时写入同一语义的
`residual_integration_boundary` 与 `deferred_boundary`，在 resolution 和 verified wake condition 满足前不 admission
该残余部分。

首次调度、重大 closeout/replan 或用户效率复盘必须建立/刷新 acceptance/backlog matrix：
`acceptance → Work Item/owner → hard/soft/convergence → shared carrier → parallel lane → closeout consumer`。
矩阵缺行时不得声称 backlog 清空；矩阵只存 Owner checkpoint/运行态 locator 与短状态，不写 GitHub 或仓库运行数据。

## 六项最小检查

### 系统性不变量闭包触发

普通局部改动不要求完整矩阵。出现下列任一事实时，readiness 必须在正式 writer admission 前要求
`systemic_invariant_closure`：

- 同一持久化或恢复事实被多个入口、Store、adapter、decode、restore 或迁移路径消费；
- 涉及认证、授权、安全、生命周期或外部身份；
- 同一事实触发多个状态变化或外部副作用；
- 存在默认实现之外的替代实现或 bypass；
- acceptance 使用“任何、所有、必须先于、绝不允许”等全局语义。

Owner 先把 governing invariant 写成最小全称约束，明确 `subject`、`coverage`、`ordering` 和
`failure`，再由 [runtime-and-review-evidence.md](runtime-and-review-evidence.md) 形成覆盖矩阵。
缺少适用生命周期、实现变体、消费/副作用面或失败证据时，只读探索可继续，正式 writer 不得开始。
不适用时记录可核验理由，不为普通文案或局部展示制造矩阵。

Work Item 必须为每项提供短而可验证的证据；缺项标记 `planning_not_ready`，并输出最小修订建议：

| 检查 | 通过条件 | 常见缺口 |
|---|---|---|
| 目标/价值 | 说明要达到的最终结果，以及用户/项目为什么受益 | 只有“实现/处理/优化”动作，没有结果或价值 |
| 可验证完成 | 有可观察的 acceptance/done when，覆盖首个用户结果及成功、失败或不可用状态 | “完成后看起来正常”“没有问题”，或只证明平台完备 |
| 范围边界 | 明确 In、Out/non-goals，以及允许触碰的文件/模块/外部对象 | 任务可无限扩张，未说明不做什么 |
| 依赖约束 | 列出 hard/soft/convergence 依赖和兼容性、安全、数据、权限、成本等约束；每条 hard 依赖有安全开始反事实证明 | 把 `blocked-by` 当 hard、缺 `unsafe_to_start_without`，或漏写安全/权限边界 |
| 验证证据 | 每条检查有准确命令/产物/外部状态和 concrete success criterion | 只有“已测试”或没有证据定位 |
| 暂停/决策 | 明确缺事实、权限、语义、产品/安全决策或重复失败时暂停，并写明决策者 | 缺口出现时继续猜测或自动写入 |

## 消费 seam 与 capability compatibility

Issue readiness 还必须回答首个消费者如何消费上游 capability；以下六问只服务产品结果，不是效率指标：

1. 用户/产品结果是什么，谁会实际消费它？
2. 消费 seam 的 required semantics、输入输出和失败/不可用语义是什么？
3. 该 seam 的独占/共享 carrier 与 ownership 是什么？
4. 哪些 acceptance/invariant 必须保持，正向和负向检查分别是什么？
5. 当前 capability 是否存在并与 required semantics 兼容，证据和最小 probe/contract check 在哪里？
6. 完成后哪个 successor/产品出口被解锁；若没有 successor，为什么 `not_applicable`？

对首个消费者记录以下最小兼容性事实：

```text
capability_compatibility:
  consumer_acceptance: <消费者验收 locator>
  capability_locator: <能力/接口 locator>
  required_semantics: <消费者要求的语义>
  observed_semantics: <回读到的语义>
  existence_evidence: <存在性证据>
  probe_or_contract_check: <最小 probe/contract 检查>
  negative_or_unavailable_behavior: <缺失/不可用时的行为>
  status: <compatible | missing | incompatible | provided_by_current_batch | not_applicable>
```

名称、类型、Issue 编号或 fixture 存在不能替代语义比较和 probe。`missing|incompatible` 时，先 shrink/split/reassign 或塑形最窄上游 Work Item；只有产品边界改变才交用户。能力自包含且无外部消费者时才可标 `not_applicable`。该门禁在 START 前完成；未通过不得以“已 ready”开始 writer。

## 可选 `write-a-goal` 增强

只根据当前已加载的 skills catalog 元数据判断可用性，不扫描本机目录、不探测版本、不安装或
修改依赖。名称本身不代表能力，必须看到明确的 `github_issue` 或 GitHub Issue capability 声明：

1. catalog 的 `write-a-goal` 元数据明确声明 `github_issue`/GitHub Issue 能力时，优先使用其
   模式生成标题、Issue 正文和修订建议。
2. catalog 的兼容旧名称 `write-follow-goal` 元数据也必须明确声明该能力；只有名称而无声明时，
   视为增强不可用，直接使用下方内置模板。
3. 增强调用不可用、返回失败或输出不合格（缺六项检查、泄漏 Tasks Owner 运行态键/控制块、把
   父 FR/milestone 套成完整 Work Item）时，丢弃增强结果并立即回退内置模板；不能仅因增强失败
   标记 `planning_not_ready`。
4. 增强不可用时，readiness 门禁仍按六项检查和 GitHub truth 独立判定；catalog enhancement 是
   可选的，readiness 门禁本身不是可选前置依赖。

## 内置最小模板

仅安装 `tasks-owner` 时，用以下结构输出可复制 Issue 草案或修订建议。只填已确认的规划事实；
未知关系写 `待确认`，不要编造 URL/编号：

```text
Readiness: ready | planning_not_ready
Missing: <缺失项或冲突事实>

Title: <可行动的结果标题>
Outcome / User value: <最终结果和用户价值>
Context / Entry points: <milestone、父 FR、Issue、代码/文档入口和现状证据>
Done when / Acceptance:
- <可观察的完成标准和失败/不可用状态>
Scope: In <范围>; Out / Non-goals <边界>
Dependencies / Constraints: <hard/soft/convergence 依赖和约束>
First-slice proof (required for infrastructure/security/platform hard blocker; every field is required):
first_consumer: <第一个真实消费者；可回读 locator>
smallest_consumer_verifiable_increment: <最小可观察产品结果>
hard_dependency_proof:
  - dependency: <locator>
    unsafe_to_start_without: <安全开始反事实>
    fixture_or_recorded_contract_insufficient_because: <为何固定证据不能先跑薄切片>
    residual_integration_boundary: <仍需真实上游的边界；无残余则写 none>
deferred_boundary: <与 residual_integration_boundary 对应的延期完备性；无延期则写 none>
Verification evidence:
- Check: <准确命令/产物/外部状态>; Success: <具体通过判据>
Pause / Decision conditions: <暂停条件和决策者>
Planning metadata:
- parent: <FR/Issue 或待确认>
- milestone: <milestone 或待确认>
- blocked-by: <Issue 列表、none 或待确认>
```

## 与运行态合同分离

Issue 草案和修订建议不得把 Tasks Owner/Codex 的运行时编排或 admission 元数据当作 Issue
合同字段。禁止的是明确的运行态键或控制块，例如 `owner_thread_id`、`task_thread_id`、
`workspace_entry`、`owner_runtime_lock`、`contract_revision`、`contract_digest`、
`execution_generation`、`event_key`、`execution_hold`、`<control>`，以及带运行时命名空间的
`model`、`agent`、`subagent`、`thread`、`worktree`、`cwd` 或 head 值（例如 `runtime.model`、
`admission.worktree`）。这些词本身不构成禁词：产品域目标、代码/接口术语、验证对象或用户
明确要求的功能可以正常使用它们。Issue 只表达规划事实、范围和证据；tasks-owner 在 admission
合同中另行补充运行态字段，不能把合同复制回 Issue。

父 FR/milestone 只需保留 `Intent / Value`、子 Work Item/exit signal 和已知约束/依赖；除非
用户要求父项本身可执行，否则不强制六项完整结构。

## 结果处理

- `planning_not_ready`：列出缺失项、事实定位和最小修订建议；始终禁止该 Work Item 的
  implementation admission/派发。若 `confirmed_owner_authority` 已明确包含 GitHub planning writes，
  Owner 可把它归为 `owner_actionable`，直接修订/创建 Issue 后重跑本门禁；否则保持只读并请求相应
  授权或产品决策。
- `ready`：列出六项检查与 GitHub truth locator；把结果交给后续 runtime/admission gate，
  不把 ready 当作已派发或已获得写入权。
- 任何“用户授权写 GitHub”的请求仍需单独回读目标、动作范围和可验证结果；readiness 本身
  不扩大权限。

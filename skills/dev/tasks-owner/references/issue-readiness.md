# Work Item Issue readiness 门禁

这是 `tasks-owner` 内置、可独立安装的规划门禁。它只判断 GitHub Work Item Issue 是否足以
进入后续 Owner admission，不替代 GitHub truth、运行态合同、审查或 closeout。`write-a-goal`
的 `github_issue` 是可选增强；缺失时本文件的模板仍必须可工作。

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

## 六项最小检查

Work Item 必须为每项提供短而可验证的证据；缺项标记 `planning_not_ready`，并输出最小修订建议：

| 检查 | 通过条件 | 常见缺口 |
|---|---|---|
| 目标/价值 | 说明要达到的最终结果，以及用户/项目为什么受益 | 只有“实现/处理/优化”动作，没有结果或价值 |
| 可验证完成 | 有可观察的 acceptance/done when，覆盖成功、失败或不可用状态 | “完成后看起来正常”“没有问题” |
| 范围边界 | 明确 In、Out/non-goals，以及允许触碰的文件/模块/外部对象 | 任务可无限扩张，未说明不做什么 |
| 依赖约束 | 列出 hard/soft/convergence 依赖和兼容性、安全、数据、权限、成本等约束 | 把未知依赖当作已解除，或漏写安全/权限边界 |
| 验证证据 | 每条检查有准确命令/产物/外部状态和 concrete success criterion | 只有“已测试”或没有证据定位 |
| 暂停/决策 | 明确缺事实、权限、语义、产品/安全决策或重复失败时暂停，并写明决策者 | 缺口出现时继续猜测或自动写入 |

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

- `planning_not_ready`：列出缺失项、事实定位和最小修订建议；保持只读，禁止 admission/派发。
- `ready`：列出六项检查与 GitHub truth locator；把结果交给后续 runtime/admission gate，
  不把 ready 当作已派发或已获得写入权。
- 任何“用户授权写 GitHub”的请求仍需单独回读目标、动作范围和可验证结果；readiness 本身
  不扩大权限。

# Unit Owner 准入、消息与收口合同

本文件只定义 Unit Owner 的运行接口。目标循环见 [operations.md](operations.md)，跨 Skill 稳定字段见
[dev-orchestration-contract.json](dev-orchestration-contract.json)，平台参数见 [codex-app.md](codex-app.md)。

## 权限与跨 Skill 合同

Owner 原样保存用户明确授予的动作、排除项和独立 Automation 授权；缺失或含糊的动作保持只读。
PMO admission、Owner mandate、Unit/convergence 身份、稀疏增量与反馈 schema/capability 只使用机器合同，不复制第二份 schema。

PMO admission 只改变 `authority_origin`。Owner 只发送合同允许的 `owner_sparse_delta`；commit、测试、普通
review、Heartbeat 和线程活性留在 Unit 内。反馈候选与产品增量正交，checkpoint 仅保留：

```text
skill_feedback_candidate_locator
feedback_fingerprint
feedback_issue_locator
last_occurrence_locator
feedback_status: none | candidate | deduped | submitted | deferred_private
next_action
```

## 准入

新建或恢复执行先进入只读 hold，只回报真实任务 locator、正式工作树、branch/head 和运行证据。完整合同至少包含：

- Owner/任务与稳定 Unit、scope、planning truth、product exit、governing invariant、convergence chain locator；
- 用户价值、目标、非目标、验收、依赖、允许/禁止写入、共享载体和 target head；
- 执行模式、任务运行 profile、权限边界、系统性闭包状态（适用时）和验证命令/成功判据；
- 消息返回路线、合同 revision/digest、PR Ready 门禁和证据 locator。

用户直接委任可以先激活 Owner，由 Owner 只读同步事实并塑形 Unit；这一步不等于 writer 已准入。无论授权来自用户
还是 PMO，正式 writer 准入前都必须按机器合同补齐同一 `unit_identity`：产品出口、不变量、归属边界和收敛链。
缺任一项只能继续只读塑形，不能开始写入。

Owner 与内部 Writer 的安全握手固定为：合同 → task 确认 → 路由确认 → 执行释放 → release 确认 → START → STARTED → Owner 回读。缺一步、事实错配或 START 前写入都保持待准入并隔离输出；这些内部 receipt 不上行成为 PMO gate，也不要求 PMO 逐步 ACK/PROCEED 或生成消息。App 任务与原生 Subagent 的具体投递、回读和运行参数按平台引用执行。

首次写入前必须核验：真实且不重复的任务身份；非 `main` 正式工作树；稳定 Unit/收敛链；完整合同和权限；
readiness/能力兼容；适用的系统性闭包；STARTED；写入 ownership；当前/目标 head 与运行证据。

## 双层消息

除纯握手外，Owner↔任务消息先给普通中文摘要，再给最小机器控制信息。摘要在删除控制信息后仍能说明：结论、对
产品的影响或风险、下一责任方和动作。用户最终输出不展示完整控制块。

机器事件保持稳定 `event` 和 `event_key`；投递状态单独从 local/pending 向 delivered、verified、consumed
单向推进。投递失败不得把状态拼进事件名，也不得伪造 message locator。相同事件的恢复有界；达到平台上限后保存
失败证据和恢复条件，只隔离受影响任务。

## 运行 profile 与执行单元

Owner、任务和原生 Subagent 使用平台引用中的语义 profile；任务 override 只能来自用户对具体任务的可定位授权，
并只在合同声明范围内传播。目标 runtime、工作树或 head 缺失、冲突、未知或静默 fallback 时 fail closed。

每个 generation 保留执行单元 locator、角色、是否 writer、宿主状态、写权限、观察时间、completion 与 Owner
消费状态。发布前，所有 writer 必须 terminal；只有平台能证明暂停和撤权时才可使用等价 quiesced 状态。任何新
writer 状态或 head 变化都会使旧收敛证明和审查失效。

## PR Ready 与 closeout

PR Ready 必须绑定：当前验收映射、适用的闭包矩阵、preflight ready、语义范围 aligned、writer 已结束、fresh
exact-head 独立审查、准确文件/diff、Hosted CI 和 PR metadata。审查 finding 先按 scope integrity 处置；同一
Unit/收敛链只有一次 finding 驱动写入。

Owner 只有独立回读产品验收、merge commit/target head、Issue/PR 状态、carrier 和必要 cleanup 后，才能声明
completed。PR、commit、CI 或任务 final 单独都不能证明完成。外部或不可逆动作无法自动回滚时，立即停止并交用户
决定。

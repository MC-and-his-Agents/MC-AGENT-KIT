# Tasks Owner 语义 scope integrity

本文件是语义归属、material delta、重复 blocker 和下游反向信号的唯一事实源。合同 digest、exact
head、测试、CI 和 code review 只能证明各自机械事实，不能替代本门禁。

## Unit 与收敛链身份

Unit 身份由 `product_exit_locator + governing_invariant_locator + ownership_boundary_locator` 共同确定，
并绑定一个稳定 `convergence_chain_locator`。文件、调用路径、Issue、PR、branch、head、reviewer、
blocker class 或 execution generation 变化都不能单独新建 Unit、收敛链或修复预算。

只有 product exit、acceptance、scope 或 ownership 发生有证据的实质变化，并完成
`shrink | split | reassign`，才允许形成新链；新链必须引用旧链、变化证据和新的边界。共享 governing
invariant 的多个路径默认保留在同一 Unit，Owner 对完整验收与不变量覆盖负责，不能只证明当前 diff。

## 强制时点与比较面

Owner 在首次 admission、改变目标/非目标/验收/依赖/写入边界的合同修订、`SCOPE_DELTA`、review
finding disposition、同一业务 scope 的修复回合、下游冲突、取得收敛通道或接受 `PR_READY` 前执行
review。逐项比较：

1. GitHub Issue/FR/milestone 的目标、非目标、依赖和领域归属；
2. 当前合同的目标、允许写入和技术自主边界；
3. 实际 change set 的文件、commit 意图、新增进程/包/构建入口与运行/安全边界；
4. 相邻 Work Item 的 ownership，以及当前 change set 是否反向阻塞其 ready 工作。

最小 checkpoint：

```text
semantic_scope_checkpoint: <单调递增 revision>
semantic_scope_trigger: admission | contract_revision | scope_delta | repeat_blocker | downstream_conflict | convergence
planning_truth_locator: <GitHub truth>
contract_scope_locator: <合同 revision>
observed_change_locator: <planned files 或 PR/diff/head>
adjacent_ownership_locator: <相邻 Issue/冲突事实或 none>
semantic_scope_status: aligned | shrink | split | reassign | user_decision
semantic_scope_evidence: <比较结论与证据定位>
```

只有四面事实都有可回读证据且仍服务目标/验收时才是 `aligned`。普通 head、push、CI、review、测试、
文档、fixture，或既有 ownership 内不改变公共/安全/运行边界的薄 adapter/helper，不因文件增加本身
触发 material delta。

## Material scope delta

任务发现以下任一项必须停止相关写入并上行 `SCOPE_DELTA`：

- 新增目标未声明的生产子系统；
- 跨越 native、build、signing 或 security boundary；
- 触碰另一 Work Item 负责的文件/领域；
- 相对已确认合同明显扩大实现面。

任务只能报告事实、保持相关写入 hold，不能自行批准合同扩张。Owner 回读 GitHub truth、任务线程和
实际 diff 后只选一个结论：

```text
aligned       # 仍在授权目标与 ownership 内
shrink        # 删除/回退越界 change set
split         # 保留可审计成果，创建精准 Work Item
reassign      # 退回既有正确 Work Item
user_decision # 产品含义、权限或真实业务范围必须由用户决定
```

修改摘要、标题、测试或 digest 不能单独把漂移改判为 `aligned`。受影响任务保持 hold；无冲突任务继续
ready wave。

## Review finding admission

审查意见不是修改授权。每个 finding 先记录以下结构；`severity` 只用于排序，不能单独授权
`fix_now`：

```text
review_finding_disposition:
  finding_locator: <review evidence>
  severity: <P0 | P1 | P2 | P3>
  acceptance_or_invariant_locator: <exact mapping or none>
  current_outcome_unsafe_without_fix: <true | false>
  unsafe_evidence_locator: <evidence or none>
  disposition: <fix_now | defer | reject | split | reassign | user_decision>
  carrier_locator: <required for defer/split/reassign; otherwise none>
  rejection_basis: <required for reject; otherwise none>
  user_decision_locator: <required for user_decision; otherwise none>
  boundary_expansion: <none | production_subsystem | permission_or_runtime>
```

finding 的出口影响、处理、权限和生命周期是四个正交维度；不得再用一个 `disposition` 混合表达：

```text
exit_impact: <blocks_current_exit | does_not_block_current_exit | uncertain>
treatment: <fix_now | defer_followup | reject_not_applicable>
authority: <unit_owner_authorized | pmo_authority_required | user_authority_required>
lifecycle: <pending_evidence | decided | in_progress | verified | closed>
```

既有 `disposition` 保留用于兼容历史 review 记录：`fix_now` 对应 `treatment=fix_now`，`defer`/`split`/`reassign` 进入 `defer_followup` 并引用已有 carrier，`reject` 对应 `reject_not_applicable`；`authority` 不由 severity 推导。`exit_impact=uncertain` 可暂时 hold，但 evidence 明确后必须进入 treatment/authority 路线；finding 成立本身不自动阻断当前出口。

只有同时满足以下条件才允许 `fix_now`：

- `acceptance_or_invariant_locator` 能精确映射本批 Done when/Accepted 不变量，或 `severity` 为
  `P0/P1` 且 `current_outcome_unsafe_without_fix: true` 并有 `unsafe_evidence_locator`；
- `boundary_expansion: none`，修复不新增生产子系统、不扩大权限或运行边界；
- 延期会使当前交付结果失真或不安全（`current_outcome_unsafe_without_fix: true`）。

其余 finding 默认 `defer`、`reject`、`split`、`reassign` 或 `user_decision`。`P2/P3` 不是绝对禁止
修复，但必须提供上述验收/不变量映射和延期风险；“发现了真实问题”本身不能扩大当前批次。
`defer`、`split`、`reassign` 必须写入已有权威 backlog/deferred carrier locator；`reject` 必须写明
可回读的 `rejection_basis`；`user_decision` 必须满足 operations 中的完整用户保留权证明，不能仅凭一个 decision locator 把职责内问题转给用户。
若 finding 已映射当前验收/不变量，或属于有证据的 P0/P1，且当前结果不修复即不安全，则不得用
`defer` 或 `reject` 掩盖；只能 `fix_now`、以 `shrink`/`split`/`reassign` 完成可回读的 scope/ownership
transition 后重新 review，或在确属用户保留权时进入完整 `user_decision`。仅填写 carrier 而未发生权威
transition 的 scope disposition 不能收口，更不能在原 scope/head 上得到 `SHIP`。

## Convergence-chain review-fix circuit breaker

共享 `repair_budget` 只统计首次 fresh review 后，因已 admission 的 finding 对被审 change set 发生的写入回合；一次 finding disposition 到下一次 writer quiescence + fresh review 算一轮。多个 finding 可在同一轮合并修复，不按 finding 数量计数。

```text
convergence_chain_locator: <稳定产品出口与因果链>
finding_write_limit: 1
finding_write_consumed: <0 | 1>
repair_evidence_locators: <每个已消费回合的证据>
reset_only_on: <product_exit_change | acceptance_change | scope_change | ownership_change>
```

`finding_write_consumed >= finding_write_limit` 后，禁止在同一 convergence chain 启动第二轮 finding-driven 写入。更换 Owner、reviewer、task、文件、branch、`blocker_class`、head/commit 或 execution generation 都不能重置预算；不得以“新类别问题”产生 `FIX3`/`FIX4`。

同一 governing invariant 的预算还必须绑定 `convergence_chain_locator`；即使 task key 或 scope revision
因机械路径变化而不同，只要产品出口、不变量和 ownership 未变，仍沿用同一已消耗预算。

只有 fresh review 中当前 finding 已明确 disposition 为 `shrink`/`split`/`reassign`，且没有待复审写入时，才允许切链。切链同时记录 trigger finding、旧/新 convergence chain、task/scope revision、语义变化证据和绑定新链且 `consumed=0` 的 `to_repair_budget`；切链后必须重新 fresh review。`reassign` 还必须绑定真实 capability 或 ownership mismatch locator；换 Owner 本身不构成新链。剩余问题按以下路径处理：

- P0/P1 且确实阻断当前验收：`shrink`、`split` 或 `reassign`，进入新的 `task_key`；
- P2/P3 或无当前验收映射：`defer`/`reject`；
- 需要改变产品、权限或运行边界：`user_decision`。

这条 generation-wide 门禁与 exact-head、writer quiescence、independent review、CI 和 cleanup 门禁
相互独立，不能由其任一证据替代。

### Product-exit convergence chain

修复预算必须绑定同一条 `convergence_chain_locator`：

```text
product_exit_locator: <Parent/产品出口>
convergence_chain_locator: <产品出口 + finding 因果链 + scope>
finding_write_limit: 1
finding_write_consumed: <0 | 1>
repair_evidence_locators: <已消费修复证据>
reset_only_on: <product_exit_change | acceptance_change | scope_change | ownership_change>
```

新 Issue、Owner、reviewer、branch/head 或 execution generation 不能重置该链。只有证据充分的 product exit/acceptance/ownership/scope 改变，并实际完成 `shrink`、`split` 或有 mismatch 证据的 `reassign`，才开始一条新的收敛链；这不是对原链的预算重置。熔断仅停止未经裁决的范围扩张，不削弱已证明的质量门禁。

## 下游反向信号

下游 ready Work Item 因上游 locator/ownership 无法 admission 时，不得只记录 write conflict 让下游
等待。Owner 立即反查上游目标、非目标、实际 locator 和相邻 ownership；若上游越界，执行 `shrink`/
`reassign` 并释放下游；只有有权威依赖证据且 ownership 合法时，才把阻塞保留在具体 task。全局 cap
不变。

# Tasks Owner 语义 scope integrity

本文件是语义归属、material delta、重复 blocker 和下游反向信号的唯一事实源。合同 digest、exact
head、测试、CI 和 code review 只能证明各自机械事实，不能替代本门禁。

## 强制时点与比较面

Owner 在首次 admission、改变目标/非目标/验收/依赖/写入边界的合同修订、`SCOPE_DELTA`、同类
blocker 重复、下游冲突、取得收敛通道或接受 `PR_READY` 前执行 review。逐项比较：

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

## Repeat-blocker circuit breaker

同一已分类 `blocker_class` 在一次定向修复后再次失败就进入 review；若两次修复/验证都有证据仍失败，
禁止第三次局部补丁，必须重新分类并 `split`、`reassign`，或在确有产品/权限决策时请求用户。不得
因“再试一次”隐藏根因；其他无冲突任务继续推进。

## 下游反向信号

下游 ready Work Item 因上游 locator/ownership 无法 admission 时，不得只记录 write conflict 让下游
等待。Owner 立即反查上游目标、非目标、实际 locator 和相邻 ownership；若上游越界，执行 `shrink`/
`reassign` 并释放下游；只有有权威依赖证据且 ownership 合法时，才把阻塞保留在具体 task。全局 cap
不变。

# Unit Owner 调度与收敛

本文件是执行模式、容量、稳定身份、紧密批次、拆分和 stacked convergence 的唯一权威来源。

## 紧密批次与依赖

共享 product exit、governing invariant、写入载体、验证矩阵和 closeout lane 的工作默认组成一个 tight batch。
只有独立用户价值、独立风险/权限/数据边界、独立 ownership、真实 hard dependency 或独立回滚证据，才支持拆分。
不得为填容量制造空任务，也不得把整个 milestone 变成超级任务。

依赖只分为：

- `hard`：不满足就不能安全开始；必须说明安全开始反事实、fixture/recorded contract 为何不足和残余集成边界；
- `soft`：只影响优先级或信息；
- `convergence`：只阻最终 merge、认证或 closeout。

`blocked-by`、父子、同 milestone 或同 target 不自动成为 hard。能以 fixture、只读准备或隔离载体安全先行的薄切片
先执行，只有残余集成保留 hard。

## 执行模式

```text
execution_mode_selection:
  mode: direct | flat | hierarchical
  independently_admissible_subunits: <locators | none>
  write_carrier_overlap: <none | shared + locators>
  acceptance_and_rollback_independence: <verified | not_verified + evidence>
  critical_path_benefit: <真实并发收益 | not_applicable>
```

- `flat`：单 writer、共享载体或统一验证/收口的默认模式。
- `hierarchical`：至少两个子单元分别 ready，写入不重叠，验收和回滚独立，并有真实关键路径收益。
- `direct`：仅用于当前 Owner 回合可持续等待并消费结果的有界工作。

具体创建、消息、等待和运行参数按 [codex-app.md](codex-app.md) 执行。模式不改变权限、单写入、审查预算或容量上限。

## Unit、任务与收敛链身份

Unit 由 product exit、governing invariant 和 ownership boundary 决定。首次准入后，稳定任务身份与
`convergence_chain_locator` 绑定该 Unit；路径、文件、Issue、PR、branch、head、reviewer 或 generation 变化不能
单独新建身份或重置预算。目标或 ownership 实质改变时，先按 scope integrity 完成 shrink/split/reassign。

## 容量与就绪波次

`resolved_max_inflight = min(host_cap, user_cap)`；缺一取另一，两者都缺时采用宿主默认。Owner、任务、风险和
故障不能自行降低它。分别记录实现目标、真实已准入实现、只读/review、待准入和收敛 lane；计划数、线程占用、
readiness 或 review 不算实现进展。

每周期从最新验收矩阵选择所有无冲突且可准入的 ready 工作，直到容量用尽。每个未选项都要有具体依赖、载体冲突、
权限缺口或恢复条件。目标未完成、容量大于 1 但健康关键路径只有一条时，不因 `width=1` 反复审计；只有产品/使能
进展停滞或既有不可并行证明失效时，才重分类依赖、形成并行薄切片或更新逐项不可并行证据。

## 阶段性收敛

同一 governing invariant 默认一个 tight batch。确需多个 PR 时，开始前固定 stack order、累计验收/不变量矩阵、
证据失效规则和最终 exact-main convergence point；每层必须有独立价值、ownership、真实 hard dependency 或独立
回滚证据。上游 head 前移后，所有绑定旧 head 的 preflight、review 和 CI 按计划重跑。

同一仓库和 target 的收敛 lane 默认单一，但不阻塞无冲突实现。merge、closeout 或依赖解除后，同周期重算并启动
已 ready 的后继；共享载体、残余 hard 或 exact-main 未释放前，只做只读 readiness，不提前创建正式 writer。

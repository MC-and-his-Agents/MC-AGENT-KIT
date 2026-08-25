---
name: pmo
description: 在用户明确委任的单一 GitHub 仓库中，以产品结果为首要责任编排多个独立 Unit Owner：维护交付前沿、关键路径、依赖、范围和产品出口，并在每个增量完成后推进 successor；跨仓库协调、单一交付单元内部执行、普通项目管理和一次性实现不使用本 Skill。
metadata:
  version: "0.6.0"
---

# PMO

PMO 负责跨交付单元的全局交付控制；Unit Owner 对单个交付单元端到端负责。PMO 把用户已经确认的目标推进到可验证的产品出口，但不因为拥有工具、Issue、Heartbeat、handoff 或历史动作就取得新的权限，也不引入组织汇报或人员管理层级。

全局只保留两个长期角色：PMO 和 Unit Owner。Writer、Reviewer、Cleanup 是 Unit Owner 为一个交付单元临时采用的内部拓扑，不是 PMO 的下属角色，也不单独获得全局 Owner 身份。

## 责任优先级

每轮都按以下顺序判断，并在同一控制周期内完成能做的动作：

1. **先推进产品目标。** 从总体目标最近未完成的产品步骤出发，选择能直接缩短差距的安全、非空、可独立验收增量。
2. **再维护有效交付前沿。** 让每项验收都有唯一归属、真实依赖、清楚的 carrier 和下一解锁条件；动态并发宽度是前沿的派生结果，不是绩效目标。
3. **最后证明等待成立。** 只有没有安全可行的仓内动作时，才逐项证明 `external_blocked`、用户决策或已有任务等待，并记录责任方和 wake condition。`zero-width proof` 不是默认状态，也不能用“暂时没有任务”代替。

用户不是日常审批节点。只要动作在用户确认的仓库、目标和权限边界内，PMO 应自主完成塑形、路由、依赖纠偏和交付取舍；产品语义、优先级、重大成本或风险、权限/数据边界及不可逆外部结果超出既有权威时，才保留给用户。

## 两个长期角色与决策边界

| 角色 | 自主负责 | 不负责 |
|---|---|---|
| Unit Owner | 一个 Work Item 的目标、范围、常规工程、review finding、PR、merge、closeout 和 cleanup；内部按当前 `$tasks-owner` 执行 | 其他 Unit 的 carrier、仓库级 DAG、全局 WIP 或产品优先级 |
| PMO | FR 到 Work Item 的覆盖、产品出口、跨 Unit DAG、关键路径、WIP、依赖重分类、范围熔断和跨 Unit 取舍；为无主范围塑形并创建或唤醒唯一 Owner | Unit 内 Writer/Reviewer/Cleanup 的调度、审批 Owner 的内部实现、替代产品或工程组织的专属权力 |

决策边界只有三级：

- **Unit 内：** Unit Owner 自主处理常规工程、测试、review、PR、merge 和 closeout。
- **跨 Unit：** PMO 处理交付单元归属、共享 carrier、关键路径、WIP、依赖、范围风险和交付取舍；只暂停冲突 carrier，不冻结无冲突路径。
- **用户权威：** 只有新产品含义、优先级变化、重大成本/风险容忍度、权限/数据边界或不可逆外部结果需要用户决定。

PMO 可以提出建议，但不能把建议伪装成用户批准，也不能把用户决策边界扩展为 standing authorization。

## 产品结果控制循环

对用户消息、Heartbeat、Owner 高层事件、GitHub 变化、merge、交付单元完成、Owner terminal 和运行时异常，执行同一循环：

1. **同步真实事实。** 回读 milestone、FR、Issue、parent/sub-issue、blocked-by、PR、target head，以及活动 Owner 的真实 thread、runtime、worktree 和状态。实时 GitHub/线程事实覆盖旧 handoff 和摘要。
2. **定位最近差距。** 把每项验收映射为“用户结果、已验证证据、已交付增量、剩余差距、下一可执行步骤”；区分 `产品进展`、`使能进展` 和 `工程活动`。
3. **分类并行动。** 逐条判断 `execution_ready`、`owner_actionable` 或 `external_blocked`。对 owner-actionable 差距立即塑形、修订依赖、修复归属或唤醒 Owner；对 ready 单元创建唯一 Owner；不能用 `ready=0` 或 `next_actor=external` 跳过分类。
4. **维护交付前沿。** `blocked-by` 只有在证明“不满足就不能安全开始”时才是 hard；能用 fixture、recorded contract、只读准备或隔离 carrier 安全先行的部分应释放，只有真实残余集成保留 hard。只阻 merge、认证或 closeout 的关系标为 convergence，不得错误阻塞前置实现。
5. **立即推进 successor。** merge、交付完成或依赖解除后，核验真实 head、验收和剩余差距，在同一周期重算 DAG、ready wave 和下一项可执行增量；不能把 successor 留给下一次 Heartbeat。
6. **收口或证明等待。** 若目标未完成且没有实施槽，先重新同步并通过 zero-width proof；不得创建空 Issue、空 Owner、重复审计或无消费者价值的工作。只有所有剩余差距都有具体等待证据时才可安静。

## 进展证据层级

- **产品进展：** 直接满足产品出口的一项真实条件，或让产品结果进入下一真实阶段，并有产品或用户证据。
- **使能进展：** 解除下一产品步骤的真实 hard dependency、决策、风险或 blocker；必须明确指出它解锁的产品步骤。
- **工程活动：** commit、PR、测试、review、Issue、Owner/线程和协议动作；只有能映射到产品进展或使能进展时，才算交付进展。

如果工程活动连续发生却没有产品进展或使能进展变化，PMO 必须检查范围漂移、非阻断边缘问题和最短产品验证路径，并按需执行 `CORRECT_DRIFT`。

每个动作都必须能说明它如何缩短产品差距或解除使能阻塞。PR 数、测试数、review 数、关闭 child 数、协议握手和文件数只能证明工程活动，不能单独冒充交付进展。

## 失败模式的主动纠正

- **旧 blocker 遗漏可做工作：** 重新检查安全开始反事实和 residual boundary；不要把宽泛的上游完备性当成首个消费者的 hard blocker。
- **后阶段门禁阻塞前置实现：** 提前做依赖、能力和只读 readiness；共享 carrier 或收敛门禁未释放时记录 wake condition，但不把可独立的前置薄切片一起停掉。
- **为表现活跃制造工作：** 不为填并发制造 Issue、Owner、重复 review 或状态数据库；稳定的 width=0 必须留下逐项不可并行或外部等待证据。

## 授权、runtime 与协作边界

开始任何仓库级动作前，只按用户明确的仓库、目标、规划写入、关系写入、路由和纠偏权限行动；缺失授权不由 Skill、Issue 或 Heartbeat 补造。PMO 与独立 Owner 默认使用 `gpt-5.6-sol/high`，禁止静默 fallback；实际 runtime 必须按当前 `$tasks-owner` 规则回读核验。Owner 的 branch、worktree、admission、review、merge、closeout 和 cleanup 由 `$tasks-owner` 管理，PMO 不复制其内部合同。PMO↔Owner admission locator 与 sparse-delta 字段细节由 `$tasks-owner` 的 contracts/scope-integrity 承载；PMO references 只保留全局判断、locator 和短状态。

直接 canonical event 到达时立即触发增量审计；周期 Heartbeat 先读取 source cursor、pending receipt、invalidation 和 due sentinel，按 [automation.md](references/automation.md) 机械选择 Fast、Affected-slice 或 Deep，再进入本控制循环。Heartbeat 不是事实源，也不因普通唤醒重复全量核验。Skill 只有被激活、locator/digest 改变或 Skill evidence 失效时才完整重读；仍需记录 skill digest、runtime/truth 状态并按影响范围 fail-closed。根据当前任务读取所需参考：

- Owner 创建、唤醒、恢复和 terminal：阅读 [owner-lifecycle.md](references/owner-lifecycle.md)。
- Work Item 塑形、依赖、ready wave、carrier 和关键路径：阅读 [delivery-dag.md](references/delivery-dag.md)。
- Owner 高层事件的边界、receipt、语义增量、人类/机器投影和通知路由：阅读 [event-contract.md](references/event-contract.md)。
- Heartbeat、checkpoint 和 handoff：阅读 [automation.md](references/automation.md)。

这些 reference 是协议和 schema 的唯一细节来源；主 Skill 只说明判断与行动，不复制事件、DAG 或 Heartbeat 字段表。

## 控制结论

每个控制周期只选择一个主结论并立即执行对应动作：

- `KEEP_CURRENT`：活动 Owner 健康、关键路径未变、没有新的 execution-ready 无主单元，且所有剩余差距都有等待证据。
- `ROUTE_INFO`：真实 head、依赖、验收或 Owner 事实变化，但无需改变拓扑；把影响精确路由给相关 Owner。
- `SHAPE_WORK_ITEMS`：已确认的 FR 验收尚无有界 Work Item；在规划权限内塑形，完成前不创建 Owner。
- `CREATE_OR_WAKE_OWNER`：存在 execution-ready 且无唯一 Owner 的交付单元，或既有 Owner 对可执行高层动作失去连续性。
- `CORRECT_DRIFT`：发现重复 Owner/写入者、依赖环、范围/归属/runtime/truth 漂移或非必要等待；只修正受影响 lane。
- `ESCALATE_USER`：只有产品范围、优先级、重大成本/风险、权限/隐私/数据、破坏性动作或权威事实无法裁决时使用。
- `CLOSEOUT_AND_RECOMPUTE`：增量 merge、交付单元完成或 Owner terminal 已被实时事实核验；收口该增量并立即重算 successor，不把 PR merge 当作 Parent 或 Owner 完成。

结束周期前确认：Skill、GitHub truth、target head、Owner runtime/scope、验收归属和事件 receipt 均可回读；无未处理跨 Unit 冲突、无可立即执行的 owner action 或 successor；若目标未完成，剩余差距都有逐项等待证据。只有通过这些检查，PMO 才可以保持静默。

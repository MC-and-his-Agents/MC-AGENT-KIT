# 交付单元 DAG

在塑形 Work Item，或同步依赖、Owner 归属、ready wave、fan-out、跨 Owner 冲突时读取。

## 内容

- 图模型
- FR 覆盖与 Work Item 塑形
- 重建流程与依赖维护
- 冲突、环与 fan-out 处理
- 增量、完成与 terminal

## 图模型

本图只覆盖 checkpoint 中 `repo_locator` 指定的单一仓库；跨仓库依赖不由本 Skill 编排。用最小恢复索引描述每个交付单元：

```text
delivery_unit:
  task_key: <稳定 Issue/FR/batch locator>
  scope_locator: <权威规划事实>
  acceptance: <首个消费者可观察结果>
  owner_thread_id: <活动 Owner 或 none>
  owner_status: <initializing | active | recovering | terminal | none>
  target_ref: <仓库级目标 ref>
  verified_head: <该单元最后同步的目标 head>
  write_carriers: <准确共享文件/模块/外部对象>
  dependencies: <hard | soft | convergence + locator>
  capability_compatibility: <compatible | missing | incompatible | provided_by_current_batch | not_applicable + locator>
  execution_mode: <direct | flat | hierarchical + selection evidence locator>
  readiness: <planning_not_ready | execution_ready>
  frontier_classification: <execution_ready | admission_pending | active_execution | waiting_external |
    waiting_user | replan_or_reownership_pending | closeout_pending>
  pmo_admission_contract: <tasks-owner contract locator>
  owner_sparse_delta: <canonical event/evidence locator or none>
  parent_outcome: <Parent/Milestone exit evidence locator + short status>
  remaining_executable_surface: <short status + evidence locator>
  convergence_chain: <product exit/finding budget locator>
  next_unlock: <candidate + wake condition locator>
  next_event: <事件或 wake condition>
```

不要在 DAG 中复制完整 Issue、日志、合同、prompt 或任务内部状态。GitHub/项目规划事实和实时线程状态始终是权威来源；checkpoint/handoff 只能索引这些事实。`pmo_admission_contract`、`owner_sparse_delta`、`convergence_chain` 和 `next_unlock` 只存 locator/短状态；Unit 内字段细节以 `$tasks-owner` 的 contracts/scope-integrity 为唯一来源。

## FR 覆盖与 Work Item 塑形

在创建 Owner 前，先审计用户委任范围内的 FR 验收是否由有界 Work Item 承载：

1. 默认规划 horizon 为当前执行波次加一个下一解锁波次；用户可明确扩大。已 execution-ready 的独立单元不等待 lookahead 塑形。下一解锁事实稳定时可提前完成 Issue shaping、依赖与只读 readiness；共享 carrier、未解除 hard dependency 或未核验 target head 仍禁止正式 execution branch/worktree、Owner 或 writer START。
2. 每个 Work Item 必须有单一消费者可观察结果、验收、范围/非目标、验证面、权威输入、准确依赖和可归属 carrier。不要把内部 task、review round 或未来实现猜测拆成 Issue。
3. 使用当前 `$write-a-goal` 的 `github_issue` 模式或仓库等价模板；Parent FR 保持轻量，运行态合同留给 `$tasks-owner`。
4. 事实足够且有 `planning_writes` 时创建、修订或拆分 GitHub Issue；缺少写权限时输出同等精度的草案。事实不足时标记 `planning_not_ready`，记录缺失事实、decision owner 和 wake condition。
5. 已有 Owner 范围内的 Issue shaping 归该 Owner；编排者只处理无主 FR、跨交付单元边界和关系，避免双写权威规划事实。

### 产品前沿闭包

每次重大用户纠偏、Unit merge/closeout、依赖解除、Owner terminal、waiting proof 失效、长期
`actual implementation width=1` 且产品目标未完成，或 Deep Audit 时，重新枚举全部未完成产品出口和直接 gap。
每个 gap 必须且只能进入机器合同定义的一种 `frontier_classification`，并保存 gap locator、owner/next actor、
evidence、wake 和 invalidation locator；完整 GitHub 快照仍留在 GitHub。

- `execution_ready`：安全开始条件已满足；本周期启动或形成 Unit。
- `admission_pending`：工作 ready，但缺唯一 Owner、writer admission、正式 carrier 或其他 Owner 可补齐门禁。
- `active_execution`：已有唯一 Owner/writer 正在真实推进。
- `waiting_external`：不可替代外部事实阻塞，且完整 waiting proof 新鲜有效。
- `waiting_user`：确需用户裁决产品、权限、重大风险或不可逆外部结果。
- `replan_or_reownership_pending`：旧方案/归属失效，需要塑形或恢复责任路径。
- `closeout_pending`：产品出口已满足，但 GitHub/Owner/Parent truth 尚未收口。

周期结束前必须记录 `frontier_closure_status=complete | incomplete`。只有 complete，且全部剩余 gap 都是
`active_execution | waiting_external | waiting_user` 时才允许整体等待。Issue OPEN、父项 OPEN、历史 blocked-by、
旧 handoff/next actor、旧 carrier、`ready=0` 或没有 writer 都不能单独证明等待。共享 carrier 只限制第二 writer；
只读 readiness、Unit/Owner 塑形、后继登记和 ready/admission frontier 仍须保持可见。

### 恢复期 gap classification

目标未完成且没有 admitted implementation 或 pending admission 时，对每个剩余差距只允许以下可审计分类：

- `owner_actionable`：恢复审计输入；重算后必须进入 `execution_ready | admission_pending | replan_or_reownership_pending | closeout_pending` 并产生动作。
- `external_blocked`：恢复审计输入；只有完整 waiting proof 成立后才可进入 `waiting_external`。
- `user_decision`：存在会实质改变产品范围、优先级、成本、权限、隐私、数据或重大外部结果的多个合法方向，且权威事实无法裁决。
- `waiting_task`：已有真实、唯一且仍在执行或收敛的任务 locator；计划、旧摘要或空 Owner 不成立。

`owner_actionable` 必须产生本轮规划或 Owner 动作；它不能以 `planning_not_ready`、`no stable contract`、
`next_actor=external` 或“无可并行 successor”为由进入静默。若权威验收不足以唯一约束首切，记录缺失的具体产品事实，
不要用泛化的“领域合同缺失”替代。

塑形是规划动作，不是 implementation admission，也不产生 Owner、branch、worktree 或 runtime 合同。

每个 Milestone/Parent 维护一个派生的产品闭环索引：`用户结果 → 已验证真实证据 → 已交付子切片 → 剩余差距 → external/deferred carrier → 下一可执行薄切片`。索引只保存 GitHub/证据 locator 和短状态，GitHub Milestone、Parent、Work Item、PR 仍是唯一规划事实；不得新增仓内 roadmap、状态页或第二进度数据库。PR 数、关闭 child 数、fixture/recorded-conformance 只能说明内部增量，不能替代 Parent exit。

### PMO ↔ Unit Owner 结果边界

admission 时 PMO 只通过一个可回读的 `pmo_admission_contract` locator 传递产品目标、预期贡献、验收、允许/排除范围、产品出口与收敛修复预算、Unit/PMO/用户权限边界，以及 exact-main 和证据基线。完整字段由 `$tasks-owner` 承载，PMO 不复制合同 schema。

Owner 仅在会改变全局判断时上报 `owner_sparse_delta`：实际产品效果/证据、局部 blocker 与 `remaining_executable_surface`、finding 对当前出口或跨 Unit 的影响、范围变化和 `next_unlock`。局部 blocker 仍属于该 Unit 的阶段性限制；只有无剩余可执行面且等待 PMO、外部或用户时才是全局等待。PMO 不逐条审批 Owner 的常规实现、测试、finding、PR、merge 或 cleanup，也不把这些内部步骤变成 heartbeat 表单或新的状态源。

blocker 由 Owner 用普通语言注明缺什么、阻塞 shaping/admission/implementation/verification/release/acceptance 的哪一阶段、没有阻止什么、独立安全增量、next actor 和 wake/invalidation 条件。finding 的出口影响、处理、权限和生命周期保持正交；只有跨 Unit、超收敛预算或产品出口裁决才上行 PMO，越过产品/成本/风险/权限边界才交用户。

每个准备 admission 的 Work Item 必须能由既有 Issue/readiness 证据回答：用户可观察结果、消费 seam 及语义、独占/共享 carrier、适用不变量、正负验证、完成后下一解锁条件。缺任一会影响安全开始的事实时先 shaping，不创建 Owner。

### Execution topology selection

- `flat` 是单一 writer、共享 carrier、统一验证/收口路径的默认模式。
- `hierarchical` 仅在至少两个子单元均可独立 admission、写入 carrier 不相交、各自有独立验收与回滚边界，且并发能真实缩短关键路径时使用；共享状态、共享 writer 或仅为填槽不成立。
- `direct` 只用于 Owner 当前回合可完成并可由原生 wait 消费结果的有界工作。

模式选择只描述执行拓扑，不改变全局容量、不授予额外权限，也不要求实际并发宽度大于 execution-ready、无冲突单元数。

## 重建流程

1. 回读唯一仓库范围内所有 milestone/FR/Issue、parent/sub-issue/blocked-by、PR 与 `target_ref`/`verified_head`，并记录每个必需来源的 `truth_status`。
2. 回读活动 Owner 的真实 thread/runtime/status、其声明的 delivery unit、写入 carrier、下一动作和专属 Heartbeat。
3. 按上方 planning horizon 审计 FR→Work Item 覆盖；必要时执行 `SHAPE_WORK_ITEMS`，再重新枚举全部产品出口和直接 gap，形成 complete product frontier。
4. 优先形成最小有效 tight batch：共享 carrier、验证矩阵和 closeout lane 的动作默认同属一个 unit；只有独立用户价值、风险/权限/数据边界、ownership、真实 hard dependency 或独立回滚证据才拆分。
5. 逐条重新分类依赖：
   - `hard`：缺失时连安全开始最小薄切片都不可能；必须有安全开始反事实、fixture/recorded-contract 不足理由、residual integration 与 deferred boundary。
   - `soft`：只影响优先级或补充信息。
   - `convergence`：只阻最终 merge、认证或 closeout。
6. 将可用 fixture、recorded contract、只读准备或隔离 carrier 的部分从整体 hard 依赖中释放；只保留真实 residual hard。
7. 对首个消费者依赖的既有 Core/platform/store/host seam，回读 Owner 按当前 `$tasks-owner` 形成的存在性、required/observed semantics 与最小 probe/contract evidence。`missing|incompatible` 时把差距放回 scope/dependency shaping；没有证据时不得把 writer START 算作有效 implementation。
8. 计算无 hard blocker、readiness 完整、capability compatibility 通过、无用户 hold、无 carrier 冲突且所需 truth 已核验的 `execution_ready` 单元；ready 但缺运行准入的范围进入 `admission_pending`，不得从前沿消失。
9. 按用户/宿主可回读容量选择 ready wave；未知容量不等于零，也不授权制造工作。

若 truth 为 `partial`，只重算完全落在 verified slice 内的节点和边；若为 `unavailable`，保留上次状态作为历史索引但不得据此创建 Owner、重分类依赖、转移 carrier 或声明完成。记录缺失 locator 与 wake condition，其他已核验 lane 继续。

## 依赖维护

每轮都对原生 parent/sub-issue/blocked-by 与实际 DAG 做差异审计：

- 对每条 blocked-by 写明被阻消费者、缺失产物和安全开始反事实；无法证明时不得保留为整体 hard。
- 对每条消费者→上游 seam 边写明 required/observed semantics 与兼容证据；能力缺失或不兼容且消费者 scope 不拥有该 seam 时，先 shrink/split/reassign 或塑形最窄上游 Work Item，保留消费者成果和原 review budget。
- fixture、recorded contract、只读准备或隔离 carrier 可安全开始时，把先行部分释放，真实集成只保留 residual hard；仅阻 merge/认证/closeout 的关系改为 convergence，单纯顺序或优先级不编码为 blocked-by。
- 产品出口、finding 因果链和 scope 共享同一收敛预算；不得以新 Issue、Owner 或 execution generation 重置。熔断只停止未经裁决的范围扩张，不削弱已证明的真实质量门禁。
- 关闭上游、重复边、依赖环、未来完备性阻塞当前首切或关系与 Owner/carrier 归属不一致时，判为 `CORRECT_DRIFT` 并重算 ready wave。
- 只有 `dependency_relation_writes` 已授权且 truth 已核验时才修改 GitHub 原生关系；否则输出 exact add/remove/reclassify 草案。关系修订不能顺带改写 FR/Work Item 的产品范围、优先级或验收。

## 唯一性与冲突审计

把以下情况判为 drift：

- 同一 `task_key` 或同一有界验收有两个活动 Owner；
- 两个 Owner 同时拥有同一写入 carrier；
- 上游 Owner 的范围扩入下游 Owner 已拥有的 carrier；
- Owner 线程、Issue、branch/worktree、`target_ref`/`verified_head` 或 runtime 互相错配；
- native 依赖已解除但 handoff 仍称 blocked；
- 一个 Owner 的输出反向要求另一个 Owner 依赖自己，形成跨 Owner cycle。

发现冲突时只暂停冲突 carrier，保留并路由已有成果；不停止无冲突路径。用稳定 `task_key + scope revision` 去重，不按线程标题或最新摘要去重。

## 环处理

对每条环记录 `A requires B` 的具体产物、Owner 和证据。优先依次处理：

1. 将仅影响最终集成的边改为 `convergence`；
2. 将 fixture/recorded-contract 可满足的部分改为 `soft`，保留 residual hard；
3. 把错误 ownership 重新分配给真正的首个消费者；
4. 将确有独立价值、边界或回滚证据的 carrier 拆成新 delivery unit；
5. 只有权威产品事实互相冲突且无法裁决时升级用户。

不要通过新增通用基础设施或伪造 accepted/real 事实打破环。

## 关键路径与 fan-out

`critical_path_width` 只计无冲突、可实际实施的路径；review、readiness、占槽或计划数不计实现宽度。

当目标未完成、容量大于 1 且宽度为 1 时，只有在没有产品/使能进展，或不可并行证明因新事实、TTL、sentinel 失效时，才在当轮执行至少一项：

- 重分类没有安全开始证明的 hard dependency；
- admission 独立 carrier 的首个消费者薄切片；
- 将共享 carrier 合为一个 tight batch，释放其他路径；
- 为每个候选留下具体不可并行证据和 wake condition。

“已审计”“同 milestone”“单一收敛 lane”或一般谨慎不算 fan-out 动作；并行证明仍新鲜时直接复用，不重复审计。没有真实 execution-ready 单元时不创建空 Owner。

当目标未完成且宽度为 0、admission 也为 0 时，先执行 Remaining-gap classification。存在任何
`owner_actionable` 差距即执行 shaping/Owner 恢复；只有全部差距都由逐项 external/user/task 证据覆盖时才可保持 width=0。

## 增量、完成与 terminal

三类事实必须分开处理：

- `PR_MERGED`：核验 exact merge commit、PR/Issue closing references 与 `target_ref`/`verified_head`；只收口该增量，把 head 前移影响路由给活动 Owner，并重算被该增量解除的边。Owner、Heartbeat、置顶和 unit ownership 保持不变。
- `DELIVERY_UNIT_COMPLETED`：独立核验该 unit 的 acceptance、deferred/successor 与 GitHub 状态后，释放该 unit 的依赖边并重算 ready wave；不能据此推断承载它的长期 Owner 已 terminal。
- `OWNER_TERMINAL`：按 owner lifecycle 独立核验 cleanup/保留、Heartbeat、置顶、活动 writer 与未完成目标，才从 active DAG 移除 Owner。

任一事件核验后都在同一控制周期：

1. 更新 `verified_head` 与受影响 carrier/边；
2. 把 head 前移影响路由给仍活动的无冲突 Owner，要求其在 convergence 前同步并重验，而非机械中断；
3. 重算新解锁的 execution-ready successor；
4. 创建/唤醒唯一 Owner，或记录具体未选证据。

truth 未核验时保持事件 receipt 未消费，不做上述状态变更。

# Owner 生命周期

在创建、唤醒、恢复、去重或关闭独立 Owner 时读取。Owner 的内部执行始终交给 `$tasks-owner`。

## `tasks-owner` 依赖门禁

首次执行 Owner 生命周期动作前，必须先完成主 Skill 的依赖检查：

1. 从当前可用 Skill 清单发现名称精确为 `tasks-owner` 的 Skill；
2. 读取其当前 `SKILL.md` 和唯一的 `references/dev-orchestration-contract.json`，确认合同版本及全部必需 capability；
3. 缺失或不兼容时停止本节全部写入与生命周期动作，回到仅分析模式；
4. 只有当前请求确实需要执行时才询问安装或更新，且必须取得用户明确同意；
5. 缺失时只从主 Skill 记录的可回读发布源安装；已有但不兼容时不调用会拒绝覆盖的 `$skill-installer`，而是请用户通过原安装方式更新；
6. 安装或更新后重新执行前两项，兼容性通过前不得创建、唤醒、恢复或接管 Owner。

不要复制 `$tasks-owner` 的内部合同，也不要为这项检查建立新的依赖数据库。当前请求和安装状态没有变化时复用检查结论，不在每次 Heartbeat 重复询问。

## 生命周期状态

```text
absent -> initializing -> active <-> recovering
initializing/active/recovering -> retiring -> terminal
```

- `initializing`：真实 Owner thread 已创建，范围/runtime/authority 正在回读，尚未宣称 active。
- `active`：Owner 的范围、runtime、专属状态和当前 delivery unit 可回读。
- `recovering`：Owner 正处理陈旧 approval、丢失事件、重复 locator、runtime/scope drift 或连续性中断。
- `retiring`：Owner 已停止接收新工作并撤销写入路由，正在完成 Heartbeat/置顶等展示收口。
- `terminal`：Owner 因 `completed|cancelled|superseded` 退出活动 DAG，交付或保留事实和展示收口均已独立核验。

## 创建

同时满足以下条件才创建 Owner：

1. delivery unit 有真实、已塑形的有界 Work Item/Issue、可观察验收和权威 scope locator；Parent FR 只有自身满足同等门槛时才可直接承载；
2. 已为 `execution_ready`，而非 `planning_not_ready` 或仅有空余容量；
3. 不存在同 `task_key`/验收的活动 Owner；
4. 写入 carrier 与其他 Owner 不冲突；
5. 用户授权覆盖创建/唤醒 Owner；
6. 编排者 runtime 与创建所需 GitHub/宿主 truth 均已核验；
7. Owner runtime 使用用户有效 override；没有 override 时使用 Codex App 引用中的 `owner_runtime_profile`，禁止 fallback，并回读目标运行证据。
8. `tasks-owner` 依赖门禁已通过，当前模式为完整模式。

创建后把以下内容交给 Owner：唯一 `repo_locator`、`target_ref`/`verified_head`、scope locator、confirmed authority、相邻 carrier ownership、已验证 hard/soft/convergence 边界、本 Skill 的高层事件合同，以及“内部按当前 `$tasks-owner` 执行”。不要替 Owner 生成 task admission 合同。

### Admission 与稀疏结果回报

PMO admission 严格使用 `$tasks-owner/references/dev-orchestration-contract.json` 的
`pmo_admission` envelope。PMO 只保留合同 locator、版本、能力核验结果和短状态，不维护第二份 schema。

Owner 对 PMO 只按同一机器合同的 `owner_sparse_delta` 上报改变全局判断的事实。常规实现、测试、finding
处置、PR、merge、closeout 与 cleanup 由 Owner 自主完成，PMO 不逐条审批，也不管理其临时
Writer/Reviewer/Cleanup。

普通 Unit 的 PMO 可见控制路径只有一次 `pmo_admission` 和一次 `unit_completed`；中间只有改变 acceptance、scope、ownership、DAG、用户权限边界或真实 material risk 的 `owner_sparse_delta` 才上行。ACK、release、START/STARTED、commit、测试、review-fix、CI、PR、branch/head 和无变化 Heartbeat 都留在 Owner 内部，既不是 PMO gate，也不产生 PMO 人类消息。

blocker 必须用普通语言标明缺什么、阻塞 shaping/admission/implementation/verification/release/acceptance 哪一阶段、未阻塞什么、独立安全增量、next actor 与 wake/invalidation 条件。局部 blocker 仍由 Owner 在剩余可执行面内推进；只有没有剩余可执行面且等待 PMO、外部或用户时才路由为全局等待。finding 的 `exit_impact`、`treatment`、`authority`、`lifecycle` 正交记录；跨 Unit、超预算或出口裁决交 PMO，越过产品/成本/风险/权限边界交用户。

PMO 分别消费 product、merge、release readiness，不用一个 Hosted 结果覆盖三层。验证权威按用户、Issue acceptance、最近仓库规则、Skill 默认解析；只有 effective authority、branch protection、release 或 security 合同要求的 Hosted check 才阻塞相应层。无关基线失败进入独立 backlog，不回滚已核验产品增量。

Owner 标准标题为 `【Owner】<仓库简称>｜<能力域>｜<交付结果>`：仓库简称取 `repo_locator` 的仓库名或用户指定别名；能力域与交付结果使用简短、可辨识的业务表述，不写 runtime、临时状态或内部 task 名。

若宿主支持且 Owner 创建授权涵盖对应可逆展示操作，在 `initializing -> active` 前设置并回读标准标题、置顶，并创建绑定真实 thread 的专属 Heartbeat。标题、置顶或 Heartbeat 与期望不一致时保持 `initializing` 并 `CORRECT_DRIFT`；能力不可用或未授权时记录 `unavailable|unauthorized`，不得虚报已完成，但纯展示能力不作为产品 hard blocker。内部 task/writer/reviewer/cleanup 不使用 Owner 标题且不得置顶。观察 Heartbeat 不替代 Owner Heartbeat。

Owner 的专属 Heartbeat 每次唤醒也应先加载当前 `$tasks-owner` 并核验自身 actual runtime；观察 Heartbeat 仍负责对所有活动 Owner 做仓库级巡检。

## 唤醒与路由

使用真实 `owner_thread_id` 和 Owner 自身已核验 runtime 精确投递。读/等工具不构成投递；发送前 payload 不含 locator，只有发送工具成功返回并写入 sender delivery record 后才可声称已投递。Owner 是否已消费只能由接收方 receipt/readback 证明。

只在以下情况唤醒：

- delivery unit 新变为 execution-ready；
- `verified_head`/PR/依赖变化会影响其 carrier 或收敛；
- 高层事件尚未被 Owner 消费；
- 已授权动作陷入非必要 waiting、approval 或 idle；
- cross-owner 冲突、cycle、runtime/scope drift 需要该 Owner 处理；
- merge/terminal 后必须立即重算 successor。

普通 `STARTED`、Owner 内部合法 fix、健康 active 状态或重复事件不唤醒。

不因普通局部 blocker、常规 finding 或内部进度唤醒 PMO；仅在 sparse delta 改变跨 Unit/DAG、产品出口、收敛预算、范围归属或 next unlock 时路由高层事件。

编排者 runtime 未核验时不发送唤醒；目标 Owner runtime 未核验时隔离该 lane，不发送写能力动作、不消费其事件、不转移 carrier。公开 metadata 与 allowlisted 本机证据冲突时 fail closed，不 fallback 或修改配置。

## 恢复 runtime 异常

实际 model/reasoning 与有效用户 policy 不符或证据无法核验时：

1. 标记 `RUNTIME_LOCK_ANOMALY`，将原 Owner 置为 `recovering` 并只隔离该 lane；保留 thread、carrier、branch/worktree 和成果。
2. 仅当 `runtime_recovery` 已授权且宿主提供可核验的原生 runtime-targeted wake/retry 时，精确恢复同一 `owner_thread_id`；禁止新建替代 Owner、fallback 或改宿主配置。
3. 新目标 turn 的 actual metadata 符合 desired runtime 后才恢复事件消费、写能力路由和 closeout；恢复请求或 Owner 自报本身不能证明成功。
4. 无恢复机制或恢复失败时报告 runtime evidence、缺失能力和 wake condition；其他已核验 Owner lane 继续。

## 恢复 owner-actionable 停滞

已授权 in-scope 动作进入 `waitingOnApproval`/`waiting_user` 时：

0. 先比较持久 canonical disposition/cursor/generation 与当前 checkpoint；较新的 terminal、RETHINK、SHIP、interrupted 或 scope-violation 立即淘汰旧 active/waiting，禁止诊断、替换、中断或读取冻结 carrier。Owner 静默和 direct delivery 丢失都不能证明 Owner 仍 active 或已经失败；冲突最多一次定向回读，并在同周期重规划受影响闭包。

1. 判为 `CORRECT_DRIFT`，不是用户决策；
2. 精确唤醒对应 Owner，而不是直接操作其 task；
3. 要求 Owner 按 `$tasks-owner` 保留 branch/worktree/未提交成果，核验陈旧 locator，隔离或撤销重复写权，并重新 admission 唯一执行单元；
4. 回读新 task locator、正式 worktree、write authority 和 START/active 事实；
5. 已恢复时不重复中断。

“没有可并行 successor”不免除这项恢复责任。

## 去重与归属

- 在委任的单一仓库内以 `stable task_key + scope revision` 识别 delivery unit，以真实 threadId 识别 Owner。
- 发现重复 Owner 时选择范围/runtime/authority/实时状态均可验证的 canonical Owner；冻结未获写权或较新的重复单元，保留证据并路由给 canonical Owner。
- 被取代的重复 Owner 转为 `retiring`，撤销写入与事件路由、暂停专属 Heartbeat并取消置顶；核验后以 `terminal_reason=superseded` 结束，不能只冻结线程却保留活动展示。
- 发现重复 writer 时不在编排层挑选文件级修复；暂停冲突 carrier并要求各 Owner报告 ownership，其他 carrier 继续。
- 不复用 terminal Owner 承担新的独立 delivery unit；新 unit 建新 Owner，除非用户明确规定长期同域 Owner。

## 取消或 supersede

用户明确撤销 Owner，或去重审计选出 canonical Owner 后：

1. 将目标 Owner 置为 `retiring`，停止新工作并撤销写入/事件路由；保留成果，不把撤销解释为删除授权。
2. 暂停或删除其专属 Heartbeat并取消置顶；不置顶替代 task 或内部线程。
3. 回读 thread、Heartbeat、置顶与 ownership；全部收口后记录 `terminal_reason=cancelled|superseded`，移出活动 DAG并重算 successor。
4. 展示收口无法核验时保持 `retiring` 并记录缺失 locator/wake condition，不虚报 terminal，也不影响无冲突 Owner。

## Terminal

`PR_MERGED` 只代表一个增量进入 `target_ref`，不能暂停 Heartbeat、取消置顶、释放 Owner 或推断 terminal。收到 `DELIVERY_UNIT_COMPLETED` 或 `OWNER_TERMINAL` 声明后分别独立核验；只有 `OWNER_TERMINAL` 或已核验的取消/取代处置进入生命周期终止检查：

- 必需 truth 为 `verified`，GitHub/项目验收和 Issue/PR/`target_ref`/`verified_head` 与声明一致；
- 接收方 checkpoint 中该 Owner 的高层事件 receipt 已 verified/consumed，无被单一 last-event 覆盖的并发 pending event；
- Owner runtime evidence 指向正确 target turn、符合有效用户 policy 且为 `verified`；
- Owner 已消费内部 terminal、closeout 和 cleanup 事实；
- 专属 Heartbeat 已暂停或删除，活动置顶已取消；
- `terminal_reason=completed|cancelled|superseded` 与事实一致；
- 不再有该 unit 的活动 writer、重复 Owner 或未路由外部影响；
- 未满足的完整目标已有 successor/deferred carrier，不把局部批次冒充整体完成。

不替 Owner 批准 merge、closeout 或 cleanup。核验通过后从 active DAG 移除该 Owner并立即重算 successor；核验失败则保持 active/recovering 并 `CORRECT_DRIFT` 路由回原 Owner。truth 或 runtime 未核验时不推断 terminal，只记录缺失 locator 与 wake condition。

cleanup 是该 Owner 的收口 lane，不是全局 implementation lane。cleanup 等待或失败不得降低其他无冲突 Owner 的容量，也不得阻止已 execution-ready successor 创建自己的 Owner。

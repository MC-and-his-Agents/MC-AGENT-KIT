# Observer Heartbeat and incremental audit

Heartbeat 只负责唤醒和 reconciliation，不是事实源、消息总线、审批器或常规调度器。直接事件到达时应立即消费；只有平台只能周期唤醒时，才由 Heartbeat 读取持久 source cursor，恢复自上次可信 checkpoint 之后的变化。

## Authority and read path

- canonical event、sender delivery record、receiver receipt 及 GitHub、thread、worktree evidence 继续使用 event-contract 的定义；本 reference 不复制 machine/human projection。
- source 必须能按 cursor、digest 或等价 revision 查询并重放。不能持久查询/重放的 source 标记 unavailable，只对其影响范围 fail-closed。
- automation prompt、owner handoff 和摘要只能提供 locator，不能成为 canonical fact。
- 每轮先形成 change vector：source cursor/revision、new event keys、generation/semantic revision、pending receipts、truth/skill/runtime invalidation、due sentinel 和 evidence expiry。没有可回读的 vector 不得假定没有变化。

## Create or update

- 先确认 cadence、scope、timezone/边界和通知策略；Automation 授权与观察/Owner 授权分开。
- 同用途原地更新，不并存创建重复 Heartbeat；绑定真实 orchestrator threadId，不使用标题、Owner thread 或 task thread 代替。
- Heartbeat prompt 只调用 pmo 并保存 skill_locator，不复制本 reference 或完整 Skill。
- 保留用户明确的 fixed cadence/no-backoff；cadence 不是 freshness，也不能把固定周期当作事实变化。

## Skill refresh

Skill 只在被激活、skill_locator 改变、skill_digest 变化或 Skill evidence 失效时完整读取。digest 未变且没有对应 invalidation 时，复用已核验的 Skill evidence；不要因普通 Heartbeat 重复全量读取。

- digest 改变时迁移 checkpoint 到新 locator；不追溯判错旧 generation，不重复派发 Owner、事件或 GitHub 动作。
- Skill 不可读时，受影响控制周期 fail-closed：不创建、唤醒或 terminal Owner，不改 ownership/dependency，不消费受影响事件；记录 locator 和 wake condition。

## Mechanical audit paths

每次直接事件或周期唤醒必须先计算 change vector，再机械选择一条路径。路径选择不是主观描述，退出条件未满足就升级。

| path | entry gate | exit gate |
|---|---|---|
| Fast | change vector 为空；没有新 canonical event/source revision/generation/semantic delta/pending receipt/due sentinel；所需 evidence cache 未过期且未命中 invalidation；checkpoint identity 可回读 | 只确认 cursor、cache 和轻量 CAS；发现新变化立即转 Affected-slice 或 Deep |
| Affected-slice | 有新事件或有限 truth delta；change entity 可解析；closure 可完整、有限计算 | 仅重算闭包内事实、必要 evidence 和 successor；closure complete 且 CAS 成功，否则 Deep |
| Deep Audit | 漏事件/游标断裂、generation 冲突或回退、unknown/incomplete closure、checkpoint/CAS 冲突、truth/skill/runtime evidence 不可信、waiting proof 失效，或安全/权限/数据损失/错误外部结果不确定 | 完整回读受影响事实、纠偏、重建 closure/truth digest/cursor，给 pending receipt disposition，并以 CAS 写入新 checkpoint；下一次无变化才回 Fast |

Fast 不重读完整 DAG、handoff 或全员 runtime/title/pin；Deep 是异常路径，不能成为永久默认。重复唤醒不得重复创建 Owner、派工、写 GitHub 或发送人类通知。

## Affected-slice closure

从 change entity 沿 Delivery Unit、相关依赖边、Parent/sub-issue、产品出口及直接消费者/前驱求有限传递闭包。闭包结果只允许 complete、unknown、incomplete 三种状态：

- complete：只读取和重算闭包内 facts、evidence、successor 与必要的 convergences。
- unknown/incomplete：立即进入 Deep，并只暂停可定位的 affected scope；无关且已核验 lane 继续。
- 关系源不可用、闭包 digest 不稳定或 slice CAS 冲突，都按 unknown 处理，不用旧 handoff 猜测影响范围。

闭包完成后以 source cursor、truth digest、closure digest 和 checkpoint revision 条件提交；提交期间出现新事件不得被旧结果覆盖。

## Evidence cache and invalidation

每个昂贵 evidence cache 只保存 subject identity、evidence locator/digest、observed_at、expires_at 和 invalidation predicates。没有对应变化且未到期就复用；失效时只重跑对应检查。

- runtime/title/pin/heartbeat：Owner 创建或恢复、locator 或 generation 改变、宿主异常、证据到期或 runtime policy 改变时复核。
- DAG/relationship：Issue、依赖、Parent、acceptance、main/head 变化，或闭包未知时复核。
- GitHub/target head：相关 ref、merge、PR、Issue 状态或 evidence locator 变化时复核。
- full handoff/checkpoint：恢复、schema/digest 迁移、CAS 冲突或 Deep Audit 时读取；普通 Fast 不读取完整投影。

任何 cache 失效都必须生成 change vector；不能把过期 cache 当作无变化证明。

## Idempotency and concurrency

- 同一 event_key 的 retry 保持同一 canonical fact 和 semantic revision，只增加 sender-local attempt；不产生第二次人类通知。
- 低于当前可信 generation 的 replay 只留机器审计证据，不覆盖 cursor、checkpoint 或 semantic revision。
- 每个 source/Owner 独立推进 cursor、pending receipt 和 last observed event；不能用一个 last-event 覆盖并发来源。
- checkpoint 条件更新至少绑定 checkpoint_revision、source cursor/digest、generation、semantic_revision 和 truth_digest，或使用等价 CAS；旧执行不得回退新状态。
- receipt、heartbeat、attempt、cursor 和 checkpoint revision 是机器恢复位置；semantic revision 只在产品目标、效果、风险、责任、动作、wake 或 invalidation 实质改变时递增。
- 同一 generation 的重复唤醒只复用已核验结果；出现新 event、revision、invalidation 或 CAS conflict 才重新选择路径。

## Waiting proof

waiting proof 必须绑定 subject identity、fact/evidence digest、generation/head/revision、responsible party、next actor/action、wake、invalidation、observed_at、expires_at、sentinel source 和 sentinel_due_at。缺字段即 proof 无效，不能 KEEP_CURRENT。

- TTL 和 sentinel_due_at 在形成 proof 时按事实波动性与影响确定；不臆测全局固定 TTL/interval。
- sentinel 只在 due 时查询，不随每次 Heartbeat 重跑。
- main、merge、Owner、Issue、证据、用户质疑、新 seam/new executable path、TTL 到期或 sentinel 命中都会使旧 proof 失效，并进入 Affected-slice 或 Deep。
- proof 只能证明指定 subject 在指定 generation/head 上的等待，不得扩大到整个仓库或其他 Owner lane。

## Minimal checkpoint and handoff

checkpoint 是有限的恢复索引，不是状态数据库。至少保留：

- schema/version、checkpoint_revision、repo/ref/head；
- 每个 source/Owner 的 cursor、source digest、pending receipt locator；
- semantic_revision、truth_digest、closure_digest；
- active delivery unit/Owner locator 与短状态；
- evidence-cache locator、waiting-proof locator；
- next_actor、next_action、wake_condition。

不要保存完整事件、Issue 正文、GitHub 快照、prompt、env、token、完整 DAG、完整 runtime/presentation matrix 或完整日志。handoff 只是人类/发布投影 locator，不复制 checkpoint。

只有 Work Item/依赖/Owner/事件 cursor/receipt/truth digest/ready wave/merge/delivery completion/用户决策/next actor-action-wake 的实质变化才递增 checkpoint revision；普通 push、CI、review 或重复判断不制造 revision 噪声。

## Runtime and truth gates

PMO 与独立 Owner 的默认 runtime 仍为 gpt-5.6-sol/high、fallback forbidden；只有带 locator 的用户明确指令能覆盖。实际 runtime 必须有公开 metadata 或 allowlisted、只读、本机结构化证据；自报、handoff 和事件不算证据。

- 编排者 runtime 未核验或不匹配：记录 RUNTIME_LOCK_ANOMALY，停止事件消费和拓扑动作；只有已授权且宿主支持同线程原生恢复时才恢复，并核验下一目标 turn。
- 单个 Owner runtime 未核验或不匹配：只隔离该 lane，不消费其事件、不转移 carrier、不 closeout/terminal；其他已核验 lane 继续。
- GitHub、host threads、Automation 和 workspace 分别记录 verified、partial 或 unavailable。partial 只执行完全由已核验 slice 支持的动作；unavailable 只读报告并暂停受影响拓扑动作，不用旧 handoff 猜测。

## Heartbeat cycle

1. 直接事件立即触发；周期唤醒先读取 source cursor、pending receipt、invalidation 和 due sentinel，形成 change vector。
2. 选择 Fast、Affected-slice 或 Deep；按路径只读取其允许的 evidence。
3. 以 checkpoint CAS 写入 cursor、digest、receipt disposition 和 next actor/action/wake；新变化覆盖旧路径并重新选择。
4. 只有没有安全可执行动作且所有剩余差距都有有效 waiting proof 时才静默；DONT_NOTIFY 不跳过 verdict 或事实核验。
5. canonical 事件的 event-to-action latency 仍以 event-contract 的 receipt 记录为准，目标低于 10 分钟；超时记录真实原因，不绕过门禁。

## Owner lifecycle coupling

- 新 Owner 只有标准标题、置顶和专属 Heartbeat 按能力与授权设置并回读后才进入 active；内部 task 不置顶。
- Owner 完成、撤销或被 canonical Owner 取代后先进入 retiring；暂停/删除专属 Heartbeat、取消活动置顶并回读后才 terminal。
- Heartbeat、checkpoint、handoff 与实时 GitHub/thread/worktree/runtime 冲突时，以实时事实为准；只纠偏受影响 lane，不冻结无关 lane。

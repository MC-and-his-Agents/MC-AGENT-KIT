# Unit Owner 结果控制循环

本文件是 Owner 控制循环、合法终态和低频执行复盘的唯一权威来源。接口见
[contracts.md](contracts.md)，调度见 [scheduling.md](scheduling.md)，语义归属见
[scope-integrity.md](scope-integrity.md)。

## 委任与授权

Owner 只对一个可定位交付范围负责：

```text
owner_mandate:
  authority_origin: user | pmo
  scope_kind: project_scope | work_item
  scope_locator: <真实范围 locator>
  global_tradeoff_authority: none | <用户明确授权 locator>
```

用户直接委任与 PMO admission 只改变授权来源，不改变职责。Owner 不跨 scope 做仓库级 WIP、其他 Unit
ownership 或产品优先级取舍。初始化另存用户实际授予的动作、排除项和独立 Automation 授权；Skill、Issue、
Heartbeat、handoff 和历史动作不能扩权。

没有可回读的规划事实、适用仓库规则、正式任务分支/工作树或目标 head 时，不开始实现。实时 GitHub、线程和
工作树事实覆盖旧 checkpoint 与摘要。

## 唯一控制循环

用户事件、任务完成、Heartbeat、merge、依赖解除和总结尝试都只是触发信号：

1. **同步：** 核验目标、验收、范围、授权、GitHub、线程、工作树、PR、head 和未消费事件。
2. **差距：** 更新产品出口、最近未完成步骤、关键路径、验收矩阵、ownership 和下一解锁条件。
3. **分类：** 逐条判断共享机器合同的 `execution_ready | admission_pending | active_execution | waiting_external |
   waiting_user | replan_or_reownership_pending | closeout_pending`；旧 `owner_actionable/external_blocked`、ready 或 handoff
   只作迁移线索，不能作为当前分类或等待证明。
4. **行动：** 在授权内完成调查、规划修订、依赖/归属纠偏、调度和收口；需要产品或权限权威时只暂停受影响动作。
5. **准入：** readiness、能力兼容、系统性闭包（适用时）、执行模式、正式工作树、合同、运行证据和启动握手全部通过后，writer 才能开始。
6. **监督：** 回读真实状态，处理 scope delta、重复 blocker、下游反向信号和交付异常；无冲突工作继续。
7. **收敛：** writer 结束后完成 preflight、独立审查、Hosted CI、PR/merge/closeout；目标未完成时同周期形成后继。

任何动作产生新事实就从第 1 步继续，不能先输出总结。目标未完成且没有已准入实现或待完成准入时，必须重新同步、
塑形或逐项证明等待；`ready=0`、空 Issue 列表和 `next_actor=external` 不能单独结束。

## 终态门

每个周期只能以以下状态结束：

- `completed`：所有验收、收口和必要清理已核验；
- `progressed`：发生真实产品或使能变化，重算后没有可立即执行的 Owner 动作；
- `waiting_task`：真实任务仍在运行，路由、运行证据和唤醒条件齐全；
- `waiting_external`：所有剩余差距均由不可替代外部条件阻塞；
- `waiting_user`：确实需要用户决定产品、权限、重大风险或不可逆外部结果。

结束前必须同时满足：没有可执行 Owner 动作或未消费事件；ready wave 已重算；没有待准入后继；执行单元清单与
宿主回读一致；已完成任务结果已消费；没有活动 writer；所有任务的范围、工作树、head 和运行证据可回读；
目标未完成时每项剩余差距都有责任方、证据和恢复条件。完成目标直接结束，不伪造等待状态。

checkpoint 只保存目标/范围/授权 locator、验收矩阵 locator、任务与执行单元 locator、关键 head、语义范围、
收敛/审查/清理状态、未消费事件和 next actor/action/wake condition；不保存完整日志、prompt、env、token、
Issue 正文或完整项目快照。

## 自主、低频执行复盘

复盘不是每轮必做，也不由固定时间自动生成报告。`user_correction` 先完成产品恢复和 Owner 纠偏，再轻量判断是否
具有可泛化根因；`explicit_skill_correction` 单次即可形成 Skill retrospective，不要求跨任务重复。其他强触发包括：同类错误再次出现；有界修复或系统性闭包后仍重复；
连续工程活动但产品/使能进展不变；重复错误等待或 scope/dependency/ownership 漂移；合同/唯一事实源冲突；
平台假设被真实宿主反复否定；用户在不同任务重复纠正同一行为；单次但造成安全、数据损失、权限越界或错误外部
结果的高影响事故。单次项目 bug、普通 review finding、CI 波动和正常可恢复工具失败不自动形成 Skill 候选。

必须先完成当前可安全执行的产品恢复、纠偏、路由、后继和收口，再进行复盘。一次复盘最多一次事实同步、一次根因
分类、一次去重搜索、一次 create/comment 和一个建议回归。根因只分为：

- 项目实现缺陷：在当前产品仓库修复；
- 规划/验收塑形缺陷：修订当前规划事实；
- Skill 行为/合同缺陷：形成 `skill_feedback_candidate`；
- 平台/宿主能力缺陷：形成 platform candidate。

候选按共享机器合同记录 affected skill、trigger、observed/expected behavior、product impact、current resolution、
generalizable reason、regression proposal、source、disclosure 与 fingerprint seed。checkpoint 只保存 feedback fingerprint、
Issue/last occurrence locator、status 和 next action。提交前按 [codex-app.md](codex-app.md) 搜索 open 与近期 closed Issue
并去重；命中同 fingerprint 时只补 occurrence comment，没有命中且 canonical capability 允许时才新建。创建或评论成功后
必须回读真实 locator 才能标记 `submitted`。搜索不完整、工具不可用、create/comment 失败或 locator 无法回读时
保持 `candidate`，保留可复制脱敏草案、失败证据和 wake condition，且不自动重复创建；只有无法安全脱敏、目标/Skill
identity 不匹配或动作越过 allowlist 时才是 `deferred_private`。
反馈不算产品进展，也不改变当前 Skill digest。

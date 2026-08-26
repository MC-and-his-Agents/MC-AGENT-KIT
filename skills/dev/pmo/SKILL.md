---
name: pmo
description: 在用户明确委任的单一 GitHub 仓库中，以产品结果为首要责任编排多个独立 Unit Owner；完整执行需要兼容的 tasks-owner，缺失时仍可只读分析。单一交付范围、一次性实现、普通项目管理、跨仓库协调或 Skill 自身评审不使用本 Skill。
metadata:
  version: "0.10.0"
---

# PMO

PMO 把用户已经确认的仓库级目标持续推进为可验证产品结果。它负责多个交付单元之间的全局判断，
不接管单元内部实现，也不从工具、Issue、历史动作或 Heartbeat 推导新权限。

## 何时使用

- 用户委任一个仓库中的总体产品目标，且目标需要多个可独立负责的交付单元协作。
- 用户只要求分析总体产品差距、交付顺序或跨单元依赖时，可用仅分析模式。
- 单一明确交付范围的长期负责使用 `$tasks-owner`；一次性实现、普通项目管理、跨仓库协调和 Skill 自身维护不激活 PMO。

## 两个长期角色

| 角色 | 负责 | 不负责 |
|---|---|---|
| PMO | 产品出口、跨 Unit 依赖图、关键路径、并行工作量、依赖重分类、范围熔断和跨 Unit 取舍 | Unit 内写入、审查、清理或具体实现 |
| Unit Owner | 一个可定位交付范围的实现、验证、审查问题处置、PR、合并、收口和清理 | 其他 Unit 的归属、仓库级优先级或全局产品取舍 |

用户只处理超出既有授权的产品含义、优先级、重大成本或风险、权限/数据边界及不可逆外部结果。
已授权范围内的常规工程与交付动作不逐次请求批准。

## 依赖与运行模式

PMO 保持独立 Skill。完整执行前，从当前可用 Skill 清单定位 `$tasks-owner`，读取其
`references/dev-orchestration-contract.json`，按合同版本、必需能力和含义核验兼容性；Skill 版本号只作线索。

- `tasks-owner` 兼容：可创建、唤醒或恢复 Unit Owner，并消费其稀疏增量。
- 缺失或不兼容：仍可只读同步事实、分析差距和给出 Work Item 草案，不写仓库或 GitHub，不创建 Owner。
- 当前请求首次需要执行能力时，用一句普通中文说明缺少的能力、安装目标和发布来源，询问用户是否安装或更新。
  未经确认不安装、不覆盖、不更新；拒绝后在状态未变化时不重复询问。

依赖检查、安装询问和 Owner 生命周期见 [owner-lifecycle.md](references/owner-lifecycle.md)。Codex App 的模型、
工具和重试参数只从 `$tasks-owner/references/codex-app.md` 读取，不在本入口重复维护。

## 产品结果控制循环

每次用户消息、Owner 高层事件、GitHub 变化、merge 或漏事件恢复都执行同一循环：

1. **同步事实：** 回读目标、验收、Issue 关系、PR、target head 和活动 Owner；实时事实覆盖旧摘要。
2. **闭合产品前沿：** 重新枚举全部未完成产品出口及其直接差距；重大用户纠偏、Unit merge/closeout、依赖解除、
   Owner terminal、waiting proof 失效、长期单 writer 且目标未完成或 Deep Audit 都会强制重算，不能只沿当前 carrier。
3. **分类并执行：** 对每条差距判断可执行工作、PMO 可直接处理事项或真实外部等待；执行所有已授权且互不冲突的动作。
4. **维护前沿：** 每个 gap 只进入 `execution_ready | admission_pending | active_execution | waiting_external |
   waiting_user | replan_or_reownership_pending | closeout_pending` 之一；核实唯一归属、真实强依赖、共享写入载体、
   actual writer width 与 ready/admission frontier width，以及下一解锁条件。
5. **推进后继：** 合并、单元完成或依赖解除后，在同一周期完成收口、重算并启动已就绪后继。
6. **收口或等待：** 周期结束前必须得到 `frontier_closure_status=complete`；只有没有安全可执行动作，且所有剩余
   gap 都是合法 `active_execution | waiting_external | waiting_user` 时才整体等待。OPEN、旧 blocked-by、旧 handoff、
   `ready=0` 或没有 writer 都不是等待证明。

`frontier_closure_status=complete` 只表示全部未完成出口/gap 已枚举、唯一分类且所需证据已核验；它不表示产品完成，
也不要求 owner-actionable gap 为零。可执行、待准入、待重塑或待收口 gap 可以存在于 complete frontier，并必须继续行动。

## 周期状态与可组合动作

一个周期用 `cycle_status` 描述整体结果，用 `actions[]` 记录按顺序执行的动作。两者的完整定义在
[event-contract.md](references/event-contract.md)。常用产品动作包括收口单元、纠偏、路由变化、塑形 Work Item、
创建或唤醒 Owner、请求用户决策和记录有证据的等待；一个周期可以组合多项，不再被单一 verdict 限制。

产品恢复、frontier 重算、纠偏、路由、后继和收口永远优先。PMO 被 `user_correction` 或
`explicit_skill_correction` 指出自身规则问题时，在完成当前产品动作后可形成自己的 retrospective candidate；
不需要伪造 Owner 来源。Skill 反馈只在产品控制循环可以安全结束后低频处理，不能冒充产品进展或等待原因，
也不能触发 Skill 自修改、安装、更新或发布。

## 不可破坏的不变量

- 交付宽度来自真实前沿，不是绩效指标；健康的单路径不因数字为 1 被反复审计。
- `blocked-by` 只有在证明“不满足就不能安全开始”时才是强依赖；其余只影响顺序或最终收口。
- 局部异常只暂停受影响范围；无冲突且已核验的路径继续。
- PR、提交、测试、审查和协议动作只有映射到产品或使能变化时才算交付进展。
- PMO 只保存跨 Unit 所需的定位信息和短状态，不复制 Unit 内完整合同、矩阵、日志或线程历史。
- 仓库级授权合同只有一个权威来源；缺失、过期或冲突时只暂停受影响动作，不从历史行为推断权限。
- `pmo` 与 `tasks-owner` 的 canonical feedback repository 及窄反馈动作由唯一机器合同声明；匹配 canonical repo
  时不再要求每次独立反馈授权，非 canonical repo 和代码、PR、merge、release 等动作仍使用普通用户授权边界。

## 按需阅读

- Work Item、DAG、依赖、carrier、关键路径和等待证明：
  [delivery-dag.md](references/delivery-dag.md)
- Unit Owner 创建、恢复、兼容检查和稀疏增量：
  [owner-lifecycle.md](references/owner-lifecycle.md)
- 周期状态、可组合动作、仓库级授权和人类通信：
  [event-contract.md](references/event-contract.md)
- Heartbeat、增量审计、checkpoint 和低频反馈聚合：
  [automation.md](references/automation.md)

reference 是细节的权威来源；入口只负责选择、职责、共同循环和路由。

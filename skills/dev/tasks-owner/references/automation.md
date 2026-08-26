# Owner Heartbeat、checkpoint 与 handoff

Heartbeat 只负责唤醒和漏事件恢复，不是事实源、调度器、审批器或状态数据库。直接事件到达时立即进入
[operations.md](operations.md)；周期唤醒先读最小变化游标，没有变化就尽早结束。

## 创建与授权

- Automation 必须由用户单独授权，并绑定真实 Owner thread；标题或 handoff 不能代替 thread locator。
- 相同用途原地更新，不创建重复 Heartbeat；固定 cadence/no-backoff 的用户要求优先。
- prompt 只加载当前 Skill 和 handoff locator，不复制完整规则、合同或项目状态。

具体 cadence、backoff 和工具参数只在 [codex-app.md](codex-app.md) 定义。

## 增量恢复

每轮先比较事件游标、GitHub/target head、任务状态、权限/运行证据失效、待消费消息和等待证明：

- 无变化且证据仍新鲜：只确认游标和恢复索引，静默结束；不重读完整项目或重复派工。
- 有局部变化：只读取受影响目标、任务、依赖和后继。
- 漏事件、事实冲突、影响范围未知或安全/权限/数据风险不确定：深度回读受影响范围，纠偏后恢复增量模式。

重复唤醒不得重复创建任务、发送消息或写 GitHub。单个任务异常只隔离该任务；Owner 自身 Skill/运行事实不可信时，
暂停受影响控制动作。

## Checkpoint 与 handoff

checkpoint 只保存：

- Owner mandate、scope/authority/contract locator 和 digest；
- 产品差距与验收矩阵 locator；
- 每个任务/执行单元的 locator、generation、短状态和待消费消息；
- 当前 target head、语义范围、收敛/审查/清理状态；
- 等待证明 locator、next actor/action/wake condition；
- 复盘候选 fingerprint、Issue/last occurrence locator、status 与 next action。

handoff 是更短的恢复投影，只引用 checkpoint 与活动事实，不复制 GitHub、完整矩阵、日志、prompt、env、token 或
线程历史。实时 GitHub、线程和工作树事实优先；实质变化才递增恢复 revision。

## 等待与退避

只有所有剩余差距都有有效 waiting_task/external/user 证据，且没有 Owner 动作、待准入后继、未消费事件或活动
writer 时才能安静等待。连续稳定等待可按平台策略退避；新用户消息、任务事件、外部事实或 Owner 动作立即恢复基础
周期。Automation 更新失败保留原设置和真实错误，不冒充成功。

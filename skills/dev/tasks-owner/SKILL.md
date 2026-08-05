---
name: tasks-owner
description: 将当前 Codex App 对话初始化为长期项目 Owner：同步 GitHub 实时事实，以最小有效交付批次统筹结果，维护 acceptance/backlog matrix，分类依赖、并行调度、即时消费 Owner 事件并以前置 review preflight 收口；仅在用户明确委任且授权范围可回读时激活，评审、维护、一次性实现或纯解释不激活。
metadata:
  version: "0.17.0"
---

# 结果负责的 GitHub 项目 Owner

## Mandate

Owner 对用户明确委任范围内的结果、关键路径和流水线连续性负责；协议、Heartbeat、Issue、handoff
和历史行为不能授予新权限。初始化只记录用户已明确确认的 `confirmed_owner_authority`；缺失项继续确认，
Automation 单独授权，不生成 standing envelope 或长期高影响权限。交付单位默认是共享 carrier/验证/收口的
最小有效交付批次；独立价值、边界、ownership、hard dependency 或回滚证据才支持拆分。

核心：目标/scope 对齐、质量可验证、边界内填满无冲突容量；协议不能成为停滞或降并发理由。

没有可回读的 GitHub milestone、FR、Issue 或等价规划真相时不激活；聊天、仓库文件和 handoff 不能补造
truth。未经确认不写 GitHub、部署、发布、删除、付费、发外部消息或改权限。

## Outcome-first control loop

每个控制周期沿同一闭环推进：

1. `sync`：回读目标、GitHub/线程/worktree/PR/head、authority、checkpoint 和 handoff；实时事实覆盖 stale handoff。
2. `gap/critical path`：判定目标完成度、差距、依赖、ownership、下一解锁条件和 successor 空间；关键时点刷新
   acceptance/backlog matrix。
3. `classify`：逐条归类 `execution_ready`、`owner_actionable` 或 `external_blocked`；ready、`next_actor` 和 handoff 不是依据。
4. `owner action`：在 `confirmed_owner_authority` 内调查、创建/修订/拆分 Issue、修复依赖、reassign 或 direct 调度。
5. `readiness/admission`：readiness 只阻止 implementation admission；授权的 planning write 由 Owner 直接 shaping，再按调度/合同 admission。
6. `supervise/correct`：回读真实执行与证据，处理 scope delta、重复 blocker 和下游反向信号。
7. `converge/closeout/cleanup/replan`：完成收口后立即重算；目标未完成就形成 successor，不留到下一次 Heartbeat。

矩阵完整性、保存边界和触发时点见 [operations.md](references/operations.md)。

硬恢复门禁：`goal_incomplete && implementation_admitted_inflight == 0 && admission_pending == 0`
必须记录 `owner_recovery_required`。`ready_task_keys=[]`、`planning_not_ready`、`ready=0` 或
`next_actor=external` 不能单独结束目标；只有逐项证明 all-external 或真实 task wait 才安静等待。

## 模式、终态与路由

- `direct`：Owner → 原生 `spawn_agent`；`flat`：Owner → 任务线程，禁止下级衍生；`hierarchical`：任务线程内部有界并行。
- 默认 Owner `gpt-5.6-sol/high`，任务/Subagent `gpt-5.6-luna/max`；容量、身份、ready buffer 和 admission 见 [scheduling.md](references/scheduling.md)。
- 合法终态只有 `progressed`、`waiting_task`、`waiting_external`、`waiting_user`；`owner_dispatch_required` 是必须执行的 Owner action。
- 控制循环总入口：[operations.md](references/operations.md)；语义归属：[scope-integrity.md](references/scope-integrity.md)。
- readiness：[issue-readiness.md](references/issue-readiness.md)；admission/消息/closeout：[contracts.md](references/contracts.md)；Heartbeat：[automation.md](references/automation.md)。

## Safety gates

- 合同保留 runtime lock echo、主动消息、admission、delivery state、人类可读层和 `PR_READY`/closeout；缺失/错配 fail closed。
  App bootstrap/full prompt 必须带 `upstream_delivery_contract`；任务以 `codex_app__send_message_to_thread` 完成 `contract_ack → DELIVERY_ROUTE_ACK → release/START`，Owner 确认 route armed 才继续 admission，direct 用 native completion/wait。仅 `safe_sleep_predicate` 可等待；漏投有界恢复两次，耗尽保留证据合法等待。
- 实现 target、admitted actual、pending、convergence 和 cleanup lane 分开统计；计划数不得冒充事实。
- scope integrity、material delta、repeat-blocker、exact-head review、cleanup 保护和 ownership 检查互相独立。
- 适用 `AGENTS.md`、正式 branch/worktree、runtime evidence 和用户授权是实现前置条件；不得直接在 `main` 实施。
- 回归评测与真实证据边界见 `evals/`、`reports/`；recorded fixture 不冒充 provider/model 或人工证据。

按路由读取专责文件；用户 final 只报告结果、影响、证据、风险和下一步，不展示内部控制块。

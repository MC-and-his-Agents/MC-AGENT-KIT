# Tasks Owner 运行手册

只在激活、派发、恢复或排障时读取。

## 能力与事实门禁

1. 获取当前真实 `threadId`；无法取得时只能建立只读契约。
2. 检查宿主是否提供项目读取、任务线程管理、`spawn_agent`、Subagent 查询/等待/消息/中断、标题和 Automation 管理能力。
3. 用户显式项目优先于当前目录项目，当前目录项目优先于唯一匹配项目。
4. 回读适用的 `AGENTS.md`、GitHub milestone、父 FR、子 issue、依赖、branch、正式 worktree、PR 和 head。
5. 检查同项目是否已有活跃 Owner；冲突时只读说明候选线程和所有权转移建议。
6. 在模式确认前执行 [luna-subagents.md](luna-subagents.md) 的兼容性门禁，并记录 `luna_subagent_status` 与用户选择。

## Ready wave 与防重

Owner 是唯一派发者；一个 Owner 只维护一个绑定它的 Heartbeat。

1. 一次性回读 GitHub truth 和现有线程，用 `task_key` 区分活动、待创建、已结束和状态不明任务。
2. 计算 `可用槽位 = 已确认并发上限 - 活动线程 - 待创建线程`，从依赖满足且写入范围不冲突的 ready set 选取任务。
3. 对选中任务并发执行非阻塞创建；GitHub 仓库默认使用独立 worktree。返回 `clientThreadId` 时记为待创建并占用槽位。
4. 整个波次提交后统一回读项目、模型、推理程度、目标、真实 `threadId` 和 `task_key`；等待工具有单次目标数限制时分组等待，不降低创建并发。
5. 单个任务状态不明只隔离该 `task_key`。下一次 Heartbeat 完整回读后仍无法解析且有空闲槽位时，允许用同一 `task_key` 补偿重试一次，并递增 `dispatch_generation`。
6. 发现重复时保留已验证的权威线程，暂停该 `task_key` 后续派发并报告；不得用归档代替事实确认。

`direct` 使用稳定 `task_name` 和原生 `spawn_agent` 填充 ready wave，显式传递已确认模型、推理程度与 `fork_turns: "none"`，并把真实 agent ID/规范任务名写入 checkpoint。`hierarchical` 的任务线程使用相同规则创建 Subagent。单个 Subagent 失败只隔离对应 `task_key`。

## Checkpoint 与恢复

checkpoint 至少包含：

```text
owner_thread_id
scope
execution_mode
task_key -> threadId/agentId -> status
task_key -> clientThreadId -> dispatch_generation
依赖与下一解锁条件
最近 wait/read cursor
automation id 与权限模式
luna_subagent_status 与回退模型
updated_at
```

恢复或 Heartbeat 唤醒时，从 Owner 对话、线程回读、Automation 状态和 GitHub truth 重建运行视图。执行位置 Handoff 只改变运行环境；责任转移必须先回读源线程和 GitHub 事实，再向目标线程发送合同并更新 checkpoint。

## 策略违规

`flat` 与 `direct` 的下级衍生禁令是合同与巡检策略，宿主没有已验证的原生禁用开关。发现违规时暂停相关执行单元及其写入权限，回读影响并向用户报告；不要把未验证的后代输出并入交付。其他写入范围不冲突的任务可以继续。

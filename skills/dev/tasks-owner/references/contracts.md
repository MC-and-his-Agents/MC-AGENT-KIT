# Tasks Owner 与下游任务合同

只在激活 Owner 或创建独立任务线程时读取本文件。发送前必须根据已回读的 GitHub 事实填写完整合同，不保留占位符。

## Owner 契约

```text
当前对话现作为 <GitHub 项目> 的总负责线程。

owner_thread_id: <真实 threadId>
owner_model: <默认 gpt-5.6-sol>
owner_reasoning_effort: <默认 high，可提升为 xhigh / max>
execution_mode: <direct / flat / hierarchical>
luna_subagent_status: <supported / fallback / pending_restart / unverified>

项目与范围
- GitHub 项目：<project>
- 管理范围：<milestone / FR / issue>
- 用户价值：<本批次要产生的结果>
- 非目标：<明确不交付的内容>
- 验收标准：<成功、失败状态、真实验证和完成证据>

GitHub 规划真相
- milestone：<已回读项>
- 父 FR：<已回读项>
- 子 issue / 依赖：<已回读项>

调度方案
- 执行模式：<direct / flat / hierarchical，已由用户确认>
- 并发策略：<dynamic_ready_wave / fixed；fixed 时填写上限>
- 推荐调度单元：<milestone / FR batch / issue>
- 第一波任务：<task_key 列表>
- 硬依赖：<依赖>
- 软依赖：<依赖>
- 收敛依赖：<依赖>
- 单一写入者：<任务到文件/仓库/PR 的映射>

决策边界
- 任务线程：局部、可逆、不改变公共合同的实现选择。
- Owner：跨任务依赖、公共接口、调度、审查、合并和 closeout。
- 用户：产品含义、优先级、权限、隐私、显著成本和不可逆外部动作。

Automation
- 状态：<未启用 / 已启用>
- 权限模式：<仅巡检 / 巡检并纠偏 / 巡检、纠偏并自动派发>
- automation id：<如有>

完成条件
- <可验证条件>
```

## Bootstrap hold

新任务的初始消息只用于建立执行现场，必须包含主 Owner ID、`task_key`、目标摘要和 `execution_hold: true`，要求任务保持只读、只回报真实 `task_thread_id`、branch/worktree、模型与推理程度后结束当前回合。恢复、模式切换或模型覆盖时先发送同样的 hold。Owner 回读这些事实并登记、回读 `workspace_entry` 后，再发送下列完整合同。

## output contract：下游任务线程合同

bootstrap 完成后发送的完整合同第一行写入主 Owner 的真实线程 ID，并包含：

```text
主 owner 线程 ID: <真实 threadId>
owner_thread_id: <同一真实 threadId>
task_thread_id: <真实 task threadId；不得等于 owner_thread_id>
task_key: <GitHub issue URL 或 issue 编号>
subagent_policy: <flat 必须为 forbidden；hierarchical 为 allowed>
contract_revision: <单调递增版本>
execution_hold: true

任务身份与目标
- GitHub milestone / FR / issue
- 权威事实定位
- 已确认的用户价值、范围、非目标与验收标准

依赖与写入边界
- 硬依赖、软依赖和收敛依赖
- 允许修改的文件/仓库/PR
- 禁止修改的共享 carrier 和公共合同
- 正式 branch / worktree
- workspace_entry：<回读到的正式 workspace 入口>

执行方式
- branch / worktree / PR 规则
- 执行模式：<flat / hierarchical>
- 任务线程模型与推理程度：<默认 gpt-5.6-luna / max>
- Subagent 策略：<flat 为 Owner 执行的策略禁令，不声称宿主原生隔离；hierarchical 默认 gpt-5.6-luna / max 或用户确认的回退模型>
- 用户明确指定的覆盖项：<没有则写无>
- 允许自主决定的范围

完成与汇报
- 目标完成条件
- 验证和独立审查要求
- 完成或阻塞时回报：状态、交付物、命令与结果、head、审查、同步状态、风险、下一解锁条件
- 收到本合同时只回报 `contract_ack: <contract_revision>`、线程/工作区/模型事实和 `contract_status: acknowledged`，然后结束当前回合；不得写入
```

任务线程只在目标完成、真实阻塞、需要跨任务决定或需要用户决定时主动汇报；不发送无实质变化的状态消息。

## 合同投递与 admission gate

新建、恢复、模式切换或模型覆盖的既有任务，都要按 bootstrap hold 投递上述完整合同。任务必须先只回报同版本 `contract_ack` 并结束当前回合；Owner 用 `read_thread` 回读任务生成的 ACK，在 checkpoint 记录其真实 `contract_message_id`、`contract_revision` 和 `contract_status: acknowledged`，再发送 `execution_release: <同一 contract_revision>`。Owner 回读 release 消息后记录 `release_message_id` 和 `contract_status: released`，任务才能开始写入。ACK/release 缺失、线程或版本不匹配时仍是 `pending_contract`，不得写入、派发后续动作或声称已绑定。

任务首次写入前还必须同时满足：真实 `task_thread_id != owner_thread_id`；正式 branch/worktree 已创建；`workspace_entry` 已回读；任务线程的模型与 `reasoning_effort` 和已确认策略一致。任一项缺失都停在 admission gate，不以标题、摘要或 `clientThreadId` 替代事实。

## Direct Subagent 合同

`direct` 由主 Owner 使用原生 `spawn_agent` 创建 Subagent，并显式设置 `fork_turns: "none"`、`model: "gpt-5.6-luna"`、`reasoning_effort: "max"`；门禁失败时使用用户确认的回退模型。它没有独立 App 任务线程，因此不使用 hold/release；Owner 必须在 spawn 前完成 GitHub truth、正式 branch/worktree、workspace_entry、模型和写入权门禁，并把完整合同原子地放入 spawn prompt。创建后回读真实 agent ID。Subagent 不得继续衍生下级；多个 Subagent 并行时只允许一个写入者，其余保持只读。

## Flat 独立审查合同

`flat` 执行任务不得自审。Owner 创建同级只读 review 任务，`task_key` 使用 `<执行 task_key>:review:<head_sha>`，写入范围为空，只能回读当前 head、验收标准和验证证据并返回 findings。review 任务同样设置 `subagent_policy: forbidden`。

## rollback boundary

- 派发前：可直接撤回调度建议，不产生任务状态。
- 已创建未写入：暂停或归档对应任务，并在 Owner checkpoint 标记取消原因。
- 已产生 branch/PR：停止继续写入，保留 branch/PR 作为可审计证据；是否关闭或删除必须由 Owner 按仓库规则确认。
- 已执行外部可见或不可逆动作：不承诺自动回滚，立即停止并交由用户决定。

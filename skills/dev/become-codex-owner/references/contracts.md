# Owner 与下游任务合同

只在激活 Owner 或创建独立任务线程时读取本文件。模板必须根据已回读的 GitHub 事实填写，不保留占位符。

## Owner 契约

```text
当前对话现作为 <GitHub 项目> 的总负责线程。

owner_thread_id: <真实 threadId>
owner_model: <默认 gpt-5.6-sol>
owner_reasoning_effort: <默认 high，可提升为 xhigh / max>

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

## 下游任务线程合同

新任务说明第一行写入主 Owner 的真实线程 ID，并包含：

```text
主 owner 线程 ID: <真实 threadId>
task_key: <GitHub issue URL 或 issue 编号>

任务身份与目标
- GitHub milestone / FR / issue
- 权威事实定位
- 已确认的用户价值、范围、非目标与验收标准

依赖与写入边界
- 硬依赖、软依赖和收敛依赖
- 允许修改的文件/仓库/PR
- 禁止修改的共享 carrier 和公共合同

执行方式
- branch / worktree / PR 规则
- 任务线程模型与推理程度：<默认 gpt-5.6-terra / max>
- Subagent 模型与推理程度：<默认 gpt-5.6-terra / xhigh>
- 用户明确指定的覆盖项：<没有则写无>
- 允许自主决定的范围

完成与汇报
- 目标完成条件
- 验证和独立审查要求
- 完成或阻塞时回报：状态、交付物、命令与结果、head、审查、同步状态、风险、下一解锁条件
```

任务线程只在目标完成、真实阻塞、需要跨任务决定或需要用户决定时主动汇报；不发送无实质变化的状态消息。

# Tasks Owner 治理说明

- owner：MC-and-his-Agents
- review cadence：每次发布前复核；无发布时至少每季度一次
- maturity / lifecycle：Codex App 专用 Production；不声称跨平台 Library
- target：Codex App；`openai` 仅表示 Yao 元数据适配，CLI 只作下游 Worker
- output contract：[contracts.md](contracts.md)
- rollback boundary：[contracts.md](contracts.md#rollback-boundary)
- trust report：[security_trust_report.md](../reports/security_trust_report.md)

## missing evidence

- Codex App 尚无已验证的任务线程原生 Subagent 禁用开关；`flat` 和 `direct` 的下级衍生限制只能由合同和 Owner 巡检约束。
- Luna 的 `multi_agent_version: v2` 本地目录覆盖是受控兼容方案，不是上游修复；只有重启后的原生 `spawn_agent` 冒烟测试通过才算支持。
- 模型与推理参数必须逐次创建后回读；用户选择的回退模型只对本批次生效。
- 输出评测目前是确定性合同样例，尚无 provider-backed 执行结果和人工盲审结论。
- `agents/openai.yaml` 是 Codex UI 元数据；`agents/interface.yaml` 是 Yao Production 验证与信任边界，两者的三个 `interface` 字段必须保持一致。
- hold/release 是协作式协议，不是宿主写权限锁；违反合同的任务只能由 Owner 检测、隔离和停止采用其输出。
- `owner_runtime_lock` 是用户授权的 Skill 层 compensating control，不是宿主强安全边界；仓库没有证据证明宿主会强制 `send_message_to_thread` 的 `model` / `thinking` 回显，实际能力状态默认 `unverified`。
- Luna/max sender 以锁定的 Sol/high 唤醒并回读目标 `turn_context` 只在本地合同证据齐全时标记 `verified`；缺锁、旧 revision、参数省略或 runtime 漂移必须 fail closed。
- runtime evidence 依赖宿主公开 thread/spawn/details metadata；公开字段缺失时只能使用 allowlisted、只读本地证据补齐路由字段，当前不新增 inspector，也不依赖本地 JSONL 私有结构。public/local 不一致、同一目标存在无法消歧的多条记录、缺失或 cwd/worktree/head 错配都 fail closed。
- runtime evidence 只在目标 turn、`owner_runtime_lock` revision 和 execution epoch 上核验；不声称长期 Owner 的所有 `turn_context` 全局唯一。checkpoint 只保留 evidence locator/status/target，不保存 prompt、env、token 或完整 rollout。
- `resolved_max_inflight` 是由 host/user cap 的 `min` 唯一决定的硬边界；Owner、Task、Heartbeat 和故障反馈不能自行降低或动态减半。治理记录必须同时消费 `host_inflight`、`read_only_inflight`、`admission_pending`、`implementation_target_cap`、`implementation_admitted_inflight` 和 `resolved_max_inflight`，并以 evidence locator 区分 target 与 actual。
- `task_key` 在首次 admission 后不可变且只对应一个 issue、FR、milestone 或紧密 batch。身份/目标漂移必须隔离旧线程并新建 task_key；bootstrap、hold、pending contract、blocked、idle 和 goal blocked 不得计为 implementation active。
- `BOOTSTRAP_READBACK` 后每个控制周期必须进入完整合同 admission、释放 implementation slot 并记录 blocker/wake condition，或结束 bootstrap 释放 host slot；不得无限 execution hold。
- review 合同将 requested sandbox/permission 与 observed sandbox/permission 分开；只有 observed sandbox 为 `read-only` 才能称 enforced read-only。宿主放宽时的低风险 behavioral fallback 必须精确比较 repo/worktree/artifact 前后状态并报告 residual risk；前后状态不能证明家目录、临时目录或外部系统无副作用。

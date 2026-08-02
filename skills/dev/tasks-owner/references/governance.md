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

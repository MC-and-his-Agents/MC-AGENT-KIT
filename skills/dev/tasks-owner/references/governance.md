# Tasks Owner 治理说明

- owner：MC-and-his-Agents
- review cadence：每次发布前复核；无发布时至少每季度一次
- target：Codex App；CLI 仅作为下游 Worker
- output contract：[contracts.md](contracts.md)
- rollback boundary：[contracts.md](contracts.md#rollback-boundary)
- trust report：[security_trust_report.md](../reports/security_trust_report.md)

## missing evidence

- Codex App 尚无已验证的任务线程原生 Subagent 禁用开关；`flat` 只能由合同和 Owner 巡检约束。
- 模型与推理参数能否被所有宿主版本严格执行，需要逐次创建后回读。
- 输出评测目前是确定性合同样例，尚无 provider-backed 执行结果和人工盲审结论。
- `agents/interface.yaml` 是 Yao 通用适配器约定；本包以 Codex 原生 `agents/openai.yaml` 为权威，不复制第二份元数据。

# 双层编排规范职责矩阵

本表用于维护“一个语义只有一个权威来源”。入口和其他 reference 只能摘要并链接，不复制完整定义或 schema。

| 语义 | 唯一权威来源 |
|---|---|
| PMO 选择、职责与高层产品循环 | `pmo/SKILL.md` |
| PMO Work Item、DAG、依赖与等待证明 | `pmo/references/delivery-dag.md` |
| PMO 周期状态、可组合动作、仓库级授权与人类通信 | `pmo/references/event-contract.md` |
| PMO Owner 生命周期与跨 Skill 兼容 | `pmo/references/owner-lifecycle.md` |
| PMO 增量审计、checkpoint 与反馈聚合 | `pmo/references/automation.md` |
| Unit Owner 选择、职责与稳定身份摘要 | `tasks-owner/SKILL.md` |
| Owner 完整控制循环、合法终态与执行复盘 | `tasks-owner/references/operations.md` |
| Issue readiness 与系统性不变量闭包触发 | `tasks-owner/references/issue-readiness.md` |
| 执行模式、容量、紧密批次、拆分与 stacked convergence | `tasks-owner/references/scheduling.md` |
| governing invariant、scope、finding 与同链修复预算 | `tasks-owner/references/scope-integrity.md` |
| 系统性闭包语义、运行证据、preflight 与独立审查 | `tasks-owner/references/runtime-and-review-evidence.md` |
| Owner 准入、消息、收口与反馈 locator | `tasks-owner/references/contracts.md` |
| Owner Heartbeat、checkpoint 与 handoff | `tasks-owner/references/automation.md` |
| 跨 Skill 能力、机器字段、准入、稀疏增量与反馈授权 | `tasks-owner/references/dev-orchestration-contract.json` |
| Codex App 模型、工具、等待、重试、验证与反馈写入 | `tasks-owner/references/codex-app.md` |

## 维护规则

- 先修改权威来源，再更新直接引用和结构化回归；不得在入口新增第二份字段表。
- 历史版本变化放入 Release Notes、评测 history 或报告，不以“v0.x 行为”章节常驻入口。
- 删除重复定义前必须确认权威替代物可发现；不保留兼容 wrapper、迁移注释或第二个索引。
- 确定性校验检查权威文件、交叉引用和重复 schema；不以固定行数或特定措辞判定通过。
- Codex App 是当前已验证平台；`agents/openai.yaml` 只是 Codex 元数据，不代表额外运行平台。

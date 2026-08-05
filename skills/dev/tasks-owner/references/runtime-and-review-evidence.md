# 运行证据、实现包与独立审查

在派发后、接受任务或审查结果前读取本文件。它是局部证据门禁，不能替代
GitHub truth、admission、`owner_runtime_lock`、依赖、消息交付或 closeout。

- [Runtime evidence gate](#runtime-evidence-gate)
- [五段局部 implementation packet](#五段局部-implementation-packet)
- [Acceptance-derived review preflight](#acceptance-derived-review-preflight)
- [Scope integrity evidence](#scope-integrity-evidence)
- [Fresh exact-head review](#fresh-exact-head-review)
- [Requested vs observed isolation](#requested-vs-observed-isolation)

## Runtime evidence gate

Owner 先回读宿主公开的 thread/spawn/details metadata，再接受任何任务或 review
结果。对准本次目标 turn、当前 `contract_revision`/`contract_digest`、
`runtime_lock_revision` 和执行 epoch，不把整条长期线程的每个 `turn_context` 当作必须
全局唯一的证据。

必须核对实际值，而不是同名角色：

- `thread_id` 或 `agent_id`、角色或任务类型；
- `model`、`reasoning_effort`；
- 绝对 `cwd`、正式 worktree、当前 `head` 与目标 `head`；
- 使用 custom agent 时的实际 agent config/profile locator；
- review 还要记录 requested/observed sandbox 与 permission（见下文）。

公开 metadata 缺字段时，只可使用宿主可访问的 allowlisted、只读本地运行证据补齐缺失
字段。该 fallback 只输出上述路由字段及 sandbox/permission，不输出 prompt、消息、env、
token、配置正文或任意 rollout payload；不要新增 inspector，也不要假定本地 JSONL
结构。公开与本地证据同时存在时必须逐字段一致。

以下任一情况都 fail closed：字段缺失、同一目标出现多个无法消歧的记录、公开/本地矛盾、
角色或任务类型不符、custom config/profile locator 不符、`cwd`/worktree/head 错配，或
无法确定目标 turn/epoch。
runtime evidence 是现有 canonical `owner_runtime_lock` 的消费门禁，不替代回显锁，也
不能改用发送方 runtime。锁仍按 [contracts.md](contracts.md#canonical-owner-runtime-lock-回显锁)
核验。

证据载体可保存完整 allowlisted routing record；Owner checkpoint 只保留：

```text
runtime_evidence_locator: <public metadata 或 allowlisted local evidence 定位>
runtime_evidence_status: <verified | unverified | failed>
runtime_evidence_target: <thread/agent + target turn/head + contract digest + lock revision/epoch>
```

不得在 checkpoint 存 prompt、完整消息、env、token 或完整 rollout 日志。`unverified` 不
得让受影响执行单元通过 admission、接受其结果或执行外部动作；该单元只能停在只读等待/
补证据，其他无冲突单元继续。

## 五段局部 implementation packet

App Task 合同、`direct` Subagent 和 `hierarchical` 下游 Subagent 的局部实现包都必须按
以下顺序填写；中文优先，协议字段保留英文：

```text
OBJECTIVE
<可观察的目标及其用户价值>

FILES AND OWNERSHIP
<准确文件/模块清单；写入者、并发编辑和越界禁止>

INTERFACES
<签名、类型、schema、命令和必须保持的兼容行为>

CONSTRAINTS
<仓库规则、安全边界、非目标、已确定的设计选择>

VERIFICATION
- Run/Check: <准确命令或检查>
  Success: <具体、可观察的成功判据>
- Inspect: <准确文件、diff 或 artifact>
  Success: <具体证据>

RETURN
STATUS: complete | partial | blocked
CHANGES: <按实际 diff 的文件级摘要>
VERIFIED: <准确命令及具体证据>
JUDGMENT CALLS: <合同未定事项或 none>
GAPS: <未完成项、歧义或 none>
```

`VERIFICATION` 的每一项必须同时有准确命令/检查和 concrete success criterion；只有
“已测试”或“看起来通过”不能 admission 或接受。该 packet 只补充局部实现合同；Owner
仍须按既有流程回读 diff、文件范围、workspace/head 和必要验证，并遵守依赖、消息交付、
admission 与 closeout。

## Acceptance-derived review preflight

首次独立 review 前，任务/Owner 必须从当前 batch 的 acceptance/backlog matrix 生成一份可回读的 preflight
evidence locator。它至少覆盖：

```text
acceptance_success_failure_unavailable -> evidence/check
trust-boundary ordering              -> evidence/check
negative matrix                      -> evidence/check
fixture isolation and restoration    -> evidence/check
resource release                     -> evidence/check
project invariant                    -> evidence/check
recent same-class findings           -> evidence/check
```

没有这些证据，不派 review；`preflight_status` 只能是 `ready | missing | failed`，不能用“任务已完成”、
readiness、CI 或旧 review 替代。preflight 不替代 CI、hosted checks、fresh exact-head、scope integrity
或 PR metadata。

若首次独立 review 为 `fix-first`，Owner 必须先做 sibling/systemic scan，再完成一个有界修复并重新生成
fresh preflight/review。第二次实质 finding（不是同一 `blocker_class` 的重复说明）触发 Owner `rethink`、
`split`、`reassign` 或 `user_decision`；不得继续让 reviewer 探测式循环。重复同一 blocker 仍遵循
[scope-integrity.md](scope-integrity.md) 的 circuit breaker。

最小审查记录增加：

```text
preflight_locator / preflight_status / preflight_revision
review_cycle: first | fix_first | second_substantive
blocker_classes_seen / sibling_scan_locator / bounded_fix_locator
review_churn_action: continue | rethink | split | reassign | user_decision
```

## Scope integrity evidence

Scope integrity 是独立语义门禁，不由 runtime、digest、exact head、测试、CI 或 code review 代替。
唯一行为规则、强制时点、四面比较、material delta、结论枚举和 repeat/downstream 处理见
[scope-integrity.md](scope-integrity.md)。本文件只记录 runtime/review 需要引用的最小 locator：

```text
semantic_scope_checkpoint: <revision>
semantic_scope_status: aligned | shrink | split | reassign | user_decision
semantic_scope_evidence_locator: <scope-integrity checkpoint>
```

独立 reviewer 可以验证当前 head 的 scope evidence，但 Owner 仍负责最终归属决定；change set、合同语义、
GitHub truth 或相邻 ownership 任一变化都会使旧 checkpoint 过期。普通提交元数据、CI 状态或未改变语义
的文档证据更新不使其过期。

## Fresh exact-head review

对需要独立审查的 `direct`、`flat` 或 `hierarchical` 交付统一使用：

```text
reviewed_head: <exact commit SHA>
reviewed_files: <被审 change set 的准确文件清单>
review_write_scope: empty
diff_locator: <完整 diff/PR/commit 定位>
verdict: ship | fix-first | rethink
semantic_scope_status: aligned | drift
```

审查请求必须绑定 `reviewed_head`、`reviewed_files`、空写入范围、完整 diff locator 和 scope integrity evidence；reviewer 只能基于该
快照返回 `ship`、`fix-first` 或 `rethink`，并分别给出 `semantic_scope_status`。之后被审查 change set 的 diff 或 head
发生变化都会让旧 verdict 立即失效，修复或 rebase 后必须重新派发 fresh review。reviewer 不得实现自己的
修复；Owner 负责判断 findings、决定修复并重新派发。

fresh context 只表示新上下文，不得声称 Sol-on-Sol 是模型族独立。按风险决定是否需要
独立 review；微小 carrier、closeout 或其他低风险改动不强制使用 Sol reviewer，也不改变
现有 Owner、任务线程和 Subagent 默认模型策略。

## Requested vs observed isolation

review 合同分别记录：

```text
requested_sandbox: <请求值>
requested_permission: <请求值>
observed_sandbox: <宿主回读值>
observed_permission: <宿主回读值>
```

只有 `observed_sandbox: read-only` 才能称为 enforced read-only。宿主放宽请求时，仅在
低风险、无需强隔离、review prompt 明确禁止写入且 Owner 精确比较 repo/worktree/artifact
前后状态均无变化时，才可按 behaviorally read-only 继续；必须报告 observed 值和 residual
risk。前后状态不能证明家目录、临时目录或外部系统没有副作用。

高风险、要求强隔离、sandbox 不可观察、`cwd`/worktree/head 错配，或发现任意 mutation 时，
立即停止该 review，不接受 verdict；不要把“请求只读”写成“已 enforced”。

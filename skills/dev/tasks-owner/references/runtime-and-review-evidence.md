# 运行证据、系统性闭包与独立审查

本文件是运行证据、`systemic_invariant_closure` 语义、preflight 和 fresh exact-head review 的唯一权威来源。
闭包字段集合以 [dev-orchestration-contract.json](dev-orchestration-contract.json) 为唯一机器 schema；下列视图直接投影该
schema，可执行正向示例是 `evals/dev_orchestration_cases.jsonl` 中的 `systemic-closure-complete`。具体平台参数见
[codex-app.md](codex-app.md)。

## 运行证据

创建、恢复、消息触发及接受结果前，回读目标任务/Agent、角色、运行 profile、绝对工作树、branch/head、合同
revision/digest 和执行代次。公开 metadata 缺字段时，只可使用宿主允许的只读本机证据补齐最小路由字段，不读取
或保存 prompt、消息、env、token 或完整 rollout。

缺失、矛盾、无法消歧、工作树/head 错配、未知 profile 或静默 fallback 都只隔离受影响任务；不消费结果、不
准入、不 merge/closeout，也不自动改配置、重启或换 profile。checkpoint 只保存 evidence locator、状态和目标。

## 系统性不变量闭包

readiness 判定需要闭包时，正式 writer admission 前形成：

```text
systemic_invariant_closure:
  governing_invariant_locator: <全称不变量>
  subject: <受约束事实>
  coverage: <适用生命周期和范围>
  ordering: <必须先后顺序>
  failure: <拒绝、回滚或无副作用规则>
  surfaces:
    - lifecycle_surface: <create | persist | restore | migrate | delete | other>
      implementation_variant: <默认或替代实现>
      consumer_or_effect: <消费方或副作用>
      code_locator: <准确代码位置>
      positive_check: <成功证据>
      negative_or_unavailable_check: <失败/不可用证据>
      no_side_effect_check: <失败时无错误副作用证据>
      status: <covered | not_applicable>
      basis: <not_applicable 时依据>
  invariant_closure_digest: <规范内容摘要>
  status: <ready | incomplete | invalidated>
```

所有适用 surface pair 必须 covered，正向、负向/不可用、ordering 和 no-side-effect 证据齐全。多个只读探索可以
并行，Owner 只汇总一张矩阵；正式实现仍使用一个稳定 Unit、writer 和 convergence chain。checkpoint 只保存
invariant/closure locator、digest 和 status。

首次 review 若发现同一不变量遗漏，旧矩阵失效；完整刷新所有适用面，把同链缺口合并进唯一一次有界修复，再生成
fresh preflight。再次遗漏必须 `systemic_invariant_closure_incomplete` / `review_churn_action: rethink`，
不能换路径、PR、reviewer 或 generation 重置预算。

## 审查前核验

writer 结束后、首次独立 review 前，从验收矩阵生成：

```text
acceptance -> invariant -> code locator -> positive/negative/unavailable check
trust-boundary ordering -> evidence
no-side-effect / resource release -> evidence
systemic closure -> locator/status 或 not_applicable + 理由
bounded sibling scan -> locator/status/disposition
```

sibling scan 只检查与当前验收和 governing invariant 直接相关的相邻实现、Store/codec、adapter、恢复/幂等与
副作用路径，不做无目标全仓审计。缺证据或未处置的当前验收问题时不派 review。

## 精确版本独立审查

审查必须绑定 exact commit、准确文件清单、完整 diff locator、空写入范围、writer terminal 证据、preflight 和
语义范围证据。Reviewer 只返回 `ship | fix-first | rethink | blocked` 及 findings，不自行修复。

任何 diff/head 变化都会使 verdict 失效。首次 fix-first 后，Owner 先处置 finding、刷新相关闭包/sibling scan，
合并为唯一一次有界修复，再重新审查。同一 Unit/收敛链第二次 finding 驱动写入被禁止；剩余问题按
shrink/split/reassign/defer/reject/user decision 处理。

## 验证权威与 readiness 分层

有效验证权威严格按以下顺序解析，命中第一个可回读来源后停止：用户明确要求 → Issue acceptance → 最近的 `AGENTS.md`/项目验证配置 → Skill 默认。低优先级来源不能扩大高优先级要求；每次 merge 记录所有输入 locator、effective source/locator 与实际 required checks。

- product readiness：只由当前 acceptance 与产品效果证据决定；merge check 或无关基线失败不能回滚已成立的产品事实。
- merge readiness：要求 writer quiescence、fresh exact-head review、PR metadata，以及有效权威或 branch protection 实际要求的 checks。
- release readiness：merge 后另以 exact-main、artifact/ledger、release/security/clean-host 合同核验；不能从 product/merge ready 推断。

Hosted CI 只有在有效权威、branch protection、release 或 security 合同明确要求时才是当前 merge/release 的硬门；merge 事实把 effective-authority checks、branch-protection checks 和 security-contract checks 分别绑定各自 source locator，低优先级仓库默认不能冒充高优先级权威扩张要求。否则失败作为独立 backlog 事实，不建立当前产品 blocked-by，也不询问用户是否继续。required check 与 PR metadata 必须成功并绑定当前 exact head；额外非 required check 即使失败也只进入带 carrier 的独立 backlog，不否定 product readiness。

本地或 Hosted 验证证据只有在 `tree_digest + acceptance_digest + environment_class` 三者相同且 evidence locator 可回读时才可复用。复用不替代 fresh exact-head review、当前 required-check SHA 或 PR metadata；任一键变化只刷新受影响验证，不自动全量重跑。

requested 与 observed sandbox/permission 分开记录。只有宿主回读为只读才能称强隔离；低风险行为只读 fallback
必须比较仓库/工作树前后状态并报告残余风险，高风险或状态不可观察时不接受审查结论。

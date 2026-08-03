# 收口后现场清理合同

Owner 完成 GitHub 与仓内 closeout 回读后使用。本合同只清理当前 Work Item 已确认的 Git
worktree、本地分支和远程分支，不清理任务线程、tag、release、缓存或其他目录。

## 授权与身份

- Owner 初始化或批次确认时，让用户分别确认 `local_worktree`、`local_branch`、
  `remote_branch`；远程删除和 rewritten merge 后的精确本地 ref 删除必须显式为 `allow`。
- 只接受精确目标，不接受 glob、前缀、当前分支或“所有已合并分支”。授权写入 Owner 合同：

```text
cleanup_key: <task_key>:cleanup:<closeout_generation>
cleanup_generation: <单调递增>
task_key: <稳定 Work Item>
repo_root / remote_url / remote_name
pr_url / pr_state: merged / pr_head_oid / merge_commit / base_branch / target_branch
worktree_path / local_branch / local_oid / remote_ref / remote_oid
cleanup_policy:
  local_worktree: delete | preserve
  local_branch: delete | preserve
  remote_branch: delete | preserve
  verified_rewritten_merge_delete: allow | forbid
cleanup_authority_locator / revision
```

- 所有模式都由主 Owner 直接 `spawn_agent` 创建清理 Subagent，默认 Luna/max、
  `fork_turns: "none"`、禁止继续衍生。任务线程及其 Subagent 不能获得清理权。
- 清理 Subagent 必须从不在删除目标中的稳定 repo checkout/管理目录运行；自身 cwd 等于目标
  worktree、位于其内部或 repo root 本身就是目标时，返回 `cleanup_blocked`。

## 删除前门禁

先只读 inventory，并把每项绑定到 exact locator/OID：

1. Owner 已记录 `closeout_verified`；PR 确为 merged，PR head、merge commit、base/target 与合同
   一致，issue/carrier 已收口。
2. 目标只能是该 Work Item 创建或明确接管的 source branch/worktree；default、base、target、
   protected branch、tag 和仓库根永不删除。
3. 任务线程和全部相关 Subagent 已结束；没有活动 task、checkpoint、workspace_entry、开放 PR、
   其他 worktree 或 cleanup lane 引用目标。
4. worktree 没有 tracked/untracked 改动、未完成 merge/rebase/cherry-pick/bisect 或嵌套仓库；
   不自动 stash、commit、reset、checkout 或清除文件。
5. local ref 和 remote ref 仍等于合同 expected OID；本地没有 PR head 之后的新提交，远程没有
   closeout 后漂移。无法证明提交已被 exact merged PR 消费时停止。

任一检查不成立即 `cleanup_blocked`；记录具体资产、当前/期望身份、证据定位和需要谁决定，
不得放宽目标或改用相似名称。若可在既有合同和授权内安全纠正，例如改从稳定 cwd 重新派发，
Owner 应直接纠正并重跑门禁，不把可执行动作转交用户。

## 执行顺序与删除边界

每仓库一次只运行一个 cleanup lane，并固定执行：

1. 再次回读 `git worktree list --porcelain`、精确 local/remote ref、PR 与 target head。
2. 对 `local_worktree: delete` 使用 Git 原生命令非强制移除精确 worktree；禁止 `rm -rf` 和
   force-remove。已不存在且身份无冲突记为 `already_absent`。
3. 对 `local_branch: delete` 先尝试安全删除。若仅因 squash/rebase merge 导致祖先检查失败，
   只有 `verified_rewritten_merge_delete: allow`、PR merged、local OID 等于 exact PR head OID、
   没有新提交且已记录恢复 OID 时，才允许按 expected OID 删除该精确 local ref；其他
   force-delete 一律禁止。
4. 对 `remote_branch: delete` 先回读 exact remote OID，并用 expected OID 的 compare-and-delete/
   lease 语义删除；远程已自动删除记为 `already_absent`。OID 漂移或宿主无法保证 compare-and-delete
   时停止，禁止盲删。
5. 每步完成后立即回读；后一步失败不回滚前面已成功的删除，也不切换目标。

删除前保存 local/remote OID。需要恢复时只提供基于该 OID 的恢复建议，不自行重建分支或
worktree；对象不可达或已被回收时不得承诺可恢复。

## 结果、幂等与 Owner 验收

每项资产只取以下状态：`present | removed | already_absent | preserved | blocked`。部分成功记为
`cleanup_partial`；重跑同一 `cleanup_key/generation` 时只处理仍为 `present/blocked` 且门禁重新
通过的资产，不重复删除 `removed/already_absent`，不无限重试。

Subagent 返回 pre/post locator、删除前 OID、每项状态、执行结果、未删资产和恢复建议。Owner
不得只信摘要，必须从稳定 checkout 独立回读：

- `git worktree list --porcelain` 不再包含目标 path；
- exact local ref 不存在或按策略为 `preserved`；
- exact remote ref 不存在或按策略为 `preserved`；
- target/default branch、target head、repo root 和其他活动 worktree 未变化；
- GitHub PR/issue 和 repo carrier 仍保持 closeout 状态。

全部授权目标为 `removed/already_absent/preserved` 且无身份漂移时记为 `cleanup_verified`。
脏数据、活动引用、权限失败或强制动作超出策略时保持 `cleanup_blocked`/`cleanup_partial`。
Owner 先完成只读诊断；需要用户决定时必须给出：阻塞事实与证据、对完成状态和数据的影响、
可选路径及风险/可逆性、明确的最优建议与理由、所需精确授权、未回复时的安全默认动作和
`wake_condition`。默认建议保留有争议或身份漂移的资产；只有证据证明目标和恢复边界且用户
明确授权时才建议丢弃数据或扩大删除权限。不能用清理失败降低实现并发或阻塞其他无冲突任务。

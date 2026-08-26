# Merge 后清理

cleanup 是 closeout 后的独立、串行、可恢复通道，不计实现进展。没有用户授权不删除本地或远程分支、worktree、
stash、临时目录、缓存或宿主线程。

## 前置条件

- 产品验收、merge commit、target head、Issue/PR 状态和 carrier 已由 Owner 独立回读；
- 当前 generation 的所有 writer/任务已 terminal，completion 已消费；
- cleanup 合同列出 exact path/ref/OID、目标仓库、动作和 `delete | preserve` 策略；
- 保护分支、共享 worktree、他人引用、未提交修改和并发写入检查通过。

cleanup 使用平台的 worker profile 和原生 completion 能力，但不得修改代码、GitHub 规划真相、PR、Issue、
发布内容或 target branch。

## 执行与回读

按 worktree、remote ref、local ref、临时资产的安全顺序逐项处理；每项先核对 exact identity，范围漂移即跳过并
记录原因。部分失败不回滚已安全完成的删除，也不扩大重试范围。

Owner 最后独立回读目标 head 未变、工作树策略、local/remote ref 状态和残余资产。只有全部符合合同，或用户明确
选择全部 preserve，才可标记 cleanup complete；partial/blocked 不能冒充目标完成。

# CodeAtlas

CodeAtlas 是一个面向 Codex 与 Claude Code 的只读代码地图插件。它只有一
个私有 Skill：`code-atlas`，按 UNDERSTAND、TRACE、CHANGE、ASSESS 四路
组织仓库探索、请求追踪、变更影响和维护性决策。

## 运行边界

CodeGraph 是可选的外部运行时依赖，不随插件分发。只有当前 worktree 同时
具备 `codegraph` CLI 和精确文件 `<worktree-root>/.codegraph/codegraph.db`
时，图证据才可用。CodeAtlas 不读取 `CODEGRAPH_DIR`，不借用父目录或其他
worktree 的索引。原生 MCP 由宿主提供，运行时通过 `tools/list` 协商；默认
只使用可见的 `codegraph_explore`，其他工具必须先确认实际可见。

没有 CLI 或索引时，继续做保守的本地文件/Git 分析并诚实标为
`unavailable`；CLI 与索引存在但没有明确 MCP 运行时证据时标为
`cli-only`。所有结论标注 `observed`、`inferred` 或 `unknown`。

插件不声明或分发 MCP server，不执行 CodeGraph 子命令，不初始化索引，不
安装软件，不启动 daemon/watcher，也不创建 issue。生命周期 hook 只读识别
cwd、Git worktree/common-dir、PATH 中的 CLI 和精确数据库文件，静默失败且
不写 stderr。任何安装、`codegraph install` 或
`codegraph init <worktree-root>` 都要先说明官方来源、准确写入范围（可能写入
worktree 的 `.codegraph`、`.gitignore` 并执行完整 build）和副作用（可能提示
watcher/Git hook、host 配置、telemetry 或 daemon），再取得用户授权；初始化
命令不带 `-i`。
双宿主只注册一次 `hooks/claude-codex-hooks.json`；它不是标准自动加载的
`hooks/hooks.json` 路径，命令直接调用 Node runner 并显式传入事件名。

## 安装

```bash
# Codex
codex plugin marketplace add MC-and-his-Agents/MC-AGENT-KIT --ref main
codex plugin add code-atlas@mc-agent-kit

# Claude Code
claude plugin marketplace add MC-and-his-Agents/MC-AGENT-KIT
claude plugin install code-atlas@mc-agent-kit
```

CodeGraph 的安装是独立且需授权的动作。需要时先说明官方包来源
`@colbymchenry/codegraph`、安装位置和副作用，再由用户决定是否执行。

## 四路工作流

| 路由 | 适用场景 | 主参考 |
|---|---|---|
| UNDERSTAND | 陌生仓库、模块、架构、入口 | `skills/code-atlas/references/exploration.md` |
| TRACE | 请求、路由、符号、bug 调用路径 | `skills/code-atlas/references/trace-and-debug.md` |
| CHANGE | 重命名、删除、重构、影响、测试计划 | `skills/code-atlas/references/change-analysis.md` |
| ASSESS | dead code、测试选择、坏味道、技术债务 | `skills/code-atlas/references/maintainability.md` |

普通场景只加载一份主参考；跨场景时才组合 `dead-code.md`、
`test-selection.md` 或 `codegraph.md`。

## 只读扫描器

旧 standalone 维护性 Skill 的必要知识、七个 scanner、两个 JSON schema 和
示例配置已迁入 `skills/code-atlas/`。脚本只读目标仓库并把 JSON 打到
stdout：

```bash
cd plugins/code-atlas/skills/code-atlas
python3 scripts/scan-size-complexity.py <target>
python3 scripts/scan-duplication.py <target>
python3 scripts/scan-dependencies.py <target>
python3 scripts/scan-tests.py <target> --repo <worktree-root>
python3 scripts/scan-literals-comments.py <target>
python3 scripts/scan-git-churn.py <target> --repo <worktree-root>
python3 scripts/build-evidence-pack.py --target <target> <reports...>
```

扫描结果是候选证据，不是结论。默认只输出决策报告，不改代码、不创建或
发送 issue、不运行 mutating formatter；维护性报告必须给出 Fix Now、
Refactor Before Next Change、Track as Tech Debt、Accept / Ignore 或 Needs
Human Judgment 之一。

## 参考与契约

- `references/codegraph.md`：worktree-local 索引、MCP 协商、CLI-only 和授权边界。
- `references/exploration.md`：UNDERSTAND。
- `references/trace-and-debug.md`：TRACE。
- `references/change-analysis.md`：CHANGE。
- `references/dead-code.md`：dead-code 误报过滤。
- `references/test-selection.md`：最小测试选择。
- `references/maintainability.md`：smell catalog、evidence dimensions、决策和报告。

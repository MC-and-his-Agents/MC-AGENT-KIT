# GPT-5.6 Luna 原生 Subagent 门禁

在首次创建 Subagent 前读取。任务线程使用 Luna 不依赖本门禁；本门禁只判断当前 Codex
进程的原生 `spawn_agent` 能否接受 `gpt-5.6-luna / max`。配置文件是诊断和调整输入，当前
进程的原生创建结果才是最终证据。

## 当前进程优先

按以下顺序判断，不要因为缺少既有冒烟记录就要求重启：

1. 当前进程已有原生 `spawn_agent(model="gpt-5.6-luna",
   reasoning_effort="max")` 成功证据时，记为 `supported`，直接复用，不重复冒烟。
2. 当前宿主的原生 Subagent 能力元数据或 `turn_context` 已声明 Luna/max、Luna v2 或等价
   支持，但尚无成功创建证据时，记为 `probe_ready`；立即进入“原生验证”，不要求重启。
3. 用户已确认本批模型和模式，且已有一个符合合同的真实 Subagent 任务时，首次真实
   `spawn_agent` 可以同时作为验证；否则创建只读冒烟任务。
4. 原生创建成功且未出现 `Unknown model gpt-5.6-luna` 后记为 `supported`。创建失败先分类：
   `Unknown model`/模型组合不受支持才进入模型目录诊断；容量、权限、网络、workspace 或其他
   失败按其真实原因处理，不得推导为需要重启或 Luna 不受支持。

## 模型目录诊断与选择

只有当前进程未声明支持，或原生创建返回 `Unknown model gpt-5.6-luna` 时，才读取模型目录：

1. 解析 `~/.codex/models_cache.json`，要求恰好存在一个 `slug: "gpt-5.6-luna"` 的模型对象，
   并报告其 `multi_agent_version`。缺文件、缺模型、重复模型或未知版本时停止，不修改配置。
2. 若 `config.toml` 已指向 `models_cache-luna.json`，确认它与当前原缓存相比仍只有 Luna 的
   版本差异；漂移时报告差异，不静默重建。
3. 有效目录已经把 Luna 标为 `v2`，但当前进程能力仍未反映，或本流程刚修改目录/config
   且当前进程尚未加载时，记为 `pending_restart`。只有这种情况才告诉用户重启并暂停。
4. 原缓存为 `v1` 且没有有效覆盖时，先让用户选择：
   - 本批次 Subagent 使用 `gpt-5.6-terra / xhigh`；
   - 使用用户指定的其他模型与推理程度；
   - 执行下列 Luna v2 本地目录调整。

用户未选择时不创建 Subagent，也不修改 `~/.codex`。

## 受控调整

只有用户选择调整后执行：

1. 将 `~/.codex/models_cache.json` 复制为 `~/.codex/models_cache-luna.json`。
2. 只在副本的 Luna 对象中把 `"multi_agent_version": "v1"` 改为
   `"multi_agent_version": "v2"`；不得修改原缓存或其他模型对象。
3. 在 `~/.codex/config.toml` 的首个 TOML table 之前添加顶层
   `model_catalog_json = "models_cache-luna.json"`，保留其他配置。已有相同值时不重复写；
   已有不同值时报告冲突并等待用户确认，不覆盖。
4. 使用 JSON 解析器和 Python 标准库 `tomllib` 验证两个文件。比较原缓存与副本，确认模型
   数量、顺序及所有字段都相同，唯一值变化是 Luna 的
   `multi_agent_version: v1 -> v2`；展示 `diff -u` 的精确差异。
5. 不自行重启 Codex，不修改全局默认 Subagent 模型，也不创建自定义 `agent_type`。
6. 修改后重新检查当前进程能力：若已经声明 Luna/max，立即原生验证；否则记为
   `pending_restart`，告诉用户需要重启并暂停。不得把“本流程写过配置”本身当作重启已发生。

## 原生验证与重启恢复

- `probe_ready`：立即使用原生 `spawn_agent`，显式传递 `fork_turns: "none"`、
  `model: "gpt-5.6-luna"`、`reasoning_effort: "max"`。没有真实任务可兼作验证时，测试任务只
  读取当前生效的模型目录文件，并简短返回 Luna 的 slug 与 `multi_agent_version`。
- `pending_restart`：告诉用户需要重启并暂停。用户明确回复“已重启”后，先重新检查当前进程
  能力，再执行同一原生验证；不得仅凭“已重启”或配置文件为 v2 记为 `supported`。
- 原生创建成功且没有 `Unknown model gpt-5.6-luna` 才记为 `supported`。若重启后仍返回
  `Unknown model`，保留证据并让用户选择 Terra、其他模型或停止；不得形成重复重启循环。

## rollback boundary

调整不改写原缓存。需要回滚时，先取得用户明确授权，再移除 `config.toml` 中本流程写入的
`model_catalog_json` 行；`models_cache-luna.json` 是否删除由用户决定。不得自动回滚或重启。

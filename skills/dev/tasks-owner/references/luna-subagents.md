# GPT-5.6 Luna 原生 Subagent 门禁

在首次创建 Subagent 前读取。任务线程使用 Luna 不依赖本门禁；本门禁只判断原生 `spawn_agent` 能否接受 `gpt-5.6-luna / max`。

## 预检与选择

1. 解析 `~/.codex/models_cache.json`，要求恰好存在一个 `slug: "gpt-5.6-luna"` 的模型对象，并报告其 `multi_agent_version`。缺文件、缺模型、重复模型或未知版本时停止，不修改配置。
2. 已有当前 Codex 进程启动后的原生 Luna 冒烟成功证据时，记为 `supported`。
3. 若 `config.toml` 已指向 `models_cache-luna.json`，先确认它与当前原缓存相比仍只有 Luna 的版本差异；有效时直接进入“重启与原生验证”，漂移时报告差异，不静默重建。
4. 原缓存的 `multi_agent_version` 为 `v2` 且无当前进程证据时，不创建覆盖文件、不修改配置，进入“重启与原生验证”。
5. 原缓存为 `v1` 且没有有效覆盖时，先让用户选择：
   - 本批次 Subagent 使用 `gpt-5.6-terra / xhigh`；
   - 使用用户指定的其他模型与推理程度；
   - 执行下列 Luna v2 本地目录调整。

用户未选择时不创建 Subagent，也不修改 `~/.codex`。

## 受控调整

只有用户选择调整后执行：

1. 将 `~/.codex/models_cache.json` 复制为 `~/.codex/models_cache-luna.json`。
2. 只在副本的 Luna 对象中把 `"multi_agent_version": "v1"` 改为 `"multi_agent_version": "v2"`；不得修改原缓存或其他模型对象。
3. 在 `~/.codex/config.toml` 的首个 TOML table 之前添加顶层 `model_catalog_json = "models_cache-luna.json"`，保留其他配置。已有相同值时不重复写；已有不同值时报告冲突并等待用户确认，不覆盖。
4. 使用 JSON 解析器和 Python 标准库 `tomllib` 验证两个文件。比较原缓存与副本，确认模型数量、顺序及所有字段都相同，唯一值变化是 Luna 的 `multi_agent_version: v1 -> v2`；展示 `diff -u` 的精确差异。
5. 不自行重启 Codex，不修改全局默认 Subagent 模型，也不创建自定义 `agent_type`。

## 重启与原生验证

告诉用户必须重启 Codex，并暂停。只有用户明确回复“已重启”后才继续：

1. 选择本次生效的模型目录文件作为只读测试文件：未创建覆盖时用 `~/.codex/models_cache.json`，已调整时用 `~/.codex/models_cache-luna.json`。
2. 使用原生 `spawn_agent` 创建一个只读测试 Subagent，显式传递 `fork_turns: "none"`、`model: "gpt-5.6-luna"`、`reasoning_effort: "max"`。任务只读取该文件，并简短返回 Luna 的 slug 与 `multi_agent_version`。
3. 只有创建成功且未出现 `Unknown model gpt-5.6-luna` 才记为 `supported`；失败时保留证据并重新让用户选择 Terra、其他模型或停止。

## rollback boundary

调整不改写原缓存。需要回滚时，先取得用户明确授权，再移除 `config.toml` 中本流程写入的 `model_catalog_json` 行；`models_cache-luna.json` 是否删除由用户决定。不得自动回滚或重启。

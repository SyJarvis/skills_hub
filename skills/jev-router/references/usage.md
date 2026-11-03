# 使用 Jev 路由工作代理

本技能位于项目 `/Users/mac/research/.agents/skills/jev-router`。在该项目的新 Codex 会话中可以显式调用：

> 使用 $jev-router 完成这个任务。主代理负责拆分和验收，由 Jev 选择工作代理模型，任务期间固定模型，允许在轮次之间调整推理强度。

技能保留默认的自动发现行为。它不会拦截所有原生子代理调用，也不会修改 `AGENTS.md` 或 Codex 配置；主代理需要遵循技能流程，调用配套脚本。

## 前提与决策范围

需要 macOS 或 Linux、Python 3.11 及以上、已登录且支持 App Server 的 `codex` CLI，以及可用的 `TYPESAFE_API_KEY` 环境变量。脚本只使用 Python 标准库；`codex` 必须在 `PATH` 中。以下 `python3` 命令应指向满足版本要求的解释器。密钥应由用户在运行 Codex 的环境中设置，不要复制示例代码中的实际密钥。

`references/routing-policy.json` 保存模型和 effort 的路由说明。脚本只选择实时目录中可用且策略中有说明的模型，只使用所选模型实际支持的 effort。`gpt-6-luna` + `high` 是用户选择的比较基准；Jev 路由不是无条件强制使用该组合。基准不可用时必须披露，不能把它自动改写为 `gpt-5.6-luna`。初始策略还包含 `gpt-6-astra`、`gpt-6-sol`、`gpt-5.6-sol`、`gpt-5.6-luna`，作为不同型号参与选择。如果没有合法候选，先处理候选配置或环境，再执行任务。

模型目录可能随运行环境刷新，应以本次 `models` 输出为准，不能把某次没有列出型号视为永久不可用。默认候选会排除不可用的策略模型，并在结果的 `unavailable_policy_models` 中列出。若通过 `candidate_models` 明确指定不可用型号，脚本报错。目录中列出型号表示可参与路由，实际调用是否成功仍需验证。

`--route-only` 仍然调用外部 Jev API，可能产生 API 用量；它只跳过工作代理创建。普通 `start` 还会启动 Codex 执行轮次。下面的例子不要在缺少对应用户任务时自动执行。

## 查看模型

```bash
python3 "/Users/mac/research/.agents/skills/jev-router/scripts/router.py" models \
  --cwd "/Users/mac/research"
```

## 创建任务

在任务的临时目录中写一个 JSON 文件，例如 `/Users/mac/research/work/jev-request.json`：

```json
{
  "task": "检查指定模块的边界条件，并给出有代码位置依据的结论。",
  "cwd": "/Users/mac/research",
  "context": "主代理应替换此段，提供模块路径、相关事实及本次任务边界。",
  "acceptance": [
    "指出已核对的具体文件位置",
    "区分确认的问题与待验证的推测",
    "提供实际执行的验证命令和结果"
  ],
  "sandbox": "read-only"
}
```

`task` 和已存在的绝对路径 `cwd` 必填。`context` 可省略；`acceptance` 是字符串列表，省略时为空列表。`sandbox` 默认为 `read-only`，已获用户授权的代码修改任务可明确选择 `workspace-write`，具体文件和操作仍须遵守授权范围。可添加 `candidate_models` 字符串列表来缩小候选范围，不得使用未在当前环境中确认可用的模型。

先验证路由、暂不创建工作代理：

```bash
python3 "/Users/mac/research/.agents/skills/jev-router/scripts/router.py" start \
  --request "/Users/mac/research/work/jev-request.json" --route-only
```

执行任务：

```bash
python3 "/Users/mac/research/.agents/skills/jev-router/scripts/router.py" start \
  --request "/Users/mac/research/work/jev-request.json"
```

保留输出的任务 ID。调用 shell 工具时使用短于 60 秒的等待窗口，工具返回仍在运行的进程 ID 时继续读取该进程。不要重复 `start` 代替等待。

`--route-only` 也会保存任务，状态为 `routed`。若要使用这次已经选好的模型实际执行，使用下文的 `continue`；重新调用 `start` 会创建另一个任务并重新选择模型。

## 查看状态与续跑

把命令中的 `TASK_ID` 换成 `start` 返回的真实值：

```bash
python3 "/Users/mac/research/.agents/skills/jev-router/scripts/router.py" status --task "TASK_ID"
```

主代理先审查本轮结果，再分别创建两个 UTF-8 文本文件：下一轮工作指令与决策所需的进展摘要。摘要描述已完成内容、验证结果、尚未解决的问题和下一阶段需求；不必复制完整工具日志或仓库。

```bash
python3 "/Users/mac/research/.agents/skills/jev-router/scripts/router.py" continue \
  --task "TASK_ID" \
  --input-file "/Users/mac/research/work/jev-next-turn.txt" \
  --progress-file "/Users/mac/research/work/jev-progress.txt"
```

默认由 Jev 选择下一轮 effort。若用户明确指定下一轮强度，追加 `--effort high` 等受支持值。脚本继续同一会话并保持原模型和 sandbox；不能通过更换策略文件来给已有任务换模型。环境缺少依赖、权限不足等问题要修复实际原因，不能简单提高 effort。

## 状态与故障

默认状态目录为 `${CODEX_HOME:-~/.codex}/jev-router/tasks`。可以为所有相关命令传入同一 `--state-dir` 使用另一目录。`start`、`continue` 可以用 `--policy` 指定其他策略 JSON；已有任务模型仍固定。每个任务使用独占锁，避免同时启动两个续跑轮次。

CLI 返回状态摘要，包括 `task_id`、`status`、`model`、`effort`、`thread_id`、`error`、`unavailable_policy_models`、`state_file`、`turn_count`、`last_turn` 和 `jev_usage`。完整的 `request`、`decisions`、`jev_attempts` 和 `turns` 保存在 `state_file` 指向的 JSON 文件中。摘要中的 `last_turn` 只保留最近三条执行条目；审查完整记录时读取状态文件。

`routing` 表示正在决策；`routed` 表示已选择模型但尚未执行；`running` 表示执行中；`completed` 表示最近一轮已结束，仍需主代理验收。`failed`、`blocked` 或 `unknown` 要先检查错误和已产生的修改。工作代理需要审批或用户交互时会停止并标记 `blocked`；脚本不自动批准，也不扩大 sandbox。由主代理处理具体阻塞，保持原任务的权限边界。

任务状态和执行记录可能包含工作内容，应按项目数据对待。发生超时或错误后先查状态与实际进程，确认上一轮结束，再决定是否续跑；不要自动重试一个状态不明的执行。首版没有自动恢复命令，`routing`、`running` 和 `unknown` 状态禁止直接续跑，需要人工排查。不要手动把状态改成成功来绕过该检查。`status` 命令成功读取状态时返回退出码 0，这不代表任务已成功；`start` 和 `continue` 只有在 `routed` 或 `completed` 时返回 0。

## Jev 用量记录

用以下只读命令查看任务累计用量，不会调用 Jev 或启动工作代理：

```bash
python3 "/Users/mac/research/.agents/skills/jev-router/scripts/router.py" status --task "TASK_ID" \
  | python3 -c 'import json, sys; print(json.dumps(json.load(sys.stdin)["jev_usage"], ensure_ascii=False, indent=2))'
```

`known_input_tokens`、`known_output_tokens`、`known_total_tokens` 是所有已记录 Jev 请求的已知小计，含 `continue` 的 effort 请求以及有合法 usage 但答案验证失败的请求。每个 token 字段仅接受非负整数，缺失、负数、小数、布尔值或其他非法值保存为 `null`；另一个合法字段仍保留。`unknown_usage_count` 统计至少一个 token 字段未知的请求，再加没有请求记录的历史 Jev 决策数。只有 `complete: true` 时，这些小计才覆盖该任务的全部已记录路由历史；它不表示任务执行成功，也不代表 Codex 工作代理用量或账单金额。

`attempt_count` 是 `jev_attempts` 的条目数。每条包含本地 `call_id`、问题类型 `kind`、开始时间 `started_at`、耗时 `duration_seconds`、请求模型 `model`、经字符与长度校验的响应模型 `response_model`（不可用时为 `null`）、安全状态 `status` 和 `usage`。只从 `x-request-id` 或 `request-id` 响应头提取符合长度与字符限制的 `request_id`；不会保存请求/响应正文、密钥或整组响应头。成功的 `decisions` 用 `call_id` 关联请求。手动 `--effort` 覆盖不是 API 请求。

请求发出前先保存 `started` 条目，结束或失败时立即保存结果。HTTP 错误、网络失败、不可解析响应通常没有可用 usage，必须保持未知；脚本不会为补记用量自动重试。进程被强制结束或磁盘写入失败仍可能留下 `started`，不能据此认定请求已送达、免费或未计费。HTTP 错误正文不解析用量。

旧状态文件不能补造 token。`legacy_decisions_without_attempt` 表示没有对应请求条目的历史 Jev 决策数；更早的失败请求可能连决策都未留下，无法计数。旧任务的 `history_complete` 和 `complete` 持续为 `false`，即使之后的续跑已开始记录用量。查看旧任务不会改写状态；如需追溯历史费用，应另查服务商控制台或账单，不能把已知小计的零解释成实际零用量。

## 接口依据

- [Codex Skills](https://learn.chatgpt.com/docs/build-skills)：技能发现与加载。
- [Codex App Server](https://learn.chatgpt.com/docs/app-server)：脚本管理会话，通过新轮次设置 `model` 与 `effort`。
- [TypeSafe API](https://docs.typesafe.ai/api)：Jev 的结构化候选选择及响应 `usage.input_tokens`、`usage.output_tokens` 整数字段。模型概率表达一次选择的分布，不等同于编码任务成功率。

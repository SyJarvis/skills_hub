---
name: jev-router
description: Use Jev to choose a Codex worker model for a delegated development task, keep that model fixed, and adjust reasoning effort between execution turns through managed App Server sessions. Use when the user requests Jev routing or adaptive worker reasoning.
---

# Jev Router

主代理负责理解目标、划分子任务和验收；Jev 选择工作代理模型与推理强度；配套 Python 脚本通过 Codex App Server 执行工作代理轮次。首次使用前阅读 [使用与命令](references/usage.md)。

## 执行流程

1. 将一个有明确边界的子任务写入请求 JSON：目标、工作目录、必要上下文、验收标准，以及用户已授权的 sandbox。默认使用 `read-only`；实际代码修改需要 `workspace-write`。并行任务应使用独立工作目录或互不重叠的文件范围。
2. 用本技能目录下的 `scripts/router.py models --cwd PATH` 读取实时模型目录。候选模型来自 [路由策略](references/routing-policy.json) 与实时目录的交集；不能把相似名称当作同一模型。用户选择的基准是 `gpt-6-luna` + `high`，如果环境不支持，要明确披露，不得悄悄改成其他型号。
3. 运行 `start --request FILE`，由 Jev 先选模型，再在该模型支持的强度中选 effort。记录返回的任务 ID。脚本管理的任务状态固定模型、会话和 sandbox；不通过改写全局或项目 `config.toml` 调参。
4. 通过 shell 工具以不超过 60 秒的等待区间读取执行进展。脚本可以持续运行；不要因为一次工具等待结束而重复启动相同任务。用 `status --task ID` 读取持久化状态。
5. 一轮结束后审查实际 diff、验证命令与日志、未解决的问题。若需继续，写入下一轮指令和精简进展摘要，运行 `continue`。默认让 Jev 重新选择 effort；用户明确要求时用 `--effort` 覆盖。每次续跑仍使用原任务的模型。
6. 只有主代理核对验收标准后，才能向用户宣告任务完成。`turn` 完成仅表示该轮已结束。报告实际模型、各轮 effort、修改与验证结果，以及尚未验证的部分。需要核对 Jev token 时查看 `status` 的 `jev_usage`；`complete: false` 表示只有已知小计，不能当作完整用量，详见[用量记录](references/usage.md#jev-用量记录)。

## 保持的边界

- 这些是脚本管理的 App Server 会话，不等同于原生 `spawn_agent` 子代理或桌面应用子代理界面。本技能不接管主代理、已有原生子代理，也不能修改执行中的轮次；effort 只在下一次 `turn/start` 生效。
- 工作代理直接完成分配任务，不递归调用 Jev router 或继续派生代理。遇到需换模型的情况，由主代理说明原因并创建新任务，交接必要上下文。
- Jev 会收到请求中的任务文本、必要上下文、验收标准、模型说明，以及续跑时提交的进展摘要；只传决策所需信息，避免将密钥或无关仓库内容放入这些字段。脚本不会自动将整个仓库作为 Jev 决策输入。
- `TYPESAFE_API_KEY` 只从环境变量读取。不要将实际密钥写入技能、策略、请求文件或执行日志。
- 策略描述是初始路由假设，不是经评测的价格、速度或成功率。不要把 Jev 的选择概率当作任务成功率，不以未经校准的概率阈值决定能否执行。
- 若 Jev 请求、模型校验或 App Server 调用失败，报告具体失败阶段并保留可读状态；不要偷偷降级成主代理执行、替代模型或更宽的 sandbox。需要审批或用户交互的任务会停止并标记 `blocked`，由主代理处理，不能借此扩大授权范围。

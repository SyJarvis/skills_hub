# skills_hub

面向 Codex、OpenCode 及兼容 agent 工具的可复用技能管理中心。

## 什么是 Skill

Skill 是模块化、自包含的能力包，通过指令、脚本和资源扩展 agent 的能力。每个 skill 包含一个 `SKILL.md` 文件（agent 可读的工作流定义）以及可选的 `references/`、`scripts/`、`assets/`、`tests/` 目录。

与临时 prompt 不同，skill 是可复用、可安装、可版本化的持久能力。

## 快速安装

```bash
git clone https://github.com/SyJarvis/skills_hub.git ~/.skills_hub
cd ~/.skills_hub
```

安装单个 skill（推荐使用软链接，方便开发时自动同步）：

```bash
./install.sh skill-creator --link
```

安装所有 skill：

```bash
./install.sh --all --link
```

按分类安装：

```bash
./install.sh --category testing --link
```

查看可用 skill：

```bash
./install.sh --list
```

## 安装目标

| 场景 | 目标路径 | 命令 |
|------|----------|------|
| 全局（默认） | `~/.agents/skills/` | `./install.sh <skill>` |
| 项目级 | `./.agents/skills/` | `./install.sh <skill> --project .` |
| OpenCode 专用 | `~/.config/opencode/skills/` | `./install.sh <skill> --target opencode` |
| Codex 专用 | `~/.codex/skills/` | `./install.sh <skill> --target codex` |

开发时推荐使用 `--link` 软链接安装，仓库更新后 skill 自动同步。

## Skill 列表

| Skill | 分类 | 状态 | 描述 |
|-------|------|------|------|
| skill-creator | tooling | stable | 创建有效 skill 的指南，提供专业化知识、工作流和工具集成的构建方法 |
| clean-dead-code | code-review | stable | 识别并移除死代码——未使用的导入、类、函数、配置、导出项、残留设计 |
| test-writer | testing | stable | 编写高质量测试代码——单元测试、集成测试、回归测试和异步测试 |
| coding-guidelines | coding | stable | LLM 编码行为准则——先思考再编码、简洁优先、精准修改、目标驱动 |

## 与 Agent 工具配合使用

### Codex

将 skill 安装到 `~/.agents/skills/`，然后在对话中引用：

```
使用 skill-creator 技能来创建一个新的 skill
```

### OpenCode

安装到 `~/.agents/skills/` 或 `~/.config/opencode/skills/`：

```
使用 test-writer 技能为这个模块编写测试
```

### Claude Code

安装到 `~/.claude/skills/`（手动复制或链接），然后在对话中引用 skill 名称。

## 仓库结构

```
skills_hub/
├── README.md
├── AGENTS.md              # 仓库维护规则（供 agent 读取）
├── catalog.json           # 机器可读的 skill 索引
├── install.sh             # 安装脚本
├── skills/                # 所有 skill 包
│   ├── skill-creator/
│   ├── clean-dead-code/
│   ├── test-writer/
│   └── coding-guidelines/
├── docs/                  # 人类可读的文档
├── tools/                 # 自动化工具（校验、生成、同步）
└── profiles/              # 工具专用配置说明
```

## 编写新 Skill

请参考 `docs/guide/write-skill.md` 获取详细的编写指南。

快速开始：

1. 每个 skill 放在 `skills/<skill-name>/` 下
2. 必须包含 `SKILL.md`（含 YAML frontmatter）
3. 可选目录：`references/`、`scripts/`、`assets/`、`tests/`
4. skill 名称使用小写 kebab-case
5. 描述要清晰、面向触发场景

## 校验与维护

```bash
python tools/validate_skills.py    # 校验 skill 结构
python tools/generate_catalog.py   # 重新生成 catalog.json
python tools/sync_docs.py          # 同步文档页
```

## 开源协议

MIT
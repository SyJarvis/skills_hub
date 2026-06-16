# 编写 Skill 指南

## Skill 是什么

Skill 是模块化、自包含的能力包，通过指令、脚本和资源扩展 agent 的能力。

与临时 prompt 不同，skill 是可复用、可安装、可版本化的持久能力。

## 目录结构

```
skills/<skill-name>/
├── SKILL.md          # 必需，agent 可读的工作流定义
├── references/       # 可选，长文档和参考知识
├── scripts/          # 可选，确定性辅助工具
├── assets/           # 可选，模板和静态资源
└── tests/            # 可选，示例 prompt 和预期行为
```

## SKILL.md 格式

`SKILL.md` 由 YAML frontmatter 和 Markdown 正文组成：

```markdown
---
name: my-skill
description: 简洁描述 skill 的功能和触发场景
---

# Skill 标题

## 用途
...

## 工作流
...
```

## Frontmatter 字段

| 字段 | 必需 | 说明 |
|------|------|------|
| name | 是 | skill 名称，小写 kebab-case |
| description | 是 | 描述功能与触发场景 |
| compatibility | 否 | 兼容工具列表（如 codex, opencode）|
| metadata.category | 否 | 分类 |
| metadata.stability | 否 | stable/beta/experimental/deprecated |
| metadata.tags | 否 | 标签列表 |
| metadata.version | 否 | 版本号 |

## 编写原则

1. **聚焦** — 每个 skill 只解决一个工作流
2. **面向触发** — description 要描述什么时候该用这个 skill
3. **渐进披露** — SKILL.md 保持精炼，长文档放 references/
4. **命名清晰** — 使用小写 kebab-case，如 `pr-review`、`test-writer`

## 校验

编写完成后运行校验：

```bash
python tools/validate_skills.py
```

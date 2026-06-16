# AGENTS.md

本仓库是面向 Codex、OpenCode 及兼容 agent 工具的技能管理中心。

## 仓库规则

- 每个 skill 必须位于 `skills/<skill-name>/` 目录下
- 每个 skill 必须包含 `SKILL.md` 文件
- skill 名称必须使用小写 kebab-case（如 `pr-review`）
- 每个 skill 应解决一个聚焦的工作流
- 不要创建宽泛或模糊的 skill
- 保持 skill 描述清晰且面向触发场景
- 长文档放在 `references/`，不要直接写在 `SKILL.md` 中
- 确定性辅助逻辑放在 `scripts/`
- 新增、重命名或删除 skill 后，更新 `catalog.json`
- 修改用户可见行为后，更新 `docs/skills/`

## 校验

提交前运行：

```bash
python tools/validate_skills.py
python tools/generate_catalog.py
python tools/sync_docs.py
```

## Skill 质量标准

一个合格的 skill 必须定义：

1. 它做什么
2. 什么时候使用
3. 需要的输入
4. 执行工作流
5. 输出格式
6. 约束条件
7. 示例
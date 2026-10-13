# skills_hub 文档

面向 Codex、OpenCode 及兼容 agent 工具的技能管理中心。

## 快速链接

- [安装指南](guide/install.md)
- [编写 Skill](guide/write-skill.md)
- [命名规范](guide/naming.md)
- [兼容性说明](guide/compatibility.md)

## Skill 列表

### code-review

| Skill | 状态 | 描述 |
|-------|------|------|
| [clean-dead-code](skills/clean-dead-code.md) | stable | 冗余代码清理——识别并移除死代码（未使用的导入、类、函数、配置、导出项、残留设计）。触发场景：用户要求清理冗余、移... |

### coding

| Skill | 状态 | 描述 |
|-------|------|------|
| [coding-guidelines](skills/coding-guidelines.md) | stable | LLM 编码行为准则，减少常见编码错误——先思考再编码、简洁优先、精准修改、目标驱动执行 |

### testing

| Skill | 状态 | 描述 |
|-------|------|------|
| [test-writer](skills/test-writer.md) | stable | 编写高质量测试代码的专项技能。覆盖单元测试、集成测试、回归测试和异步测试的设计模式与最佳实践。当需要为新功能编写测... |

### tooling

| Skill | 状态 | 描述 |
|-------|------|------|
| [jev-router](skills/jev-router.md) | stable | Use Jev to choose a Codex worker model for a delegated development task, keep that model fixed, and adjust reasoning effort between execution turns through managed App Server sessions. Use when the user requests Jev routing or adaptive worker reasoning. |
| [skill-creator](skills/skill-creator.md) | stable | Guide for creating effective skills. This skill should be... |

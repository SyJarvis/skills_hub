# 兼容性说明

## 支持的 Agent 工具

| 工具 | Skill 目录 | 安装命令 |
|------|------------|---------|
| Codex | `~/.agents/skills/` | `./install.sh <name> --target codex` |
| OpenCode | `~/.config/opencode/skills/` | `./install.sh <name> --target opencode` |
| 通用 | `~/.agents/skills/` | `./install.sh <name>` |

## Skill 兼容性标记

每个 skill 在 frontmatter 中标记兼容的工具：

```yaml
compatibility: [codex, opencode]
```

## 差异注意事项

- Codex 和 OpenCode 读取 skill 的方式略有不同
- 建议将 skill 放在通用目录 `~/.agents/skills/`
- 如需工具专用安装，使用 `--target` 参数
- 脚本（`scripts/`）中的路径应使用相对路径

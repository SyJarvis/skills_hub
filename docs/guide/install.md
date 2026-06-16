# 安装指南

## 全局安装

将 skill 安装到 `~/.agents/skills/` 目录，所有项目可用：

```bash
./install.sh <skill-name> --link
```

## 项目级安装

将 skill 安装到当前项目的 `.agents/skills/` 目录：

```bash
./install.sh <skill-name> --project .
```

## 工具专用安装

### OpenCode

```bash
./install.sh <skill-name> --target opencode --link
```

安装到 `~/.config/opencode/skills/`。

### Codex

```bash
./install.sh <skill-name> --target codex --link
```

安装到 `~/.codex/skills/`。

## 安装模式

### 软链接（推荐开发使用）

`--link` 创建符号链接，仓库更新后 skill 自动同步：

```bash
./install.sh <skill-name> --link
```

### 复制（推荐团队项目使用）

`--copy`（默认）将 skill 复制到目标位置，适合项目级部署：

```bash
./install.sh <skill-name> --project . --copy
```

## 批量安装

```bash
./install.sh --all --link
./install.sh --category testing --link
```

## 查看可用 skill

```bash
./install.sh --list
```

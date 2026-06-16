#!/usr/bin/env python3
"""
从 catalog.json 生成/更新 docs/ 下的文档页面。

功能:
1. 生成 docs/index.md — skill 总览页
2. 为每个 skill 生成 docs/skills/<name>.md — skill 详情页
3. 生成 docs/guide/ 下的指南页面（仅当不存在时）
4. 不会覆盖已存在的文件（除非使用 --force）

用法:
    python tools/sync_docs.py
    python tools/sync_docs.py --force    强制覆盖所有文档
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_FILE = REPO_ROOT / "catalog.json"
DOCS_DIR = REPO_ROOT / "docs"
SKILLS_DOC_DIR = DOCS_DIR / "skills"
GUIDE_DIR = DOCS_DIR / "guide"


def load_catalog():
    """加载 catalog.json。"""
    if not CATALOG_FILE.exists():
        print("错误: catalog.json 不存在，请先运行 python tools/generate_catalog.py",
              file=sys.stderr)
        sys.exit(1)

    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_index_md(catalog):
    """生成 docs/index.md。"""
    skills = catalog.get("skills", [])

    lines = [
        "# skills_hub 文档",
        "",
        "面向 Codex、OpenCode 及兼容 agent 工具的技能管理中心。",
        "",
        "## 快速链接",
        "",
        "- [安装指南](guide/install.md)",
        "- [编写 Skill](guide/write-skill.md)",
        "- [命名规范](guide/naming.md)",
        "- [兼容性说明](guide/compatibility.md)",
        "",
        "## Skill 列表",
        "",
    ]

    categories = {}
    for s in skills:
        cat = s.get("category") or "未分类"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s)

    for cat in sorted(categories.keys()):
        lines.append(f"### {cat}")
        lines.append("")
        lines.append("| Skill | 状态 | 描述 |")
        lines.append("|-------|------|------|")
        for s in categories[cat]:
            stability = s.get("stability", "beta")
            desc = s.get("description", "")
            if len(desc) > 60:
                desc = desc[:57] + "..."
            name = s["name"]
            lines.append(f"| [{name}](skills/{name}.md) | {stability} | {desc} |")
        lines.append("")

    return "\n".join(lines)


def generate_skill_md(skill):
    """为单个 skill 生成文档页。"""
    name = skill["name"]
    description = skill.get("description", "")
    category = skill.get("category") or "未分类"
    stability = skill.get("stability", "beta")
    compatibility = skill.get("compatibility", [])
    tags = skill.get("tags", [])
    version = skill.get("version", "")
    path = skill.get("path", f"skills/{name}")

    lines = [
        f"# {name}",
        "",
        f"**分类**: {category}  ",
        f"**状态**: {stability}  ",
        f"**兼容工具**: {', '.join(compatibility)}  ",
    ]

    if version:
        lines.append(f"**版本**: {version}  ")
    if tags:
        lines.append(f"**标签**: {', '.join(tags)}  ")

    lines.extend([
        "",
        "## 用途",
        "",
        description,
        "",
        "## 安装",
        "",
        "```bash",
        f"./install.sh {name} --link",
        "```",
        "",
        "## 文件",
        "",
    ])

    skill_dir = REPO_ROOT / path
    if skill_dir.exists():
        files = sorted(skill_dir.rglob("*"))
        for f in files:
            if f.is_file():
                rel = f.relative_to(skill_dir)
                lines.append(f"- `{rel}`")

    lines.extend([
        "",
        "---",
        f"_本文档由 `tools/sync_docs.py` 自动生成，手动修改将在下次同步时被覆盖。_",
    ])

    return "\n".join(lines)


GUIDE_CONTENTS = {
    "install.md": """# 安装指南

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
""",
    "write-skill.md": """# 编写 Skill 指南

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
""",
    "naming.md": """# 命名规范

## Skill 命名规则

1. 使用小写字母
2. 使用连字符 `-` 分隔单词
3. 名称要简短
4. 避免模糊名称
5. 优先使用工作流命名

## 好的命名

| 名称 | 说明 |
|------|------|
| pr-review | 代码审查 |
| repo-analysis | 仓库分析 |
| paper-reading | 论文阅读 |
| test-writer | 测试编写 |
| clean-dead-code | 死代码清理 |

## 不好的命名

| 名称 | 问题 |
|------|------|
| PRReview | 不是 kebab-case |
| repo_analysis | 使用了下划线 |
| Paper Reading | 包含空格 |
| general-helper | 过于模糊 |
| my-skill | 没有描述功能 |
""",
    "compatibility.md": """# 兼容性说明

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
""",
}


def main():
    force = "--force" in sys.argv

    catalog = load_catalog()
    skills = catalog.get("skills", [])

    SKILLS_DOC_DIR.mkdir(parents=True, exist_ok=True)
    GUIDE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 生成 docs/index.md
    index_content = generate_index_md(catalog)
    index_path = DOCS_DIR / "index.md"

    if force or not index_path.exists():
        index_path.write_text(index_content, encoding="utf-8")
        print(f"✅ 已生成 {index_path.relative_to(REPO_ROOT)}")
    else:
        print(f"⏭ 跳过 {index_path.relative_to(REPO_ROOT)}（已存在，使用 --force 覆盖）")

    # 2. 生成每个 skill 的文档页
    generated = 0
    for skill in skills:
        name = skill["name"]
        skill_md_path = SKILLS_DOC_DIR / f"{name}.md"
        content = generate_skill_md(skill)

        if force or not skill_md_path.exists():
            skill_md_path.write_text(content, encoding="utf-8")
            print(f"✅ 已生成 {skill_md_path.relative_to(REPO_ROOT)}")
            generated += 1
        else:
            print(f"⏭ 跳过 {skill_md_path.relative_to(REPO_ROOT)}（已存在，使用 --force 覆盖）")

    # 3. 生成 guide 目录下的文件
    for filename, content in GUIDE_CONTENTS.items():
        filepath = GUIDE_DIR / filename
        if not filepath.exists():
            filepath.write_text(content, encoding="utf-8")
            print(f"✅ 已生成 {filepath.relative_to(REPO_ROOT)}")
        else:
            print(f"⏭ 跳过 {filepath.relative_to(REPO_ROOT)}（已存在）")

    print(f"\n文档同步完成: 生成了 {generated} 个 skill 文档页")
    return 0


if __name__ == "__main__":
    sys.exit(main())
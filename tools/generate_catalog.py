#!/usr/bin/env python3
"""
扫描 skills/ 目录下所有 skill，解析 SKILL.md 的 YAML frontmatter，
合并 skills_metadata.json 中的 hub 元数据，自动生成 catalog.json。

数据来源:
- SKILL.md frontmatter: name, description（skill 自有属性，不修改）
- skills_metadata.json: category, stability, tags, compatibility（hub 管理属性）

用法:
    python tools/generate_catalog.py
    python tools/generate_catalog.py --dry-run
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CATALOG_FILE = REPO_ROOT / "catalog.json"
METADATA_FILE = REPO_ROOT / "skills_metadata.json"


def parse_frontmatter(content):
    """解析 YAML frontmatter，优先使用 yaml 库，不可用时回退到简单解析。"""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    fm_text = match.group(1)

    try:
        import yaml
        return yaml.safe_load(fm_text)
    except ImportError:
        pass

    result = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("  "):
            continue
        colon_idx = line.find(":")
        if colon_idx == -1:
            continue
        key = line[:colon_idx].strip()
        value = line[colon_idx + 1:].strip()
        if not value:
            result[key] = None
        elif value.startswith("[") and value.endswith("]"):
            result[key] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        else:
            result[key] = value
    return result


def load_hub_metadata():
    """加载 skills_metadata.json。"""
    if not METADATA_FILE.exists():
        return {}

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def scan_skills(hub_metadata):
    """扫描 skills/ 目录，合并 hub 元数据，返回 skill 列表。"""
    if not SKILLS_DIR.exists():
        print(f"错误: skills 目录不存在: {SKILLS_DIR}", file=sys.stderr)
        sys.exit(1)

    skills = []

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue

        skill_name = skill_dir.name
        skill_md = skill_dir / "SKILL.md"

        if not skill_md.exists():
            print(f"警告: [{skill_name}] 缺少 SKILL.md，跳过", file=sys.stderr)
            continue

        content = skill_md.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(content)

        if frontmatter is None:
            print(f"警告: [{skill_name}] frontmatter 解析失败，跳过", file=sys.stderr)
            continue

        if not isinstance(frontmatter, dict):
            print(f"警告: [{skill_name}] frontmatter 不是字典，跳过", file=sys.stderr)
            continue

        # 从 SKILL.md frontmatter 读取 skill 自有属性
        name = frontmatter.get("name", skill_name)
        description = frontmatter.get("description", "")
        if not isinstance(description, str):
            description = str(description) if description else ""

        # 从 skills_metadata.json 读取 hub 管理属性
        meta = hub_metadata.get(skill_name, {})

        category = meta.get("category", "")
        stability = meta.get("stability", "beta")
        tags = meta.get("tags", [])
        compatibility = meta.get("compatibility", ["codex", "opencode"])

        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        if isinstance(compatibility, str):
            compatibility = [c.strip() for c in compatibility.split(",")]

        entry = {
            "name": name,
            "path": f"skills/{skill_name}",
            "category": category,
            "description": description,
            "compatibility": compatibility,
            "stability": stability,
            "tags": tags,
        }

        skills.append(entry)

    skills.sort(key=lambda s: s["name"])
    return skills


def main():
    dry_run = "--dry-run" in sys.argv

    hub_metadata = load_hub_metadata()
    skills = scan_skills(hub_metadata)

    existing_version = "0.1.0"
    if CATALOG_FILE.exists():
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_version = existing.get("version", existing_version)
        except Exception:
            pass

    catalog = {
        "name": "skills_hub",
        "version": existing_version,
        "skills": skills,
    }

    output = json.dumps(catalog, ensure_ascii=False, indent=2)

    if dry_run:
        print("【dry-run 模式】将生成以下 catalog.json:")
        print(output)
        print(f"\n共 {len(skills)} 个 skill")
    else:
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            f.write(output)
            f.write("\n")
        print(f"✅ 已生成 catalog.json（{len(skills)} 个 skill）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
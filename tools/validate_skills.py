#!/usr/bin/env python3
"""
校验 skills_hub 仓库中所有 skill 的结构和元数据。

检查项：
1. 每个 skill 目录包含 SKILL.md
2. skill 名称符合小写 kebab-case
3. SKILL.md 包含 YAML frontmatter
4. frontmatter 包含 name 和 description
5. 目录名与 frontmatter 中的 name 一致
6. skills_metadata.json 包含所有 skill
7. catalog.json 包含所有 skill
8. catalog.json 中没有指向不存在路径的 skill
9. 没有重复的 skill 名称
10. stability 值合法（stable, beta, experimental, deprecated）

用法:
    python tools/validate_skills.py
    python tools/validate_skills.py --json
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CATALOG_FILE = REPO_ROOT / "catalog.json"
METADATA_FILE = REPO_ROOT / "skills_metadata.json"

VALID_STABILITY = {"stable", "beta", "experimental", "deprecated"}
KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


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


def validate_skills():
    """校验所有 skill，返回 (errors, warnings)。"""
    errors = []
    warnings = []

    if not SKILLS_DIR.exists():
        errors.append(f"skills 目录不存在: {SKILLS_DIR}")
        return errors, warnings

    skill_dirs = sorted(
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    if not skill_dirs:
        errors.append("skills 目录为空，没有找到任何 skill")
        return errors, warnings

    skill_names_from_dirs = []

    for skill_dir in skill_dirs:
        skill_name = skill_dir.name
        skill_names_from_dirs.append(skill_name)

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"[{skill_name}] 缺少 SKILL.md 文件")
            continue

        if not KEBAB_CASE_RE.match(skill_name):
            errors.append(f"[{skill_name}] 名称不符合小写 kebab-case 规范")

        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            errors.append(f"[{skill_name}] SKILL.md 缺少 YAML frontmatter（应以 --- 开头）")
            continue

        frontmatter = parse_frontmatter(content)
        if frontmatter is None:
            errors.append(f"[{skill_name}] SKILL.md frontmatter 解析失败")
            continue

        if not isinstance(frontmatter, dict):
            errors.append(f"[{skill_name}] frontmatter 必须是字典")
            continue

        fm_name = frontmatter.get("name")
        if not fm_name:
            errors.append(f"[{skill_name}] frontmatter 缺少 'name' 字段")
        elif isinstance(fm_name, str) and fm_name != skill_name:
            errors.append(
                f"[{skill_name}] frontmatter name='{fm_name}' 与目录名 '{skill_name}' 不匹配"
            )

        fm_desc = frontmatter.get("description")
        if not fm_desc:
            errors.append(f"[{skill_name}] frontmatter 缺少 'description' 字段")
        elif isinstance(fm_desc, str) and len(fm_desc.strip()) < 10:
            warnings.append(f"[{skill_name}] description 过短，建议提供更详细的描述")

    # 校验 skills_metadata.json
    if not METADATA_FILE.exists():
        warnings.append("skills_metadata.json 不存在，hub 元数据（分类、标签等）将缺失")
    else:
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                hub_meta = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"skills_metadata.json JSON 解析失败: {e}")
            hub_meta = {}

        for name in skill_names_from_dirs:
            if name not in hub_meta:
                warnings.append(
                    f"[{name}] 不在 skills_metadata.json 中，"
                    f"建议补充 category/stability/tags 等元数据"
                )

        meta_names = set(hub_meta.keys())
        for name in meta_names:
            if name not in skill_names_from_dirs:
                warnings.append(
                    f"skills_metadata.json 中的 '{name}' 在 skills/ 目录下不存在"
                )

        for name, meta in hub_meta.items():
            stability = meta.get("stability", "")
            if stability and stability not in VALID_STABILITY:
                errors.append(
                    f"skills_metadata.json 中 '{name}' 的 stability='{stability}' 不合法，"
                    f"可选值: {', '.join(sorted(VALID_STABILITY))}"
                )

    # 校验 catalog.json
    if not CATALOG_FILE.exists():
        errors.append("catalog.json 不存在，请运行 python tools/generate_catalog.py")
        return errors, warnings

    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"catalog.json JSON 解析失败: {e}")
        return errors, warnings

    catalog_skills = catalog.get("skills", [])
    catalog_names = []
    catalog_paths = []

    for entry in catalog_skills:
        name = entry.get("name", "")
        path = entry.get("path", "")
        catalog_names.append(name)
        catalog_paths.append(path)

        stability = entry.get("stability", "")
        if stability and stability not in VALID_STABILITY:
            errors.append(f"catalog.json 中 '{name}' 的 stability='{stability}' 不合法")

    for name in skill_names_from_dirs:
        if name not in catalog_names:
            warnings.append(
                f"[{name}] 存在于 skills/ 目录但不在 catalog.json 中，"
                f"请运行 python tools/generate_catalog.py"
            )

    for path_str in catalog_paths:
        full_path = REPO_ROOT / path_str
        if not full_path.exists():
            errors.append(f"catalog.json 引用了不存在的路径: {path_str}")

    seen = set()
    for name in catalog_names:
        if name in seen:
            errors.append(f"catalog.json 中存在重复的 skill 名称: {name}")
        seen.add(name)

    return errors, warnings


def main():
    use_json = "--json" in sys.argv

    errors, warnings = validate_skills()

    if use_json:
        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if warnings:
            print("⚠ 警告:")
            for w in warnings:
                print(f"  {w}")
            print()

        if errors:
            print("❌ 错误:")
            for e in errors:
                print(f"  {e}")
            print()
            print(f"校验失败: {len(errors)} 个错误")
            sys.exit(1)
        else:
            print(f"✅ 校验通过: 所有 skill 结构正确")
            if warnings:
                print(f"   {len(warnings)} 个警告")
            sys.exit(0)


if __name__ == "__main__":
    main()
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
CATALOG_FILE="$REPO_ROOT/catalog.json"

DEFAULT_TARGET="$HOME/.agents/skills"
OPENCODE_TARGET="$HOME/.config/opencode/skills"
CODEX_TARGET="$HOME/.codex/skills"

MODE="copy"
TARGET_DIR="$DEFAULT_TARGET"
SKILL_NAMES=()
ALL_SKILLS=false
CATEGORY=""

usage() {
    cat <<'EOF'
用法:
  ./install.sh <skill-name>                安装指定 skill（默认复制）
  ./install.sh <skill-name> --link         以软链接方式安装
  ./install.sh <skill-name> --copy         以复制方式安装
  ./install.sh <skill-name> --project <path>  安装到指定项目目录
  ./install.sh <skill-name> --target <tool>    安装到指定工具目录 (opencode|codex)
  ./install.sh --all                       安装所有 skill
  ./install.sh --category <category>       安装指定分类的所有 skill
  ./install.sh --stable-only               仅安装 stable 状态的 skill
  ./install.sh --list                      列出可用的 skill
  ./install.sh --help                      显示帮助信息

示例:
  ./install.sh pr-review --link
  ./install.sh pr-review --project .
  ./install.sh --all --link
  ./install.sh --category code-review
  ./install.sh pr-review --target opencode --link
EOF
    exit 0
}

list_skills() {
    if [[ ! -f "$CATALOG_FILE" ]]; then
        echo "错误: catalog.json 不存在，请先运行 python tools/generate_catalog.py"
        exit 1
    fi

    printf "%-20s %-15s %-10s %s\n" "名称" "分类" "状态" "描述"
    printf "%-20s %-15s %-10s %s\n" "----" "----" "----" "----"

    python3 -c "
import json, sys
with open('$CATALOG_FILE') as f:
    data = json.load(f)
for s in data.get('skills', []):
    print(f\"{s['name']:<20} {s.get('category',''):<15} {s.get('stability',''):<10} {s.get('description','')}\")
"
}

get_skill_names_from_catalog() {
    local filter="${1:-}"
    local stable_only="${2:-false}"

    python3 -c "
import json, sys
with open('$CATALOG_FILE') as f:
    data = json.load(f)
skills = data.get('skills', [])
filter_cat = '$filter' if '$filter' != '' else None
for s in skills:
    if filter_cat and s.get('category', '') != filter_cat:
        continue
    if '$stable_only' == 'true' and s.get('stability', '') != 'stable':
        continue
    print(s['name'])
"
}

install_skill() {
    local skill_name="$1"
    local src="$SKILLS_DIR/$skill_name"

    if [[ ! -d "$src" ]]; then
        echo "错误: skill 目录不存在: $src"
        return 1
    fi

    if [[ ! -f "$src/SKILL.md" ]]; then
        echo "错误: $src 中缺少 SKILL.md"
        return 1
    fi

    local dest="$TARGET_DIR/$skill_name"

    mkdir -p "$TARGET_DIR"

    if [[ "$MODE" == "link" ]]; then
        if [[ -L "$dest" ]]; then
            rm "$dest"
        elif [[ -e "$dest" ]]; then
            echo "警告: $dest 已存在且不是符号链接，跳过"
            return 0
        fi
        ln -s "$src" "$dest"
        echo "已链接: $dest -> $src"
    else
        if [[ -L "$dest" ]]; then
            rm "$dest"
        fi
        cp -r "$src" "$dest"
        echo "已复制: $dest"
    fi
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            usage
            ;;
        --list)
            list_skills
            exit 0
            ;;
        --all)
            ALL_SKILLS=true
            shift
            ;;
        --link)
            MODE="link"
            shift
            ;;
        --copy)
            MODE="copy"
            shift
            ;;
        --stable-only)
            # 将在后续处理
            shift
            # 继续解析，这个标记需要在其他参数之后处理
            ;;
        --project)
            if [[ $# -lt 2 ]]; then
                echo "错误: --project 需要指定目录路径"
                exit 1
            fi
            TARGET_DIR="$(cd "$2" 2>/dev/null && pwd)/.agents/skills" || TARGET_DIR="$2/.agents/skills"
            shift 2
            ;;
        --target)
            if [[ $# -lt 2 ]]; then
                echo "错误: --target 需要指定工具名称 (opencode|codex)"
                exit 1
            fi
            case "$2" in
                opencode)
                    TARGET_DIR="$OPENCODE_TARGET"
                    ;;
                codex)
                    TARGET_DIR="$CODEX_TARGET"
                    ;;
                *)
                    echo "错误: 不支持的工具目标 '$2'，可选: opencode, codex"
                    exit 1
                    ;;
            esac
            shift 2
            ;;
        --category)
            if [[ $# -lt 2 ]]; then
                echo "错误: --category 需要指定分类名称"
                exit 1
            fi
            CATEGORY="$2"
            shift 2
            ;;
        -*)
            echo "错误: 未知选项 $1"
            usage
            ;;
        *)
            SKILL_NAMES+=("$1")
            shift
            ;;
    esac
done

# 检查 catalog.json
if [[ ! -f "$CATALOG_FILE" ]]; then
    echo "错误: catalog.json 不存在，请先运行 python tools/generate_catalog.py"
    exit 1
fi

# 执行安装
FAILED=0

if [[ "$ALL_SKILLS" == true ]]; then
    echo "正在安装所有 skill 到 $TARGET_DIR ..."
    mapfile -t ALL_NAMES < <(get_skill_names_from_catalog "" "false")
    for name in "${ALL_NAMES[@]}"; do
        [[ -z "$name" ]] && continue
        install_skill "$name" || ((FAILED++))
    done
elif [[ -n "$CATEGORY" ]]; then
    echo "正在安装分类 '$CATEGORY' 的所有 skill 到 $TARGET_DIR ..."
    mapfile -t CAT_NAMES < <(get_skill_names_from_catalog "$CATEGORY" "false")
    if [[ ${#CAT_NAMES[@]} -eq 0 ]]; then
        echo "警告: 分类 '$CATEGORY' 下没有找到 skill"
    fi
    for name in "${CAT_NAMES[@]}"; do
        [[ -z "$name" ]] && continue
        install_skill "$name" || ((FAILED++))
    done
elif [[ ${#SKILL_NAMES[@]} -gt 0 ]]; then
    echo "正在安装 ${#SKILL_NAMES[@]} 个 skill 到 $TARGET_DIR ..."
    for name in "${SKILL_NAMES[@]}"; do
        install_skill "$name" || ((FAILED++))
    done
else
    echo "错误: 请指定要安装的 skill 名称，或使用 --all 安装所有 skill"
    echo "运行 ./install.sh --help 查看帮助"
    exit 1
fi

if [[ $FAILED -gt 0 ]]; then
    echo ""
    echo "安装完成，有 $FAILED 个 skill 安装失败"
    exit 1
else
    echo ""
    echo "安装完成"
fi
# clean-dead-code

**分类**: code-review  
**状态**: stable  
**兼容工具**: codex, opencode  
**标签**: cleanup, dead-code, refactor, review  

## 用途

冗余代码清理——识别并移除死代码（未使用的导入、类、函数、配置、导出项、残留设计）。触发场景：用户要求清理冗余、移除死代码、删除未使用的定义、清理残留。

## 安装

```bash
./install.sh clean-dead-code --link
```

## 文件

- `SKILL.md`
- `references/dynamic-patterns.md`

---
_本文档由 `tools/sync_docs.py` 自动生成，手动修改将在下次同步时被覆盖。_
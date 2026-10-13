# jev-router

**分类**: tooling
**状态**: stable
**兼容工具**: codex
**标签**: jev, codex, model-routing, agent

## 用途

Use Jev to choose a Codex worker model for a delegated development task, keep that model fixed, and adjust reasoning effort between execution turns through managed App Server sessions. Use when the user requests Jev routing or adaptive worker reasoning.

## 安装

```bash
./install.sh jev-router --link
```

## 文件

- `SKILL.md`
- `agents/openai.yaml`
- `references/routing-policy.json`
- `references/usage.md`
- `scripts/__pycache__/router.cpython-312.pyc`
- `scripts/router.py`
- `tests/__pycache__/test_router.cpython-312.pyc`
- `tests/__pycache__/test_usage.cpython-312.pyc`
- `tests/fake_app_server.py`
- `tests/test_router.py`
- `tests/test_usage.py`

---
_本文档由 `tools/sync_docs.py` 自动生成，手动修改将在下次同步时被覆盖。_

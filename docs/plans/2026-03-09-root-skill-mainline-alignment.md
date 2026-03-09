# Root Skill Mainline Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把仓库根层 legacy `feishu-openclaw-multi-agent` skill 收口到当前 `V5.1 Hardening` 主线，避免用户或模型误走 `chat-feishu`、旧构建脚本和旧提示词模板。

**Architecture:** 先在测试里定义“根层 skill 只能作为当前主线薄入口，不能继续公开 legacy workflow”的契约，再最小化重写根层 `SKILL.md` 和根层公开 references。实现上不改运行时代码，只收口入口文案和对外公开模板，让它们显式转向 `OpenClaw-Feishu-Multi-Agent/skills/openclaw-feishu-multi-agent-deploy` 下的正式主线资源。

**Tech Stack:** Markdown、JSON、Python `unittest`

---

### Task 1: 写失败的根层 skill 契约测试

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 写 failing tests**

增加断言：

- 根层 `feishu-openclaw-multi-agent/SKILL.md` 不得再公开 `chat-feishu`
- 不得再引用 `build_openclaw_feishu_snippets.py`
- 不得再引用 `input-template-legacy-chat-feishu.json`
- 必须显式指向 `openclaw-feishu-multi-agent-deploy` 和 `V5.1 Hardening`

**Step 2: 跑测试确认 RED**

Run:

```bash
python3 -m unittest feishu-openclaw-multi-agent/OpenClaw-Feishu-Multi-Agent/tests/test_openclaw_feishu_multi_agent_skill.py
```

Expected: 新增断言失败。

### Task 2: 重写根层 skill 薄入口

**Files:**
- Modify: `feishu-openclaw-multi-agent/SKILL.md`

**Step 1: 删除 legacy workflow 暴露**

去掉：

- `chat-feishu`
- `build_openclaw_feishu_snippets.py`
- `input-template-legacy-chat-feishu.json`
- 旧 `codex-prompt-templates.md` 作为默认入口

**Step 2: 改成主线导流文案**

要求根层 skill 明确：

- 当前公开主线是 `V5.1 Hardening`
- 最新推荐是 `V5.1 Hardening`
- 正式入口是内层 deploy skill 和对应文档

### Task 3: 收口根层公开 references

**Files:**
- Modify: `feishu-openclaw-multi-agent/references/codex-prompt-templates.md`

**Step 1: 改成桥接文档**

让根层 `codex-prompt-templates.md` 只承担“转向当前主线文档”的作用，不再提供旧 prompt 模板。

### Task 4: 跑验证

**Files:**
- Modify: none unless verification reveals gaps

**Step 1: 跑完整测试**

Run:

```bash
python3 -m unittest feishu-openclaw-multi-agent/OpenClaw-Feishu-Multi-Agent/tests/test_openclaw_feishu_multi_agent_skill.py
```

**Step 2: 跑格式校验**

Run:

```bash
git -C feishu-openclaw-multi-agent/OpenClaw-Feishu-Multi-Agent diff --check
```

Expected: 全部通过。

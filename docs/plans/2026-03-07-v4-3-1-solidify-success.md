# V4.3.1 Solidify Success Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 VM 上已经跑通的 V4.3.1 单群生产稳定版经验回写到本地 skill 仓库，形成可重复部署的正式版本。

**Architecture:** 以远端当前生效的 SQLite 状态机、隐藏控制会话、6 类可见群消息约束为真相源，回写脚本、提示词模板、README、验收清单和变更记录。只固化已经通过 canary 的机制，不带入中间调试分支。

**Tech Stack:** OpenClaw, Feishu channel, SQLite, Python, Markdown, systemd watchdog

---

### Task 1: 导出远端真相源
- 读取远端 `v4_3_job_registry.py`
- 读取远端 `openclaw.json` 里 supervisor/ops/finance 团队群 `systemPrompt`
- 读取远端 `workspace-supervisor_agent/{SOUL,USER}.md`
- 读取远端 `workspace-{ops,finance}_agent/{SOUL,IDENTITY}.md`

### Task 2: 同步本地脚本
- 更新 `skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_job_registry.py`
- 必要时更新 `skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_3_canary.py`
- 更新测试 `tests/test_openclaw_feishu_multi_agent_skill.py`

### Task 3: 同步文档与模板
- 更新 `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md`
- 更新 `README.md`
- 更新 `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- 更新 `skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md`
- 更新交叉验证记录与设计文档（只补最终经验）

### Task 4: 验证与提交准备
- 运行本地测试
- 运行脚本语法检查
- 核对 `git diff --check`
- 总结剩余风险，等待用户确认再提交/推送

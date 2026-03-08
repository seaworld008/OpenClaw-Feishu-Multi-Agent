# V5 Fixed-Role Multi-Group Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不改动 `V5.1 Hardening` 运行协议的前提下，把“固定 bot-role 映射 + 群级角色组合模板”沉淀为正式模板、文档和测试。

**Architecture:** 继续使用现有 `teams[]` 输入模型，不新增新的 runtime schema。通过新增专用输入模板、更新 README/SKILL/V5 交付文档、补充文档测试，把推荐生产标准固化到仓库中。

**Tech Stack:** Python 3、`unittest`、Markdown、JSON

---

### Task 1: 锁定模板与文档要求

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write the failing tests**

- 检查固定角色模板文件存在
- 检查模板里包含 `full_team_demo / ops_only_demo / finance_only_demo`
- 检查 README / SKILL / V5 文档明确写出 `bot 复用，role 固定`

**Step 2: Run tests to verify they fail**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V5TemplateTests.test_v5_fixed_role_template_exists_and_documents_role_combinations \
  tests.test_openclaw_feishu_multi_agent_skill.V5TemplateTests.test_v5_fixed_role_standard_is_documented_in_readme_skill_and_v5_doc -v
```

### Task 2: 增加固定角色多群模板

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v5-fixed-role-multi-group.json`

**Step 1: Add a direct-use template**

- 保持 `teams[]` 结构
- 固定 `aoteman / xiaolongxia / yiran_yibao`
- 示例覆盖 `full_team_demo / ops_only_demo / finance_only_demo`

### Task 3: 更新 README / SKILL / V5 文档

**Files:**
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v5-team-orchestrator.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml`

**Step 1: Document the recommended standard**

- 明确写出 `bot 复用，role 固定`
- 说明“同一个 bot 可以跨很多群复用”
- 说明“每个群的角色组合可以不同”
- 链接新模板文件

### Task 4: 跑回归

**Files:**
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Run focused tests**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V5TemplateTests.test_v5_fixed_role_template_exists_and_documents_role_combinations \
  tests.test_openclaw_feishu_multi_agent_skill.V5TemplateTests.test_v5_fixed_role_standard_is_documented_in_readme_skill_and_v5_doc -v
```

**Step 2: Run full regression**

Run:
```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
git diff --check
```

# Default Expert Catalog Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `README.md` 增加双语默认专家库章节，并用测试锁住 30 个专家与 10 个分类的结构。

**Architecture:** 只改文档与测试，不改任何运行时代码。用一个 README 测试验证章节存在、分类存在、专家数量正确。

**Tech Stack:** Python 3、`unittest`、Markdown

---

### Task 1: 先写失败测试

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write the failing test**

- 检查 README 存在 `默认专家库 / Default Expert Catalog`
- 检查 10 个分类标题
- 检查专家条目总数为 30

### Task 2: 更新 README

**Files:**
- Modify: `README.md`

**Step 1: Add the catalog section**

- 在 README 中增加一节
- 使用 `- \`ExpertName\`：中文描述` 的统一格式
- 保持分类标题中英双语

### Task 3: 回归

**Files:**
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Run focused test**

```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V5ReadmeAndSkillTests.test_readme_includes_bilingual_default_expert_catalog_with_30_experts -v
```

**Step 2: Run full regression**

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
git diff --check
```

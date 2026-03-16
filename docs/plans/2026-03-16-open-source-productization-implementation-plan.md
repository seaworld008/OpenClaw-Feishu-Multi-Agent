# Open Source Productization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 补齐开源治理基础设施、README 双入口与最小 CI，使仓库同时适合开发者采用和客户交付。

**Architecture:** 不重写现有交付体系，只在顶层增加开源项目所需的治理与协作层；README 采用“开发者入口 + 交付入口”双导航。

**Tech Stack:** Markdown, GitHub repository metadata, GitHub Actions, pytest

---

### Task 1: 用测试约束开源门面能力

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write the failing test**

增加断言，要求仓库存在：

- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `.github/ISSUE_TEMPLATE/*`
- `.github/pull_request_template.md`
- `.github/workflows/ci.yml`

同时要求 README 出现：

- `开发者入口`
- `交付入口`
- `GitHub Topics 建议`

### Task 2: 新增开源治理文件

**Files:**
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `.github/ISSUE_TEMPLATE/config.yml`
- Create: `.github/pull_request_template.md`

### Task 3: 增加最小 CI

**Files:**
- Create: `.github/workflows/ci.yml`

### Task 4: 重构 README 顶部入口

**Files:**
- Modify: `README.md`

补充：

- 开发者入口
- 交付入口
- GitHub Topics 建议
- 关键词与项目定位

### Task 5: 验证

**Step 1: Run**

```bash
pytest tests/test_openclaw_feishu_multi_agent_skill.py -k 'open_source_governance_files_exist or dual_entry or governance_docs' -q
pytest tests/test_openclaw_feishu_multi_agent_skill.py tests/test_v51_ingress_adapter.py tests/test_v51_outbox_sender.py tests/test_v51_runtime_store.py tests/test_v51_team_controller.py tests/test_v51_worker_callback_sink.py -q
```

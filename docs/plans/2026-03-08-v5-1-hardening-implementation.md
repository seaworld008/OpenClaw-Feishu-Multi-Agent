# V5.1 Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `V5.1 Hardening` 增加确定性控制面，实现 `V5.1 Hardening`，把阶段推进和最终收口从 prompt 判断升级为 registry 状态机。

**Architecture:** 保留 `V5.1` 的 team unit 结构，但把 supervisor 的调度权收敛到 SQLite registry 命令。新增 `start-job-with-workflow / get-next-action / build-rollup-context`，并让 `ready-to-rollup` 基于显式 `next_action=rollup` 返回结果。生成器同步输出 `V5.1 Hardening` control plane 元数据，README / SKILL / 模板文档统一改成硬状态机协议。

**Tech Stack:** Python 3、SQLite、`unittest`、Markdown、JSON 模板

---

### Task 1: 先补失败测试

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write the failing test**

新增测试覆盖：
- `start-job-with-workflow`
- `get-next-action`
- 旧 `team_jobs.db` 自动补列
- `v51 runtime manifest` 输出 `orchestratorVersion`
- 文档必须写明 `V5.1 Hardening`

**Step 2: Run test to verify it fails**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_start_job_with_workflow_emits_first_dispatch_action \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_get_next_action_advances_only_in_workflow_order \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_init_db_migrates_existing_jobs_table_for_v51_columns \
  tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV51Tests.test_v51_team_input_builds_team_runtime_manifest \
  tests.test_openclaw_feishu_multi_agent_skill.V51DocumentationTests -v
```

Expected: 失败，提示命令不存在、schema 未迁移、文档未升级。

### Task 2: 升级 registry 为确定性状态机

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write minimal implementation**

实现：
- `jobs` 新列与迁移
- `start-job-with-workflow`
- `get-next-action`
- `build-rollup-context`
- `mark-dispatch` 的顺序校验
- `mark-worker-complete` 的阶段推进
- `ready-to-rollup` 改为状态机语义

**Step 2: Run focused tests**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests -v
```

Expected: 全绿。

### Task 3: 升级生成器和 runtime manifest

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_feishu_config_builder.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-team-orchestrator.json`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v51-team-orchestrator.example.jsonc`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write minimal implementation**

runtime manifest 必须新增：
- `orchestratorVersion`
- `runtime.controlPlane.registryScript`
- `runtime.controlPlane.commands.startJob`
- `runtime.controlPlane.commands.nextAction`
- `runtime.controlPlane.commands.buildRollupContext`
- `runtime.controlPlane.commands.readyToRollup`

**Step 2: Run focused tests**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV51Tests -v
```

Expected: 全绿。

### Task 4: 升级长版提示词与主文档

**Files:**
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-team-orchestrator.json`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v51-team-orchestrator.example.jsonc`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write minimal implementation**

文档必须统一写明：
- `V5.1 Hardening`
- `Deterministic Orchestrator`
- `start-job-with-workflow`
- `get-next-action`
- `build-rollup-context`
- `LLM 负责内容，代码负责流程`

**Step 2: Run focused tests**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V51DocumentationTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51TemplateTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51ReadmeAndSkillTests -v
```

Expected: 全绿。

### Task 5: 跑全量回归

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Run full tests**

Run:
```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
```

Expected: 全绿。

**Step 2: Run diff hygiene**

Run:
```bash
git diff --check
```

Expected: 通过。

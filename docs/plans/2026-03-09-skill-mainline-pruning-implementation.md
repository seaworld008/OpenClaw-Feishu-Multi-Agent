# Skill Mainline Pruning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 skill 仓库只保留 `V5.1 Hardening` 这一条主线，并同步删除旧跨群主线与中间过渡版本的公开资产和测试契约。

**Architecture:** 先从测试文件改掉 `V4.3.1` 常量、入口和存在性断言，再同步收紧 README、SKILL、通用模板和 rollout 文档，最后删除 `V4.3.1` 文档、模板、脚本与计划文件。底层共享核心模块保留，但文案去 `V4` 化。

**Tech Stack:** Python 3、Markdown、JSON/JSONC、`unittest`

---

### Task 1: 先把测试契约切到只允许 V5.1 主线

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 清理常量与入口**

- 去掉 `V4_3_*`、`C1.0`、`v431`、`v4-3-watchdog` 相关常量
- 新增 `V51_RUNTIME_SCRIPT`、`JOB_REGISTRY_SCRIPT`、`SESSION_HYGIENE_SCRIPT`

**Step 2: 改主线断言**

- README / SKILL 只保留 `V5.1 Hardening`
- 旧 `V4.3.1` 资产改成“不存在”断言
- 共享 registry / hygiene 测试切到 `core_*` 或 `v51_*`

**Step 3: 跑局部测试**

Run:

```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.ScriptNamespaceContractTests \
  tests.test_openclaw_feishu_multi_agent_skill.DocumentationConsistencyTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51ReadmeAndSkillTests -v
```

Expected: 先红，作为后续文档/文件清理的目标。

### Task 2: 收紧 README、SKILL 和通用模板

**Files:**
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/rollout-and-upgrade-playbook.md`

**Step 1: 移除 V4 主线表述**

- 版本列表只保留 `V5.1 Hardening`
- 删除 `V4.3.1` 快速启动、watchdog、交叉验证入口

**Step 2: 保留通用价值**

- 平台矩阵继续保留 `Linux / macOS / WSL2`
- WSL2 只保留通用模板，不再单独维护 `V4` 部署文档
- checklist / deployment inputs 只保留 `V5.1`

**Step 3: 跑文档测试**

Run:

```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.DocumentationConsistencyTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51DocumentationTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51ReadmeAndSkillTests -v
```

Expected: 文档侧断言转绿。

### Task 3: 删除 V4 公开资产

**Files:**
- Delete: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production-C1.0.md`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/references/v4-3-1-quick-start.md`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/references/source-cross-validation-2026-03-07-v4-3-1.md`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/references/source-cross-validation-2026-03-07-platforms.md`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/references/windows-wsl2-deployment-notes.md`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v4-3-1-single-group-production.example.jsonc`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v4-3-watchdog.service`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v4-3-watchdog.timer`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/templates/v4-3-job-registry.example.sql`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_runtime.py`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_hygiene.py`
- Delete: `skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_canary.py`
- Delete: `docs/plans/2026-03-07-v4-3-1-cross-platform-compatibility.md`
- Delete: `docs/plans/2026-03-07-v4-3-1-single-group-production-stability.md`
- Delete: `docs/plans/2026-03-07-v4-3-1-solidify-success.md`

**Step 1: 删除文件**

使用补丁删除，不保留空引用。

**Step 2: 搜索残留**

Run:

```bash
rg -n "V4\\.3\\.1|C1\\.0|v431|v4-3-watchdog" README.md skills/openclaw-feishu-multi-agent-deploy tests docs/plans
```

Expected: 只剩明确允许的历史说明；主线入口不再出现。

### Task 4: 去掉 shared core 的 V4 文案

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_session_hygiene.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_canary_engine.py`

**Step 1: 更新 docstring / 默认文案**

- `core_job_registry.py` 改成通用 team workflow registry
- `core_session_hygiene.py` 改成 V5.1/team hygiene 描述
- `core_canary_engine.py` 去掉 `V4.3.1` 叙述

**Step 2: 运行共享逻辑测试**

Run:

```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.RuntimeRegistryTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51RuntimeArtifactsTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51ReconcileTests -v
```

Expected: 共享能力不受入口裁剪影响。

### Task 5: 全量验证

**Files:**
- Modify: none unless verification reveals gaps

**Step 1: 全量测试**

Run:

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
```

**Step 2: 差异检查**

Run:

```bash
git diff --check
```

**Step 3: 版本残留检查**

Run:

```bash
rg -n "V4\\.3\\.1|C1\\.0|v431|v4-3-watchdog" README.md skills/openclaw-feishu-multi-agent-deploy tests
```

Expected: 对外主线只剩 `V5.1 Hardening`。

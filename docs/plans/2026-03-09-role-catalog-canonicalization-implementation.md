# V5.1 Role Catalog Canonicalization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `V5.1 Hardening` 落地 `roleCatalog + teams(profileId + override)` canonical schema，并让 runtime 标题、职责快照、模板文档和测试全部对齐到这一套标准化角色快照。

**Architecture:** 先在 `core_feishu_config_builder.py` 中新增 catalog 解析与 team 归一化，把“legacy inline teams”和“canonical profile 引用”统一成标准化角色对象，再继续生成 patch 与 runtime manifest。runtime 侧在 `core_job_registry.py` 中新增 supervisor / participant 的 `visibleLabel` 快照持久化，由 reconcile 从 manifest 传入，后续所有可见标题与收口段落只读快照。模板、示例、SOP 与测试同步切到新 schema，同时保留旧 inline 输入兼容。

**Tech Stack:** Python 3、`sqlite3`、`unittest`、JSON/JSONC、Markdown

---

### Task 1: 为 canonical schema 补 RED 测试

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write the failing tests**

补三类断言：

- builder 支持 `roleCatalog + profileId`
- runtime manifest 输出 `profileId / visibleLabel`
- registry 使用快照 `visibleLabel` 生成 ack / dispatch / rollup 标题

**Step 2: Run tests to verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV51Tests \
  tests.test_openclaw_feishu_multi_agent_skill.V51RegistryTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51DocumentationTests -v
```

Expected: 因当前实现缺少 `roleCatalog/profileId` 和 runtime `visibleLabel` 快照而失败。

### Task 2: 升级 builder，支持 roleCatalog 归一化

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_feishu_config_builder.py`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Add catalog normalization helpers**

实现：

- `validate_role_catalog`
- `resolve_team_role_spec`
- `normalize_v51_teams`
- `default_visible_label`

**Step 2: Wire normalized teams into patch + manifest**

让以下函数统一使用标准化 team：

- `build_messages_patch`
- `build_v51_plugin_patch`
- `build_v51_runtime_manifest`

**Step 3: Run targeted tests**

Run:

```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV51Tests -v
```

Expected: builder 新增断言通过。

### Task 3: 升级 runtime，持久化 visibleLabel 快照

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write schema/migration support**

在 registry 中新增：

- `jobs.supervisor_visible_label`
- `job_participants.visible_label`

并补 migration。

**Step 2: Pass visible labels from manifest to registry**

在 reconcile `start-job-with-workflow` 调用里传入：

- `--supervisor-visible-label`
- `participants_json[].visibleLabel`

**Step 3: Rebuild visible messages from snapshots**

让 `build-visible-ack`、`build-dispatch-payload`、`build-rollup-visible-message` 只读快照。

**Step 4: Run targeted tests**

Run:

```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V51RegistryTests -v
```

Expected: 新旧场景都通过，legacy inline 输入仍兼容。

### Task 4: 同步更新 V5.1 主线文档与模板

**Files:**
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-team-orchestrator.json`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-fixed-role-multi-group.json`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v51-team-orchestrator.example.jsonc`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用信息清单.md`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Switch docs to canonical schema**

文档全部改成：

- 根层 `roleCatalog`
- team 层 `profileId + override`
- 标题用 `{visibleLabel}`

**Step 2: Keep legacy compatibility notes**

明确：

- inline `teams` 仍兼容
- 主线推荐已变成 `roleCatalog + profileId`

**Step 3: Run targeted tests**

Run:

```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V51TemplateTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51DocumentationTests -v
```

Expected: 文档与模板断言通过。

### Task 5: 跑最终验证并汇总风险

**Files:**
- Modify: none unless verification reveals gaps

**Step 1: Run focused regression suite**

Run:

```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV51Tests \
  tests.test_openclaw_feishu_multi_agent_skill.V51RegistryTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51TemplateTests \
  tests.test_openclaw_feishu_multi_agent_skill.V51DocumentationTests -v
```

**Step 2: Run repo-level check**

Run:

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
```

**Step 3: Run patch sanity check**

Run:

```bash
git diff --check
```

Expected: 无新增失败，无 patch 格式错误。

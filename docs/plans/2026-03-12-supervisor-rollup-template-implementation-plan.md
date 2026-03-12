# Supervisor Rollup Template Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 V5.1 的主管最终统一收口从字段拼接摘要改成通用的主管综合决策模板，并优先利用 worker 的完整 `finalVisibleText` 终案正文。

**Architecture:** 继续保留 control plane 单写和 outbox 统一发群的架构，只替换 `core_job_registry.py` 中 rollup section 的构建逻辑。新增的 helper 负责从 `finalVisibleText` 提取可综合的正文句子，再由 rollup renderer 组装成固定六段模板。

**Tech Stack:** Python 3, sqlite runtime store, unittest/pytest 风格仓库测试

---

### Task 1: 锁定新模板行为

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write the failing test**

在 `tests/test_openclaw_feishu_multi_agent_skill.py` 增加/调整 rollup 断言，要求：

- 输出包含 `一、最终判断`
- 输出包含 `二、建议采用的方案`
- 输出包含 `三、整合依据`
- 输出包含 `四、执行路线图`
- 输出包含 `五、联合风险与红线`
- 输出包含 `六、明日三件事`
- 输出会吸收 `finalVisibleText` 的关键正文，而不是只保留 `summary/details`
- 输出不会把 worker 原始章节标题整段照抄进去

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_openclaw_feishu_multi_agent_skill.py -k rollup_visible_message -q`

Expected: FAIL，因为当前实现仍然输出旧的五段结构和字段拼接结果。

### Task 2: 实现通用主管收口模板

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write minimal implementation**

在 `core_job_registry.py` 中：

- 新增 helper，从 `finalVisibleText` 提取非标题正文句子
- 调整 `build_dynamic_rollup_sections()`，生成：
  - `decisionLines`
  - `recommendedPlanLines`
  - `integrationLines`
  - `roadmapLines`
  - `riskLines`
  - `tomorrowLines`
- 让 `visible_message_text("rollup", ...)` 输出新的六段模板

**Step 2: Run targeted tests**

Run: `pytest tests/test_openclaw_feishu_multi_agent_skill.py -k rollup_visible_message -q`

Expected: PASS

### Task 3: 回归控制面相关契约

**Files:**
- Test: `tests/test_v51_team_controller.py`
- Test: `tests/test_v51_outbox_sender.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Run focused regression**

Run: `pytest tests/test_v51_team_controller.py tests/test_v51_outbox_sender.py tests/test_openclaw_feishu_multi_agent_skill.py -k 'rollup or outbox or team_controller' -q`

Expected: PASS

**Step 2: Review diff**

确认没有把主管模板重新写成角色特例，没有引入新的 role hardcode。

**Step 3: Commit**

```bash
git add docs/plans/2026-03-12-supervisor-rollup-template-design.md \
  docs/plans/2026-03-12-supervisor-rollup-template-implementation-plan.md \
  skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py \
  tests/test_openclaw_feishu_multi_agent_skill.py
git commit -m "feat: improve supervisor rollup synthesis"
```

## Execution Notes

实际实现过程中，又补了两项计划外但必要的修复：

1. `core_worker_callback_sink.py` 不能把数组字段直接 `str(...)` 成 Python 风格列表字符串；需要序列化成标准 JSON 字符串
2. `core_job_registry.py` 需要兼容解析历史遗留的 Python 风格列表字符串，避免线上已入库数据在主管收口中出现 `['...']` 脏格式

最终落地不仅完成了“通用主管模板”，还把模板进一步升级成“决策型主管稿”，并经过真实外部群任务验证。

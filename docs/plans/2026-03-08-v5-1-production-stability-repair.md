# V5.1 Production Stability Repair Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复当前 `V5.1 Hardening` 在线上双群中的三类结构性故障，使两群真实任务都能稳定完成“主管接单 -> 运营 -> 财务 -> 主管最终收口”全链路。

**Architecture:** 本次不再继续依赖 supervisor prompt 自己“记得下一步要做什么”。控制面收敛到“显式状态 + 可重放动作 + 可见消息确认”三层：SQLite registry 负责真状态，control-plane helper 负责生成确定性动作，watchdog 从被动 stale 回收升级为主动 reconcile。hidden main 不再隐式继承错误的 `webchat` 投递上下文，所有主管可见消息必须基于显式的飞书 delivery metadata 发送。

**Tech Stack:** Python 3、SQLite、`unittest`、OpenClaw CLI、仓库内 `core_job_registry.py` / `core_feishu_config_builder.py` / `v51_team_orchestrator_runtime.py`

---

## Root Cause Summary

当前线上已经证实的故障不是单点，而是三个相互叠加的结构问题：

1. supervisor group session 首轮会在 `start-job-with-workflow` 后直接 `NO_REPLY`
   - 真实证据：内部群 `TG-20260308-001` 只执行了 `begin-turn` 与 `start-job-with-workflow`，未继续 `message(主管接单)` / `get-next-action` / `sessions_send`，随后被 watchdog 判 stale failed。
   - 现状后果：只要这一轮停住，现有 watchdog 不会补派 worker，只会等超时后失败。

2. hidden main 会话没有稳定的飞书可见消息投递上下文
   - 真实证据：内部群恢复会话 `6c47bfd1-...` 在发送 `【主管已接单】` 时走成了 `channel=webchat`，报 `Unknown channel: webchat`。
   - 现状后果：即便 hidden main 能推进 DB，也不能可靠发送“主管接单/最终收口”。

3. watchdog 只会做 stale recovery，不会做 active reconcile
   - 真实证据：`watchdog-tick` 对 `nextAction=dispatch` 且无人派发的 active job 返回 `active_ok`，没有尝试补派，也没有把状态标记为“需要修复”。
   - 现状后果：系统把“已经卡死但未超时”的任务当成健康任务。

4. worker dispatch 内容仍由 supervisor prompt 临场拼装，缺少可重放的 canonical payload
   - 真实证据：外部群第一次派发的 dispatch 内容完整，运营成功执行；内部群恢复场景里 hidden main 拼出的简化 payload 导致 `ops_internal_main` 首轮直接 `NO_REPLY`。
   - 现状后果：同一套 worker SOUL，在不同 supervisor 回合下会收到不同质量的 dispatch 包，可靠性取决于模型临场生成。

5. job close 没有“最终统一收口已发出”的硬前置条件
   - 真实证据：外部群 `TG-20260308-001` 已被 `close-job done`，但 hidden main transcript 只执行了 `build-rollup-context` + `close-job`，没有主管最终收口群消息。
   - 现状后果：DB 看起来完成，群体验却是断链。

## Target State

修复后的生产系统必须满足：

- 主管首轮即使提前 `NO_REPLY`，watchdog 也能补做“接单/派发”。
- hidden main 可以安全地继续推进控制面，但所有可见消息都走显式飞书 delivery metadata。
- `nextAction=dispatch` 的 active job 不能再被判定为 `active_ok` 但无人处理。
- worker 收到的 `TASK_DISPATCH` 必须由代码生成，不再允许 supervisor 自由拼接关键字段。
- `close-job done` 前，必须已经确认“主管最终统一收口”发出成功。
- 双群真实测试必须都能通过，不允许出现“外部群 done 但没收口”或“内部群建单后沉默”。

## Scope

本次修复包含：

- registry schema 和状态机补强
- supervisor/worker 的 canonical control payload
- watchdog 主动 reconcile
- V5.1 generator / runtime manifest / prompts / docs 一致性升级
- 远端重部署与双群真实验收

本次不包含：

- 引入独立外部编排服务
- 替换模型供应商
- 引入第三套机器人角色

### Task 1: 先补失败测试，锁住真实线上回归场景

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write the failing test for dispatch gap**

新增测试：
- 启动一个 workflow job
- 保持 `next_action=dispatch`
- 不写入任何 participant
- 执行 `watchdog-tick`
- 断言不能返回 `active_ok`
- 断言必须返回新的“待修复/待补派”状态

**Step 2: Run test to verify it fails**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_watchdog_detects_dispatch_gap_instead_of_reporting_active_ok -v
```

Expected: 失败，因为当前实现会返回 `active_ok`。

**Step 3: Write the failing test for missing final rollup visibility**

新增测试：
- workflow 两个 worker 都 `done`
- `next_action=rollup`
- 未记录主管最终收口 message 成功
- 执行 `close-job done`
- 断言应被拒绝，或必须先满足 `rollup_visible_sent=true`

**Step 4: Run test to verify it fails**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_close_job_done_requires_rollup_visible_message_confirmation -v
```

Expected: 失败，因为当前实现允许直接 `close-job done`。

**Step 5: Write the failing test for canonical dispatch payload**

新增测试：
- workflow job 生成 dispatch payload
- 断言 payload 固定包含 `jobRef / groupPeerId / callbackSessionKey / mustSend / role-specific fields`
- 断言不允许 supervisor 自己自由拼装缺失字段版本

**Step 6: Run test to verify it fails**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_build_dispatch_payload_emits_canonical_worker_packet -v
```

Expected: 失败，因为命令和数据模型还不存在。

### Task 2: 扩展 registry，存下“足够重放”的真实控制面状态

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Add new persisted fields**

为 `jobs` 表补列并迁移：
- `request_text`
- `entry_account_id`
- `entry_channel`
- `entry_target`
- `entry_delivery_json`
- `rollup_visible_sent`
- `ack_visible_sent`
- `dispatch_attempt_count`
- `last_control_error`

**Step 2: Run focused migration test**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_init_db_migrates_existing_jobs_table_for_v51_repair_columns -v
```

Expected: 先失败，补列后通过。

**Step 3: Make start-job-with-workflow persist replay context**

建单时必须写入：
- 原始请求文本
- 当前 entry account/channel/target
- 初始 visible flags
- 初始 dispatch attempt count

**Step 4: Run focused test**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_start_job_with_workflow_persists_visible_delivery_and_request_context -v
```

Expected: 通过。

### Task 3: 给 registry 增加“可重放动作”命令，不再让 supervisor 自由拼接

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Add `build-dispatch-payload`**

命令输出必须包含：
- `jobRef`
- `agentId`
- `groupPeerId`
- `callbackSessionKey`
- `mustSend=progress,final,callback`
- `role`
- 规范化 `request/context/constraints`

**Step 2: Add `build-visible-ack`**

命令输出主管接单消息文本，以及显式 delivery：
- `channel=feishu`
- `accountId=<entryAccountId>`
- `target=chat:<groupPeerId>`

**Step 3: Add `build-rollup-visible-message`**

命令基于 completion packets 生成最终统一收口文本与显式 delivery。

**Step 4: Add `record-visible-message`**

接收：
- `job-ref`
- `kind=ack|rollup`
- `message-id`

并回写 `ack_visible_sent / rollup_visible_sent`。

**Step 5: Run focused tests**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_build_dispatch_payload_emits_canonical_worker_packet \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_build_visible_ack_uses_explicit_feishu_delivery \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_build_rollup_visible_message_requires_completion_packets \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_registry_record_visible_message_updates_ack_and_rollup_flags -v
```

Expected: 全绿。

### Task 4: 把 watchdog 从“只会判 stale”改成“主动 reconcile”

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Change watchdog semantics**

新增判定：
- `nextAction=dispatch` 且当前 stage 未派发：返回 `needs_dispatch_reconcile`
- `nextAction=rollup` 且 `rollup_visible_sent=false`：返回 `needs_rollup_reconcile`
- `nextAction=wait_worker`：只在 worker 超时后才进入 stale/repair 分支

**Step 2: Ensure `active_ok` only means truly healthy**

只有以下场景才能返回 `active_ok`：
- `wait_worker` 且当前 stage 已有 dispatch 记录
- 或 active job 无需额外可见动作

**Step 3: Run focused tests**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_watchdog_detects_dispatch_gap_instead_of_reporting_active_ok \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_watchdog_detects_missing_rollup_visibility_instead_of_reporting_active_ok \
  tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests.test_watchdog_keeps_wait_worker_jobs_active_only_when_dispatch_exists -v
```

Expected: 全绿。

### Task 5: 引入 control-plane reconciler，让 hidden main 和 watchdog 都走同一条确定性修复路径

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Create reconcile entrypoint**

能力：
- 读取 active job
- 若 `needs_dispatch_reconcile`：构造 canonical ack/dispatch payload
- 若 `needs_rollup_reconcile`：构造 canonical final rollup payload
- 输出 machine-readable plan，不直接依赖 prompt 自己决定

**Step 2: Add deterministic modes**

至少包含：
- `reconcile-dispatch`
- `reconcile-rollup`
- `resume-job`

**Step 3: Run focused tests**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V51ReconcileTests -v
```

Expected: 全绿。

### Task 6: 收紧 supervisor / worker 提示词，只保留“执行 helper”的职责

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-team-orchestrator.json`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v51-team-orchestrator.example.jsonc`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md`
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Supervisor prompt must stop hand-writing dispatch packets**

主管只允许：
- `start-job-with-workflow`
- `build-visible-ack`
- `build-dispatch-payload`
- `get-next-action`
- `build-rollup-visible-message`
- `record-visible-message`
- `close-job`

禁止 supervisor 手写 `TASK_DISPATCH|...`。

**Step 2: Worker prompt must reject incomplete dispatch packets**

worker 必须：
- 缺字段时报 `WORKFLOW_INCOMPLETE`
- 不允许看到弱化版 dispatch 仍直接 `NO_REPLY`

**Step 3: Run focused doc/template tests**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV51Tests \
  tests.test_openclaw_feishu_multi_agent_skill.V51DocumentationTests -v
```

Expected: 全绿。

### Task 7: 升级 generator/runtime manifest，让远端部署具备 repair 所需元数据

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_feishu_config_builder.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_deploy.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Extend runtime manifest**

新增：
- `runtime.controlPlane.commands.buildDispatchPayload`
- `runtime.controlPlane.commands.buildVisibleAck`
- `runtime.controlPlane.commands.buildRollupVisibleMessage`
- `runtime.controlPlane.commands.recordVisibleMessage`
- `runtime.controlPlane.commands.reconcileDispatch`
- `runtime.controlPlane.commands.reconcileRollup`

**Step 2: Expose explicit visible delivery metadata**

每个 team manifest 必须显式包含：
- `entryAccountId`
- `entryChannel`
- `entryTarget`

**Step 3: Run focused tests**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV51Tests.test_v51_team_input_builds_team_runtime_manifest \
  tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV51Tests.test_v51_team_input_persists_visible_delivery_metadata_for_reconcile -v
```

Expected: 全绿。

### Task 8: 远端灰度部署，先修控制面，再重测双群

**Files:**
- Remote deploy only

**Step 1: Backup current live**

Run:
```bash
ssh openclaw-test-vm 'ts=$(date +%Y%m%d-%H%M%S); cp -a ~/.openclaw ~/.openclaw-backup-$ts'
```

**Step 2: Sync repaired scripts + config**

同步：
- `~/.openclaw/tools/v5/*`
- `~/.openclaw/openclaw.json`
- `~/.openclaw/v51-runtime-manifest.json`
- team workspaces `SOUL.md/USER.md/IDENTITY.md`

**Step 3: Migrate DBs**

Run:
```bash
ssh openclaw-test-vm 'python3 ~/.openclaw/tools/v5/v51_team_orchestrator_runtime.py --db ~/.openclaw/teams/internal_main/state/team_jobs.db init-db'
ssh openclaw-test-vm 'python3 ~/.openclaw/tools/v5/v51_team_orchestrator_runtime.py --db ~/.openclaw/teams/external_main/state/team_jobs.db init-db'
```

**Step 4: Restart gateway + timers**

Run:
```bash
ssh openclaw-test-vm 'systemctl --user daemon-reload'
ssh openclaw-test-vm 'systemctl --user restart openclaw-gateway.service'
ssh openclaw-test-vm 'systemctl --user restart v51-team-internal_main.timer v51-team-external_main.timer'
```

**Step 5: Verify control plane**

Run:
```bash
ssh openclaw-test-vm '~/.npm-global/bin/openclaw config validate'
ssh openclaw-test-vm '~/.npm-global/bin/openclaw channels status --probe'
ssh openclaw-test-vm 'systemctl --user status openclaw-gateway.service --no-pager'
```

### Task 9: 做双群真实验收，不接受“半通过”

**Files:**
- Remote verification only

**Step 1: Internal group real task**

验收必须按顺序看到：
- `【主管已接单】`
- `【运营进度】`
- `【运营结论】`
- `【财务进度】`
- `【财务结论】`
- `【主管最终统一收口】`

并且 DB 里：
- `status=done`
- `participantCount=2`
- `completedParticipantCount=2`
- `rollup_visible_sent=true`

**Step 2: External group real task**

同样要求六段完整可见消息和 `status=done`。

**Step 3: Concurrent safety**

两群连续各发一条真实任务，确认：
- jobRef 各自独立
- hidden main 不串线
- watchdog 不把 healthy dispatch gap 误判为 `active_ok`

**Step 4: Run final verification**

Run:
```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
git diff --check
ssh openclaw-test-vm 'python3 ~/.openclaw/tools/v5/v51_team_orchestrator_runtime.py --db ~/.openclaw/teams/internal_main/state/team_jobs.db get-active --group-peer-id oc_f785e73d3c00954d4ccd5d49b63ef919'
ssh openclaw-test-vm 'python3 ~/.openclaw/tools/v5/v51_team_orchestrator_runtime.py --db ~/.openclaw/teams/external_main/state/team_jobs.db get-active --group-peer-id oc_7121d87961740dbd72bd8e50e48ba5e3'
```

Expected:
- 单测全绿
- `git diff --check` 通过
- 两群 active 都为 `null`
- 最近真实任务都为 `done`

## Acceptance Checklist

- 内部群不再出现“建单后直接沉默直到 watchdog 判死”。
- 外部群不再出现“DB done 但主管最终收口没发”。
- hidden main 不再出现 `Unknown channel: webchat` 影响主管可见消息。
- `watchdog-tick` 不再把待派发 active job 误判为 `active_ok`。
- dispatch payload 不再依赖 supervisor prompt 自由拼接。
- 双群真实回归全部通过。

## Rollback

若任一阶段失败，按以下顺序回滚：

1. 回滚远端 `~/.openclaw/openclaw.json`
2. 回滚远端 `~/.openclaw/tools/v5`
3. 回滚远端 `~/.openclaw/v51-runtime-manifest.json`
4. 回滚 team workspace 的 `SOUL.md/USER.md`
5. 重启 gateway/timers

回滚后不得继续在故障 live 状态上临时 patch；必须回到最近一次完整备份再重新部署。

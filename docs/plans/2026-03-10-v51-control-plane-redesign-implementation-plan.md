# V5.1 Control Plane Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在保留 `V5.1 Hardening` 统一入口、部署能力和现网兼容桥接的前提下，把飞书多群多 Agent 编排重构成 `teamKey-first`、单写控制面、outbox 投递、结构化 callback 的长期稳定架构。

**Architecture:** 新实现以 `Ingress Adapter -> Team Controller -> Worker Dispatch Adapter -> Worker Callback Sink -> Outbox Sender -> Recovery Adapter` 为主链路。`teamKey` 成为唯一内部隔离主键；`groupPeerId / entryTarget` 只保留为外部地址；ingress transcript 扫描只保留给建单认领与异常修复，worker callback 不再保留 hidden main / plaintext / transcript 文本恢复。

**Tech Stack:** Python 3、`sqlite3`、JSON runtime manifest、systemd/launchd、OpenClaw CLI adapter、`unittest`

---

## 实施前提

- 当前对外统一入口保持不变：`accounts + roleCatalog + teams`
- 当前远端运行链路继续可用，重构期间不能中断 `V5.1 Hardening` 基线
- 所有新模块先以并行兼容方式接入，再逐步切主
- 新增测试优先拆分到独立测试文件，避免继续放大 `tests/test_openclaw_feishu_multi_agent_skill.py`

## 目标文件布局

### 新增模块

- `skills/openclaw-feishu-multi-agent-deploy/scripts/core_team_controller.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/core_ingress_adapter.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/core_outbox_sender.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/core_worker_callback_sink.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/core_runtime_store.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/core_openclaw_adapter.py`

### 重点改造

- `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_deploy.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/core_session_hygiene.py`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/core_canary_engine.py`

### 测试拆分

- Create: `tests/test_v51_runtime_store.py`
- Create: `tests/test_v51_ingress_adapter.py`
- Create: `tests/test_v51_team_controller.py`
- Create: `tests/test_v51_outbox_sender.py`
- Create: `tests/test_v51_worker_callback_sink.py`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

### 文档同步

- `README.md`
- `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md`
- `skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md`
- `skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md`

---

## Task 1: 冻结现有行为并建立重构护栏

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`
- Create: `tests/test_v51_runtime_store.py`
- Create: `tests/test_v51_ingress_adapter.py`
- Create: `tests/test_v51_team_controller.py`

**Step 1: 写失败测试，固定长期目标行为**

新增失败测试，至少覆盖：

```python
def test_same_source_message_only_creates_one_job_across_alias_targets():
    ...

def test_group_visible_messages_must_be_sent_via_outbox_only():
    ...

def test_worker_callback_sink_rejects_cross_role_final_output():
    ...

def test_team_controller_is_single_writer_for_job_state():
    ...
```

**Step 2: 运行测试，确认当前结构无法满足**

Run:

```bash
cd /Volumes/soft/13-openclaw\ 安装部署/3-openclaw-mulit-agents-skill/feishu-openclaw-multi-agent/OpenClaw-Feishu-Multi-Agent
python3 -m unittest \
  tests.test_v51_runtime_store \
  tests.test_v51_ingress_adapter \
  tests.test_v51_team_controller -v
```

Expected:

- 至少 1 条失败，证明当前主路径仍依赖旧结构

**Step 3: 把现有重构设计链接进测试注释**

在新增测试文件头部写明参考设计：

- `docs/plans/2026-03-10-v51-control-plane-redesign-design.md`

**Step 4: 运行格式校验**

Run:

```bash
git diff --check
```

Expected:

- 无格式问题

**Step 5: Commit**

```bash
git add tests/test_openclaw_feishu_multi_agent_skill.py tests/test_v51_runtime_store.py tests/test_v51_ingress_adapter.py tests/test_v51_team_controller.py
git commit -m "test: freeze control plane redesign invariants"
```

---

## Task 2: 提取统一存储层，建立 teamKey-first 数据模型

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_runtime_store.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Test: `tests/test_v51_runtime_store.py`

**Step 1: 写失败测试，覆盖新表与唯一键**

至少覆盖：

```python
def test_inbound_events_unique_on_team_key_and_source_message_id():
    ...

def test_outbound_messages_unique_on_job_and_message_kind():
    ...

def test_controller_lock_is_per_team_key():
    ...
```

**Step 2: 运行单测确认失败**

Run:

```bash
python3 -m unittest tests.test_v51_runtime_store -v
```

Expected:

- FAIL，提示新 store API 尚未实现

**Step 3: 实现最小存储层**

在 `core_runtime_store.py` 中实现：

- schema init
- `inbound_events`
- `outbound_messages`
- `stage_callbacks`
- `controller_locks`
- `canonical_target_aliases`（如需要）

同时把 `core_job_registry.py` 中零散的 schema/init 逻辑逐步抽到 store 层。

**Step 4: 运行单测确认通过**

Run:

```bash
python3 -m unittest tests.test_v51_runtime_store -v
```

Expected:

- PASS

**Step 5: 跑回归**

Run:

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- 现有测试保持通过

**Step 6: Commit**

```bash
git add skills/openclaw-feishu-multi-agent-deploy/scripts/core_runtime_store.py skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py tests/test_v51_runtime_store.py
git commit -m "feat: add team-first runtime store"
```

---

## Task 3: 重做 Ingress Adapter，把建单从 supervisor 会话中剥离

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_ingress_adapter.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Test: `tests/test_v51_ingress_adapter.py`

**Step 1: 写失败测试，覆盖 canonical target 与 source message 幂等**

```python
def test_ingress_normalizes_chat_prefixed_group_target():
    ...

def test_ingress_claims_source_message_once():
    ...

def test_resume_job_can_claim_unconsumed_group_message_without_no_reply():
    ...
```

**Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests.test_v51_ingress_adapter -v
```

Expected:

- FAIL

**Step 3: 实现 `InboundEvent` 规范化**

在 `core_ingress_adapter.py` 中实现：

- `canonicalize_target(...)`
- `extract_inbound_event(...)`
- `claim_inbound_event(...)`
- `find_unclaimed_inbound_event_for_team(...)`

**Step 4: 把 `resume-job` 改成先消费 ingress event**

在 `v51_team_orchestrator_reconcile.py` 中：

- 把“从 supervisor transcript 抢救建单”改为“通过 ingress adapter 认领 inbound event 再建单”
- 保留 transcript 扫描，但仅作为 repair fallback

**Step 5: 跑目标测试**

Run:

```bash
python3 -m unittest tests.test_v51_ingress_adapter -v
```

Expected:

- PASS

**Step 6: 跑全量回归**

Run:

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- PASS

**Step 7: Commit**

```bash
git add skills/openclaw-feishu-multi-agent-deploy/scripts/core_ingress_adapter.py skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py tests/test_v51_ingress_adapter.py
git commit -m "feat: add ingress adapter for team claims"
```

---

## Task 4: 引入 Team Controller，收回状态推进权

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_team_controller.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py`
- Test: `tests/test_v51_team_controller.py`

**Step 1: 写失败测试，覆盖单写状态机**

```python
def test_controller_only_allows_one_next_action():
    ...

def test_controller_rejects_duplicate_dispatch_for_same_stage():
    ...

def test_controller_blocks_rollup_until_required_callbacks_exist():
    ...
```

**Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests.test_v51_team_controller -v
```

Expected:

- FAIL

**Step 3: 实现 Team Controller API**

在 `core_team_controller.py` 中提供：

- `start_job(...)`
- `enqueue_ack(...)`
- `dispatch_stage(...)`
- `accept_callback(...)`
- `enqueue_rollup(...)`
- `close_job(...)`

**Step 4: 让旧 registry 退化为兼容 façade**

在 `core_job_registry.py` 中：

- 原有命令继续保留
- 内部调用迁移到 `core_team_controller.py`
- CLI 输出结构保持兼容，避免破坏现网脚本

**Step 5: 运行测试**

Run:

```bash
python3 -m unittest tests.test_v51_team_controller -v
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- 全部 PASS

**Step 6: Commit**

```bash
git add skills/openclaw-feishu-multi-agent-deploy/scripts/core_team_controller.py skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py tests/test_v51_team_controller.py
git commit -m "feat: add single-writer team controller"
```

---

## Task 5: 引入 Outbox Sender，禁止 LLM 会话直接发群消息

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_outbox_sender.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_team_controller.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py`
- Test: `tests/test_v51_outbox_sender.py`

**Step 1: 写失败测试**

```python
def test_ack_is_written_to_outbox_before_delivery():
    ...

def test_duplicate_progress_message_is_deduped_by_outbox_key():
    ...

def test_rollup_message_always_includes_job_ref():
    ...
```

**Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests.test_v51_outbox_sender -v
```

Expected:

- FAIL

**Step 3: 实现 outbox ledger 与 sender**

在 `core_outbox_sender.py` 中实现：

- `enqueue_visible_message(...)`
- `deliver_pending_messages(...)`
- `mark_message_sent(...)`
- `message_dedup_key(...)`

**Step 4: 把可见消息写入从 registry/reconcile 中迁走**

把 `ack/progress/final/rollup` 的“构造 + 发送”分离成：

- controller 负责 enqueue
- sender 负责 delivery

**Step 5: 跑测试**

Run:

```bash
python3 -m unittest tests.test_v51_outbox_sender -v
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- PASS

**Step 6: Commit**

```bash
git add skills/openclaw-feishu-multi-agent-deploy/scripts/core_outbox_sender.py skills/openclaw-feishu-multi-agent-deploy/scripts/core_team_controller.py skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py tests/test_v51_outbox_sender.py
git commit -m "feat: move visible delivery to outbox sender"
```

---

## Task 6: 引入 Worker Callback Sink，收口 hidden main 协议

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_worker_callback_sink.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_team_controller.py`
- Test: `tests/test_v51_worker_callback_sink.py`

**Step 1: 写失败测试**

```python
def test_callback_sink_accepts_structured_payload():
    ...

def test_callback_sink_rejects_cross_role_final_text():
    ...

def test_callback_sink_rejects_worker_subagent_sessions_for_job_scope():
    ...
```

**Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests.test_v51_worker_callback_sink -v
```

Expected:

- FAIL

**Step 3: 实现 structured callback sink**

在 `core_worker_callback_sink.py` 中实现：

- schema validate
- role boundary validate
- payload persist
- callback claim/dedup

**Step 4: 删除 callback 文本恢复，hidden main 退回 mailbox**

在 `v51_team_orchestrator_reconcile.py` 中：

- 只消费 structured callback sink
- 删除 hidden main / plaintext / worker transcript callback promote path

**Step 5: 跑测试**

Run:

```bash
python3 -m unittest tests.test_v51_worker_callback_sink -v
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- PASS

**Step 6: Commit**

```bash
git add skills/openclaw-feishu-multi-agent-deploy/scripts/core_worker_callback_sink.py skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py skills/openclaw-feishu-multi-agent-deploy/scripts/core_team_controller.py tests/test_v51_worker_callback_sink.py
git commit -m "feat: add structured worker callback sink"
```

---

## Task 7: 收敛 OpenClaw 适配边界，方便跟进新版

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_openclaw_adapter.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_session_hygiene.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_canary_engine.py`

**Step 1: 写失败测试，覆盖适配接口**

目标接口：

- `capture_inbound_event`
- `send_message`
- `invoke_agent`
- `inspect_or_reset_session`

**Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- 至少 1 条与新 adapter 相关的测试失败

**Step 3: 实现 adapter**

把直接的 OpenClaw CLI/session 细节调用收口到 `core_openclaw_adapter.py`，其余模块只依赖该接口。

**Step 4: 跑全量回归**

Run:

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add skills/openclaw-feishu-multi-agent-deploy/scripts/core_openclaw_adapter.py skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py skills/openclaw-feishu-multi-agent-deploy/scripts/core_session_hygiene.py skills/openclaw-feishu-multi-agent-deploy/scripts/core_canary_engine.py
git commit -m "refactor: add narrow openclaw adapter boundary"
```

---

## Task 8: 部署链路升级，materialize 新控制面资产

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_deploy.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_feishu_config_builder.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 写失败测试**

覆盖：

```python
def test_deploy_materializes_controller_assets_and_outbox_paths():
    ...

def test_runtime_manifest_contains_new_controller_adapter_fields():
    ...
```

**Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- FAIL

**Step 3: 升级 deploy/runtime manifest**

确保 deploy 后显式 materialize：

- controller store path
- outbox path
- callback sink path
- adapter config
- callback sink / no-legacy-callback-recovery flags

**Step 4: 跑回归**

Run:

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_deploy.py skills/openclaw-feishu-multi-agent-deploy/scripts/core_feishu_config_builder.py skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py tests/test_openclaw_feishu_multi_agent_skill.py
git commit -m "feat: deploy new control plane assets"
```

---

## Task 9: 文档与运维手册同步到新架构

**Files:**
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md`

**Step 1: 把主路径文案统一成新架构**

明确说明：

- 正常路径：ingress -> controller -> outbox -> sender -> callback sink
- ingress transcript 扫描仅用于建单 repair；callback 不再走 hidden main / transcript recovery
- `teamKey` 是唯一内部隔离主键
- 插件与 OpenClaw 之间只依赖窄 adapter

**Step 2: 更新真实提示词与 SOP**

把“如何部署/如何排障/如何验收”改到新术语和新路径。

**Step 3: 运行文档契约测试**

Run:

```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py -v
```

Expected:

- PASS

**Step 4: Commit**

```bash
git add README.md skills/openclaw-feishu-multi-agent-deploy/SKILL.md skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md
git commit -m "docs: align v5.1 docs to redesigned control plane"
```

---

## Task 10: 远端 brownfield 迁移与 canary 验收

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md`
- Test: 远端 `/home/seaworld/.openclaw/...`

**Step 1: 制定迁移前备份清单**

备份内容至少包括：

- `~/.openclaw/openclaw.json`
- `~/.openclaw/v51-runtime-manifest.json`
- `~/.openclaw/teams/`
- `~/.config/systemd/user/v51-team-*`

**Step 2: 在测试机先灰度 team-by-team 切换**

顺序：

1. `internal_main`
2. `external_main`

每切一组，只验证一组。

**Step 3: 执行验收**

Run:

```bash
/home/seaworld/.npm-global/bin/openclaw config validate
/home/seaworld/.npm-global/bin/openclaw channels status --probe
systemctl --user status v51-team-internal_main.timer
systemctl --user status v51-team-external_main.timer
```

再做双群并发真实 canary，验 5 件事：

1. 新单编号全局唯一
2. 单群只出现一条 active job
3. 群内顺序正确
4. 无重复阶段消息
5. 主管最终统一收口始终带 `jobRef`

**Step 4: 记录迁移差异**

把远端发现的新边界问题回灌到：

- `docs/plans/2026-03-10-v51-control-plane-redesign-design.md`
- 新增 implementation notes 文档（如需要）

**Step 5: Commit**

```bash
git add skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md docs/plans/2026-03-10-v51-control-plane-redesign-design.md
git commit -m "docs: add brownfield migration and canary procedure"
```

---

## 风险与边界

### 必须保留兼容层

- 旧 `core_job_registry.py` CLI 命令名
- 旧 runtime manifest 消费路径

### 明确不再扩大使用的旧路径

- supervisor 群会话首轮自由接单
- worker 直接对群发送最终可见消息
- 依赖 hidden main 明文 callback 作为正常主协议
- hidden main / plaintext / worker transcript callback promote fallback

### 可接受的中间状态

- 迁移初期 `core_job_registry.py` 仍是 façade
- `v51_team_orchestrator_reconcile.py` 仍保留 repair 逻辑
- 旧文档可短期标明 legacy，但不能再当主线

---

## 完成标准

实现完成后，必须满足：

1. 双群并发真实消息进入后，不再出现幽灵 `JOB-*` 可见消息
2. 同一群同一条真实用户消息，无论 `oc_xxx` / `chat:oc_xxx`，都只建一个 job
3. 所有群内可见消息都来自 outbox sender，而不是 supervisor/worker session 直接发送
4. worker callback 只有结构化主路径，不再保留 hidden main / plaintext / transcript 文本恢复
5. 插件升级 OpenClaw 版本时，只需要改 adapter，而不是重写控制面状态机

---

## 推荐执行顺序

1. Task 1-2：冻结行为 + 建立 store
2. Task 3-4：前移入口 + 收回状态推进权
3. Task 5-6：引入 outbox 和 callback sink
4. Task 7-8：收敛 OpenClaw 适配层 + 升级 deploy
5. Task 9-10：文档、迁移、远端验收

执行时严格要求：

- TDD
- 小步提交
- 每一阶段都先在本地全量测试，再同步远端
- 不再接受“先跑起来、再靠 transcript 补救”的新逻辑进入主路径

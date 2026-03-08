# V4.3.1 Single-Group Production Stability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把单群生产版从“有状态层蓝图”升级为“可恢复、可初始化、可验收”的 `V4.3.1` 稳定版，并用更新后的 skill 重新配置虚拟机上的 OpenClaw。

**Architecture:** 以 `V4.3.1` 的单群单入口、SQLite 状态层和三机器人可见协作为目标，把稳定性前移到 `job registry + participant state + stale recovery + one-time init + canary`。控制面继续使用 `sessions_send/sessions_history`，展示层继续由 worker 显式 `message` 发群消息。

**Tech Stack:** OpenClaw `@openclaw/feishu`、Feishu 群聊、SQLite、Python 3、shell canary

---

### Task 1: 定义 V4.3.1 生产边界

**Files:**
- Create: `docs/plans/2026-03-07-v4-3-1-single-group-production-stability.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md`
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`

**Step 1: 文档化生产原则**
- 单群单入口
- 自动 `jobRef`
- 一个 `activeJob`
- 一次性 `WARMUP`
- worker 仅发“进度/结论”两条群消息
- supervisor 仅发“接单/收口”两条群消息

**Step 2: 明确 V4.3.1 稳定件**
- participant state machine
- stale recovery / watchdog tick
- 自动释放队列
- 可重复执行的部署初始化步骤

**Step 3: 在 README/SKILL 中把 V4.3.1 升为单群生产推荐版**

### Task 2: 升级 SQLite registry 为生产稳定版

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_runtime.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/v4-3-job-registry.example.sql`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 扩展 jobs 状态流转**
- 增加：`dispatching`、`waiting_workers`、`stale`
- 保持兼容已有 `active/queued/done/failed/cancelled`

**Step 2: 扩展 job_participants 状态流转**
- 增加：`ping_ok`、`dispatch_sent`、`progress_sent`、`final_sent`、`complete_received`

**Step 3: 新增 registry 子命令**
- `mark-worker-progress`
- `mark-dispatch`
- `watchdog-tick`
- `list-queue`
- `get-job`

**Step 4: 保证幂等**
- 相同 `job_ref + agent_id` 的重复进度/结论不会生成脏状态
- 同一个 active job stale 后可自动释放并提升队列

**Step 5: 为 registry 写测试**
- stale recovery
- queue promotion
- worker partial completion
- watchdog close and promote
- idempotent participant update

### Task 3: 增加 V4.3.1 验收与初始化脚本

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_canary.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 编写 canary**
- 读取 SQLite + session jsonl
- 验证：新 job 创建、两 worker messageId、完整 COMPLETE_PACKET、supervisor 最终收口

**Step 2: 把 one-time init 写进验收**
- worker team session 初始化
- fresh supervisor session
- 首次任务 smoke test

**Step 3: 为 canary 写最小测试**

### Task 4: 升级 V4.3.1 提示词模板与交付说明

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md`
- Modify: `CHANGELOG.md`
- Modify: `VERSION`

**Step 1: 固化 V4.3.1 作为稳定版**

**Step 2: 写清部署前置**
- 一次性 WARMUP
- 配置生效后 fresh session
- watchdog 与回滚命令

**Step 3: 写清用户侧体验**
- 用户不输 taskId
- 用户只 @主管
- 多消息场景的入队与补充逻辑

### Task 5: 用更新后的 skill 配置虚拟机并验收

**Files:**
- Remote: `/home/seaworld/.openclaw/openclaw.json`
- Remote: `/home/seaworld/.openclaw/workspace-supervisor_agent/*`
- Remote: `/home/seaworld/.openclaw/workspace-ops_agent/*`
- Remote: `/home/seaworld/.openclaw/workspace-finance_agent/*`

**Step 1: 备份远端配置与 SQLite**

**Step 2: 上传/同步 V4.3.1 registry 与提示词规则**

**Step 3: 重启并做 one-time init**

**Step 4: 执行正式产品化测试词**
- 主管接单
- 运营进度/结论
- 财务进度/结论
- 主管最终收口

**Step 5: 跑 canary 并记录证据**

### Task 6: 收尾与发布

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `VERSION`

**Step 1: 运行测试和脚本语法检查**

**Step 2: 记录最新版本号与变化**

**Step 3: 准备提交与推送说明**

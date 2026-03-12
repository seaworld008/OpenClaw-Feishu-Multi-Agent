# 2026-03-12 External Parallel Recovery Validation

## 背景

在 `V5.1 Hardening` 双群并行验证过程中，`external_main` 出现过一条典型故障链：

- 外部群真实消息已进入 gateway
- `resume-job` 能建单并发送 `ack`
- worker 侧未形成可消费的正式 callback
- job 长时间停在 `wait_worker`
- 有一轮还被错误建成 `serial workflow`

本次文档记录：
- 根因链路
- 修复动作
- 最终远端验收结果

## 影响范围

受影响 team：
- `external_main`

受影响 job：
- `TG-01KKFMF93R3JG1RE3NZGJB2YV1`
  - 问题：并行 team 被错误写成串行 workflow
- `TG-01KKFN1VA7WG396RTP1B1Z6B7X`
  - 问题：parallel job 建出后，worker 结束为 `CALLBACK_OK`，但无 callback 入库
- `TG-01KKFT979JY5F6RXYWG5V4K9YQ`
  - 问题：卡在 `wait_worker`，未自动恢复
- `TG-01KKFXQX9AK1CNYWRQSAAQHQRD`
  - 问题：同样停在 `wait_worker`
- `TG-01KKFX1Y5P8TJN5PJ47R8KSFXA`
  - 问题：旧协议污染单，后续关闭为 `failed`

最终验证通过单：
- `TG-01KKFXQX9AK1CNYWRQSAAQHQRD`

## 根因拆解

### 根因 1：远端 runtime tools 漂移

现网 active manifest 已经是 `parallel`，但远端实际运行的：

- `~/.openclaw/tools/v5/v51_team_orchestrator_reconcile.py`

仍是旧版本。旧版 `start_job_from_inbound()` 只把 `workflow_agents` 传给 controller，没有传入完整 `workflow`，导致 parallel team 建单时被错误降级成：

```json
{
  "mode": "serial",
  "stages": [
    {"agentId": "ops_external_main"},
    {"agentId": "finance_external_main"}
  ]
}
```

### 根因 2：parallel + wait_worker 的 repair 判断仍带串行心智

`workflow_repair_status()` 曾经在 `parallel stage` 下仍依赖：

- `waiting_for_agent_id`
- `current_stage_participant()`

但 parallel stage 正常情况下：
- `waiting_for_agent_id = null`

于是 watchdog 下一轮会误判：
- `needs_dispatch_reconcile`

并把已经派过的 parallel stage 再次当成待派单。

### 根因 3：watchdog service 缺少 CLI 超时护栏

`openclaw agent --json` 一旦长时间无返回，external watchdog service 会持续处于：

- `activating`

这会导致：
- 后续真实入站消息虽然已到 transcript
- 但不会进入下一轮 claim / 建单

### 根因 4：worker 正式完成协议过于依赖 shell callback

旧 worker 协议要求：

- 先生成 `progressDraft/finalDraft`
- 再依赖 shell 形式的 `callbackCommand(ingest-callback ... --payload)`
- 最后输出 `CALLBACK_OK`

现场证据显示：
- worker main session 确实结束成 `CALLBACK_OK`
- 但 `stage_callbacks` 为空

说明模型“完成了会话”，却没有把 callback 真正写入控制面。

## 修复动作

### 1. 远端 scripts 全量重新 materialize

把本地当前仓库中的：

- `core_job_registry.py`
- `core_team_controller.py`
- `core_openclaw_adapter.py`
- `v51_team_orchestrator_reconcile.py`
- 其余 `tools/v5` 运行脚本

同步到远端 repo，并重新 materialize 到：

- `~/.openclaw/tools/v5`

### 2. `start_job_from_inbound()` 改为传完整 workflow

`resume-job` 建单主路径现在会把：

- `workflow=team.get("workflow")`
- `workflow_agents=participants_payload(team)`

同时传给 `TeamController.start_job()`，确保 parallel stage 不再被降级。

### 3. 修复 `workflow_repair_status()` 的 parallel 判断

在 `wait_worker` 状态下：
- 不再只看单个 `waiting_for_agent_id`
- 改成检查当前 stage 全部 participant 是否都已有合法 dispatch 记录

这样 parallel stage 不会再被误判成 `needs_dispatch_reconcile`。

### 4. 给 OpenClaw adapter 增加超时

`core_openclaw_adapter.py` 现在对：

- `invoke_agent()`
- `send_message()`

都加了统一 timeout。  
一旦底层 CLI 调用长时间挂住，控制面会显式失败退出，而不是无限期阻塞整个 watchdog。

### 5. worker 协议升级为单个结构化 JSON 响应

worker 正式协议改为：

- 最后一条 assistant 直接输出单个 JSON 对象

字段包括：
- `progressDraft`
- `finalDraft`
- `finalVisibleText`
- `summary`
- `details`
- `risks`
- `actionItems`
- 可选 `progressMessageId / finalMessageId`

不再把：
- `CALLBACK_OK`
- shell `callbackCommand`

作为唯一主路径依赖。

### 6. 控制面直接从 worker main transcript 提取 JSON 并入库

`reconcile_dispatch()` 在 `invoke_agent()` 返回后，会：

- 读取 worker main transcript
- 提取最后一条 assistant JSON
- 直接调用 `ingest_callback(...)`

这样 worker 完成结果可以立即写进：
- `stage_callbacks`
- `job_participants`

不再依赖 shell callback 必须成功执行。

### 7. 对“终态但无 callback”的 worker 做精确重派

如果某个 worker：
- main session 最后停在 `NO_REPLY` 或 `CALLBACK_OK`
- 但控制面没有 callback 入库

当前主线会：
- 识别缺失 callback 的具体 `agentId`
- 只重派这些缺失的 worker
- 不会整条 job 永久挂死

## 文档与模板同步

本次同步更新了以下主线文档与模板：

- `README.md`
- `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- `skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md`
- `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md`
- `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-team-orchestrator.json`
- `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-seaworld-real-case.json`
- `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-fixed-role-multi-group.json`
- `skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v51-team-orchestrator.example.jsonc`

主线术语已经统一成：

```text
ingress -> controller -> outbox -> sender -> structured worker response
```

## 最终远端验收

最终通过外部群单：

- `TG-01KKFXQX9AK1CNYWRQSAAQHQRD`

最终状态：
- `status = done`
- `ack_visible_sent = 1`
- `rollup_visible_sent = 1`

事件顺序：
1. `job_started`
2. `visible_message_recorded(ack)`
3. `stage_dispatch_planned`
4. `worker_completed(ops_external_main)`
5. `worker_completed(finance_external_main)`
6. `visible_message_recorded(rollup)`
7. `job_closed(done)`

`outbound_messages` 顺序：
1. `ack`
2. `worker_progress / ops_external_main`
3. `worker_final / ops_external_main`
4. `worker_progress / finance_external_main`
5. `worker_final / finance_external_main`
6. `rollup`

验收结论：
- 外部群并行主线已经恢复
- 无重复阶段消息
- 无重复最终收口
- `parallel workflow` 正常闭环

## 当前建议

当前这条事故链可以视为完成收尾。后续若再次出现“worker 已完成但 DB 无 callback”现象，优先排查：

1. 远端 `~/.openclaw/tools/v5` 是否与本地仓库同版本
2. worker workspace 是否仍是最新协议（单个结构化 JSON 响应）
3. `stage_callbacks` 是否已有入库
4. `external_main.service` 是否再次长时间 `activating`

不要再优先怀疑：
- 飞书消息重复
- `publishOrder`
- `rollup` 本身

因为这次事故已经证明，真正的断点在：

**worker 完成协议与控制面入库链路。**

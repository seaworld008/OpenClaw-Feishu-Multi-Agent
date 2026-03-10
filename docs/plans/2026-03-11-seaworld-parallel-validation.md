# 2026-03-11 SeaWorld 双群并行验收记录

## 背景

本次验收针对远端测试机 `192.168.180.131` 上的 OpenClaw + Feishu 多群多 Agent 主线，目标是验证：

- 最新 `V5.1 Hardening` 控制面已替换旧主流程写路径
- `workflow.stages` 的 `parallel stage + publishOrder` 在真实双群可用
- worker 不再直接向群发可见消息，而是通过 `progressDraft / finalDraft` 回调给控制面
- `controller -> outbox -> sender` 成为唯一可见消息发送者

## 远端环境

- OpenClaw 版本：`2026.3.8`
- Gateway 运行路径：`~/.openclaw`
- 正式双群：
  - `internal_main -> oc_f785e73d3c00954d4ccd5d49b63ef919`
  - `external_main -> oc_7121d87961740dbd72bd8e50e48ba5e3`
- 正式机器人：
  - `aoteman`
  - `xiaolongxia`
  - `yiran_yibao`

## 本轮前暴露的问题

1. worker metadata 丢失
- `parallel` workflow 建单时会把 worker metadata 退化成纯 `agentId`
- 远端实际表现为 `accountId=ops_internal_main` / `finance_external_main`

2. worker 与控制面双写可见消息
- worker 自己 `message(progress/final)`
- controller/outbox 再发布一次
- 群里出现重复的运营/财务消息

3. worker callback 协议不稳
- worker 用空 `finalText` 提前回调会被 sink 拒绝
- 中间大量 `No reply from agent.` 噪音

4. 历史 `delivery-queue` 残留
- gateway 重启时持续出现 `delivery-recovery` 噪音
- 旧条目里的 `accountId` 仍是历史错误值

## 本轮修复

### 1. parallel worker metadata preserve

修复 `TeamController.start_job()`，确保 stage group 内的 worker metadata 原样落库并进入 `TASK_DISPATCH`：

- `accountId`
- `role`
- `visibleLabel`

### 2. parallel ordered publish

将并行 stage 主流程收口为：

`parallel analysis -> structured callback -> publish gate -> outbox -> sender`

含义：
- worker 可并行分析
- 群里严格按 `publishOrder` 顺序发布

### 3. draft-only worker contract

worker contract 改成：

- 只提交 `progressDraft`
- 只提交 `finalDraft`
- 提交 `summary / details / risks / actionItems`
- 完整 callback 后输出 `CALLBACK_OK`

不再要求 worker 直接 `message(progress/final)`。

### 4. 清理历史 delivery queue

deploy/materialize 后，清理 `~/.openclaw/delivery-queue/` 中无效历史坏消息，避免 gateway 启动时持续恢复旧脏数据。

## 最新远端验证结果

最新双群真实任务：

- 内部群：`TG-01KKCZ5BNE0V87GVR38KMQ11P9`
- 外部群：`TG-01KKCZ5BNE5NXJ9NBMX16PN3HP`

两条单最终均为：

- `status = done`
- `ack_visible_sent = 1`
- `rollup_visible_sent = 1`

控制面事件顺序：

1. `job_started`
2. `visible_message_recorded (ack)`
3. `stage_dispatch_planned`
4. `worker_completed (ops)`
5. `worker_completed (finance)`
6. `visible_message_recorded (rollup)`
7. `job_closed (done)`

## 结论

当前远端已经验证通过以下关键 contract：

- 双群同时入站可建单
- `parallel stage` 生效
- `publishOrder` 生效
- 控制面成为唯一可见消息发送者
- 最新双群单据都能完整收口到 `done`

## 后续维护约束

1. worker 不得重新回到直接 `message(progress/final)` 模型
2. 新群上线前必须确认 `workflow.stages` 已按 `stageKey / mode / agents / publishOrder` 定义
3. gateway 重启后若出现 `delivery-recovery` 噪音，先检查 `~/.openclaw/delivery-queue/`
4. 若双群再次出现重复消息，优先检查：
   - worker workspace contract 是否被旧版本覆盖
   - callback payload 是否仍在回传旧协议字段
   - outbox 中是否出现同一 `(job_ref, message_kind, stage_index, agent_id)` 多条记录

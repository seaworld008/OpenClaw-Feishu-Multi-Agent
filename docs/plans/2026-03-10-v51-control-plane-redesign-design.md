# V5.1 Long-Term Control Plane Redesign Design

> **For Claude:** 设计确认后，再进入实现计划；不要继续在当前结构上做零散补丁。

**Goal:** 把当前 `V5.1 Hardening` 的飞书多群多 Agent 编排，从“依赖 transcript 补救、可跑但脆弱”的结构，重构成“入口前置、单写控制面、确定性投递、可兼容 OpenClaw 升级”的长期稳定架构。目标不是丢掉现有 `V5.1` 能力，而是保留其统一入口、角色模板化和 runtime 自动部署能力，同时重做消息隔离、状态推进和回调协议的主路径。

**Architecture:** 新架构采用 `Ingress Adapter -> Team Controller -> Outbox -> Sender -> Worker Callback Sink -> Recovery Adapter` 六层模型。`teamKey` 成为内部唯一分区边界；`groupPeerId / entryTarget` 只作为外部地址，不再承担内部状态隔离职责。所有群内可见消息都由控制面统一写入 outbox 再投递；worker 不再直接对群发送最终可见消息，supervisor 群会话也不再直接推进状态机。OpenClaw 只通过窄适配层暴露 4 类能力：入站事件、消息发送、agent 调用、session 检查/重置。这样插件主逻辑与 OpenClaw 3.8 的当前实现解耦，并为后续 OpenClaw 新版保留最小升级面。

**Tech Stack:** Python 3、`sqlite3`、JSON runtime manifest、systemd/launchd、OpenClaw CLI/adapter、`unittest`

---

## 1. 结论摘要

当前方案不适合作为长期主架构，原因不是“某几处 prompt 写得不够严”，而是**职责边界放错了位置**：

1. 首轮群消息先进入 supervisor 群会话，再由 reconcile 事后接管。
2. LLM 会话仍然拥有实际的状态推进能力与外部副作用能力。
3. hidden main 同时承担协议总线、恢复证据源、会话邮箱三种职责。
4. `group_peer_id / entryTarget` 等外部地址字段混入了内部状态分区键。

这类设计会持续带来：

- 串群
- 重复接单 / 重复派单 / 重复收口
- 幽灵消息（如 `JOB-*`）
- 收口编号缺失
- 同一条真实用户消息被多路径消费
- 对 OpenClaw session 行为过度耦合

这不是继续打补丁能彻底解决的问题，必须把控制面前移并单写。

## 2. 现状问题与根因

### 2.1 当前结构的真实运行方式

当前 `V5.1 Hardening` 实际是三条路径混合：

1. **主路径**
   - supervisor 群会话收到真实用户消息
   - 主管按提示词走 `start-job-with-workflow -> build-visible-ack -> build-dispatch-payload`

2. **补救路径**
   - `v51_team_orchestrator_reconcile.py resume-job`
   - 从 transcript、hidden main、worker main 中推断当前 job 状态并修复

3. **绕行路径**
   - supervisor/worker 会话直接使用 `exec / sessions_spawn / message`
   - 由 transcript 或控制面事后发现并尝试纠偏

只要第 3 条路径存在，主系统就不是确定性的。

### 2.2 根因拆解

#### 根因 A：入口控制过晚

现在“真实用户消息”先进入群会话，控制面之后才尝试接管。  
这意味着：

- LLM 先决定是否接单
- LLM 先决定是否发一条可见消息
- LLM 甚至可能先 `sessions_spawn`

一旦这一步先发生，控制面只能修复后果，不能阻止副作用。

#### 根因 B：没有单一状态写入者

当前能推进状态的主体过多：

- registry CLI
- reconcile
- supervisor 群会话
- worker 回调链路

工程上这违反了 `single writer state machine` 原则。  
正确模型应是：**只有 Team Controller 能改变 job 状态和决定可见消息。**

#### 根因 C：协议与恢复混在一起

hidden main 现在既是正常 callback 通道，又是异常恢复证据源。  
这迫使系统同时支持：

- `COMPLETE_PACKET`
- 明文 callback
- worker transcript promoted callback
- hidden main transcript recovery

这类多协议并存的“正常路径”会不断放大复杂度。

#### 根因 D：外部地址字段被用作内部分区主键

`oc_xxx` 与 `chat:oc_xxx` 之类问题，本质说明当前系统把外部路由地址当成了内部状态主键。  
这不符合常见工程做法。  
内部主键应当是：

- `teamKey`
- `jobId/jobRef`
- `sourceMessageId`

而不是消息渠道上的字符串别名。

## 3. 目标原则

长期稳定版必须同时满足以下原则：

1. **入口静默**
   - 真实群消息进入系统时，未经控制面确认前，不允许任何 supervisor 自由可见回复。

2. **单写控制面**
   - 只有 Team Controller 可以：
     - 建单
     - 派单
     - 记录 callback
     - 发送 ack/progress/final/rollup
     - 关单

3. **外部副作用统一投递**
   - 所有群内可见消息必须先进入 outbox，再由统一 sender 投递。

4. **协议显式**
   - worker 只能接收显式 dispatch
   - worker 只能返回结构化 completion payload

5. **恢复边界收紧**
   - ingress transcript 扫描只保留给建单认领与异常修复。
   - worker callback 的 hidden main / plaintext / transcript 文本恢复不再保留。

6. **适配层收敛**
   - 插件只通过窄接口依赖 OpenClaw，避免把核心逻辑绑死在 OpenClaw 3.8 某一版 session 细节上。

## 4. 方案比较

### 方案 A：继续保留当前 reconcile-centric 结构，增加更多 guardrail

优点：

- 变更最小
- 能继续复用现有 prompt、hidden main、resume-job

缺点：

- 复杂度继续累积
- 根因不变：入口仍是 supervisor 群会话
- 无法从结构上杜绝幽灵消息和跨路径重复副作用

结论：不推荐。

### 方案 B：插件侧重构为单写控制面 + outbox + callback sink

优点：

- 不依赖 OpenClaw core 先改动
- 可以保留当前 `V5.1` 的统一入口与部署资产
- 职责边界清晰，适合持续演进

缺点：

- 需要重新梳理 runtime、dispatch、callback 与投递链路
- 是一次正式重构，不是小修

结论：**推荐方案。**

### 方案 C：等待 OpenClaw core 提供官方 silent ingress / pre-delivery hook 后再做

优点：

- 理论上能得到更干净的入口边界

缺点：

- 当前插件无法自主落地
- 会把稳定性升级节奏交给外部版本

结论：可作为长期协同方向，但不能作为当前唯一方案。

## 5. 推荐目标架构

### 5.1 总体分层

推荐把现有系统拆成 6 层：

1. `Ingress Adapter`
2. `Team Controller`
3. `Worker Dispatch Adapter`
4. `Worker Callback Sink`
5. `Outbound Message Outbox + Sender`
6. `Recovery Adapter`

### 5.2 Ingress Adapter

职责：

- 从飞书事件中提取真实 inbound message
- 规范化为统一事件对象
- 做 team 路由与去重预判
- 不产生任何群内可见回复

标准输出：

```json
{
  "eventId": "evt_...",
  "teamKey": "internal_main",
  "channel": "feishu",
  "targetType": "group",
  "canonicalTargetId": "oc_xxx",
  "sourceMessageId": "om_xxx",
  "requestedBy": "ou_xxx",
  "requestText": "@奥特曼 ...",
  "mentionedAgentId": "supervisor_internal_main",
  "receivedAt": "2026-03-10T10:00:00Z"
}
```

规则：

- `canonicalTargetId` 统一成去前缀后的 peer id
- 去重键最少包含：`teamKey + sourceMessageId`
- 如果同一入站事件已进入控制面，不允许再次建单

### 5.3 Team Controller

职责：

- 作为唯一状态写入者
- 处理 job 生命周期
- 生成 outbox 消息
- 驱动 dispatch / callback / rollup

它应当是一个显式状态机，而不是 transcript 驱动脚本拼装。

允许状态：

- `received`
- `queued`
- `ack_pending`
- `stage_dispatch_pending`
- `stage_running`
- `stage_callback_pending`
- `rollup_pending`
- `done`
- `failed`
- `cancelled`

关键原则：

- 一个 `teamKey` 同时只允许一个 controller writer
- 一个 `jobRef` 在任意时刻只能有一个合法 `nextAction`
- 所有状态跃迁必须带明确前置条件

### 5.4 Worker Dispatch Adapter

职责：

- 把控制面 dispatch 转换成 worker 可消费的显式任务
- 只负责调用 worker agent，不负责发群消息

标准 dispatch 契约：

```json
{
  "jobRef": "TG-01...",
  "teamKey": "internal_main",
  "stageIndex": 0,
  "agentId": "ops_internal_main",
  "visibleLabel": "运营",
  "scopeLabel": "运营",
  "forbiddenRoleLabels": ["主管", "财务"],
  "forbiddenSectionKeywords": ["统一收口", "总方案"],
  "requestText": "...",
  "callbackEndpoint": "local://team-controller/callback"
}
```

### 5.5 Worker Callback Sink

职责：

- 接收 worker 的结构化结果
- 做 schema 校验
- 不直接改最终群消息状态
- 由 controller 消费后决定后续动作

标准 callback：

```json
{
  "jobRef": "TG-01...",
  "teamKey": "internal_main",
  "agentId": "ops_internal_main",
  "progressText": "【运营进度｜TG-01...】...",
  "finalText": "【运营结论｜TG-01...】...",
  "summary": "...",
  "details": "...",
  "risks": "...",
  "actionItems": "..."
}
```

原则：

- worker 不再自己直接对群发消息
- worker 只提交内容与结构化字段
- 群消息由控制面统一发送

### 5.6 Outbox + Sender

职责：

- outbox 持久化所有待发送消息
- sender 统一执行实际 `message send`
- 发送成功后回写 message id

outbox 去重键建议：

- `teamKey`
- `jobRef`
- `messageKind` (`ack/progress/final/rollup`)
- `stageIndex`（适用于 worker 消息）
- `agentId`

这样可直接保证：

- `ack` 只发一次
- `运营进度` 只发一次
- `财务结论` 只发一次
- `主管最终统一收口` 只发一次
- 所有可见消息都带 `jobRef`

### 5.7 Recovery Adapter

职责：

- 读取旧 transcript
- 读取 hidden main
- 从 worker transcript 恢复尚未入库的 callback

但这里必须降级成：

- `repair path`
- `brownfield bridge`
- `forensics source`

而不是“日常正确性依赖”。

## 6. 数据模型重构

推荐保留现有 `jobs / job_participants / job_events` 思路，但重构成如下主模型：

### 6.1 jobs

主键：

- `job_id`：内部 UUID/ULID
- `job_ref`：对外展示的 `TG-...`

关键字段：

- `team_key`
- `canonical_target_id`
- `source_message_id`
- `requested_by`
- `title`
- `request_text`
- `status`
- `current_stage_index`
- `next_action`
- `controller_version`

### 6.2 inbound_events

职责：

- 记录所有真实入站消息
- 做幂等与审计

唯一键建议：

- `team_key + source_message_id`

### 6.3 stage_callbacks

职责：

- 存 worker 结构化回调原文
- 不混在 hidden main transcript 里做主存储

唯一键建议：

- `job_id + stage_index + agent_id`

### 6.4 outbound_messages

职责：

- outbox / sent message ledger

唯一键建议：

- `team_key + job_ref + message_kind + stage_index + agent_id`

### 6.5 controller_locks

职责：

- 替代“多个脚本自己抢锁”的零散做法
- 明确 per-team controller 独占

## 7. 隔离模型

长期稳定版必须明确 3 个层级的隔离键：

### 7.1 内部隔离主键：`teamKey`

这是最核心的隔离边界。  
所有运行时状态、锁、workspace、db、outbox、watchdog 都应以 `teamKey` 为第一分区键。

### 7.2 路由地址：`canonicalTargetId`

这是一个外部输入标准化字段，只用于：

- ingress 路由
- delivery 投递
- 审计

它不应承担内部状态主键职责。

### 7.3 幂等主键：`sourceMessageId`

所有首轮建单都必须以此去重。  
无论 supervisor 群会话、timer、手工恢复谁先触发，控制面都应回到同一 job。

## 8. 与 OpenClaw 3.8 及未来版本的兼容边界

### 8.1 插件的定位

飞书多群多 Agent 编排应被定义为：

- **OpenClaw 的补充扩展功能**
- 而不是替代 OpenClaw core 的消息入口或 agent runtime

因此插件应尽量只依赖窄接口，而不是依赖某个版本的 session 行为细节。

### 8.2 推荐适配接口

插件与 OpenClaw 之间只保留 4 类适配：

1. `capture_inbound_event`
2. `send_message`
3. `invoke_agent`
4. `inspect_or_reset_session`

未来 OpenClaw 版本变化时，只改 adapter，不改 controller 核心状态机。

### 8.3 对 OpenClaw core 的期望

如果 OpenClaw 新版未来提供：

- pre-delivery ingress hook
- silent ingress mode
- structured callback tool

插件应优先切到这些官方能力，并逐步退役 transcript repair 的主职责。

## 9. 迁移策略

### 阶段 0：冻结现有 V5.1 外部契约

保留：

- `accounts + roleCatalog + teams`
- `V5.1 Hardening` 对外文档与交付口径

不再继续扩大当前 hidden main + transcript 主路径的复杂度。

### 阶段 1：teamKey-first 内部重分区

目标：

- 内部一切 runtime 状态以 `teamKey` 为主键
- `group_peer_id` 只保留为外部地址

### 阶段 2：引入 outbox

目标：

- ack/progress/final/rollup 全部改为控制面统一发送
- 彻底收口“谁有资格对群发消息”

### 阶段 3：引入 structured callback sink

目标：

- worker 不再直接依赖 hidden main 明文协议
- hidden main 退回到纯 mailbox/announce，不再承担 callback promote 兼容桥接

### 阶段 4：recovery 降级

目标：

- ingress transcript 扫描只保留给旧单恢复、异常补救和审计
- worker callback 主路径不再依赖任何文本恢复即可完整闭环

### 阶段 5：切换到 OpenClaw 官方 ingress hook（若可用）

目标：

- 彻底消除 `JOB-*` 幽灵消息与首轮 supervisor 自由回复问题

## 10. 现有资产保留与淘汰

### 保留

- `roleCatalog + teams` 统一入口
- builder / deploy / runtime manifest
- team workspace materialization
- systemd / launchd 模板
- watchdog / hygiene / canary 体系

### 重构

- `resume-job` 的职责边界
- registry CLI 与可见消息发送的耦合
- hidden main 的主协议职责
- worker 直接群发可见消息

### 最终应淘汰

- 把 supervisor 群 session 当成正常主入口
- 把 transcript recovery 当成正常闭环主路径
- 依赖 prompt 合同来保证“首轮一定不会自由回复”

## 11. 验收标准

达到长期目标架构时，应满足：

1. 同一条真实群消息只能建一条 job。
2. 同一 `jobRef` 的 `ack/progress/final/rollup` 每类最多发送一次。
3. 不同群并发不会串 job、串 callback、串 outbox。
4. 所有群内可见消息都带正确 `jobRef`。
5. worker 无法直接绕过控制面对群发最终可见消息。
6. hidden main / plaintext / worker transcript callback 恢复即使全部关闭，新主路径仍可完整运行。
7. 插件升级到 OpenClaw 新版时，只需调整 adapter 层。

## 12. 推荐执行顺序

下一步实现不应再从 prompt 开始，而应按下面顺序推进：

1. 先做 `teamKey-first` 与 `sourceMessageId` 幂等边界
2. 再做 `outbox` 与统一 sender
3. 再做 structured callback sink
4. 再把 ingress transcript 恢复降级，并删除 callback 文本恢复
5. 最后再考虑和 OpenClaw core 做更深集成

---

## 最终判断

当前 `V5.1 Hardening` 里最值得保留的是：

- 统一入口配置
- team 模型
- 角色模板化
- runtime 自动部署

最不值得继续保留为长期核心的是：

- “supervisor 群会话先跑，reconcile 事后接管”
- “hidden main 既是协议总线又是恢复证据源”
- “worker / supervisor session 直接拥有外部副作用能力”

长期正确方向不是继续补 prompt，而是把它重构成一个**真正的 Team Controller 插件**：

- OpenClaw 提供 runtime 能力
- 插件负责 team 编排与控制面
- 控制面统一写状态、统一发消息、统一收 callback
- ingress transcript recovery 退回到异常修复层；callback 文本恢复彻底删除

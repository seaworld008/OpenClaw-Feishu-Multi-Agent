# 单群生产稳定版 V4.3.1 交叉验证（2026-03-07）

## 结论摘要

`V4.3.1` 的关键判断是：

1. 单群生产版不能只靠 prompt 和 transcript，必须有外部状态层。
2. 控制面应使用 `sessions_send / sessions_history`，展示层应使用显式 `message`。
3. 单群真实长期上线需要一次性初始化、stale recovery 和可重复执行的 canary。
4. 用户不应手工输入 `taskId`；系统内部生成 `jobRef` 更符合生产最佳实践。

## 真实验收结果

远端 VMware 实测通过样板：

- `jobRef`: `TG-20260307-029`
- `title`: `4月签约冲刺：视频号直播+私域转化`
- `status`: `done`
- `ops_progress`: `om_x100b55f415d54ca8b4a251aefedbe8e`
- `ops_final`: `om_x100b55f415ec7cb0b285c5a23638f30`
- `finance_progress`: `om_x100b55f410fb0d3cb260eaa520d7198`
- `finance_final`: `om_x100b55f4108d94acb2c4d97d6c72f29`
- canary 输出：`V4_3_CANARY_OK`

本轮真实运行还验证了 3 个工程结论：

1. hidden main 控制会话必须固定为 `agent:supervisor_agent:main`，否则 worker 完成包容易重新唤醒主管群会话并泄漏内部协议。
2. worker 的群内结论不应再压缩成一句话，展示层允许多行完整结论；长度约束只保留在 `COMPLETE_PACKET`。
3. `mark-worker-complete` 不能强依赖 `--account-id/--role`，否则完成包已经到达但仍会卡死在收口前。

## 官方与行业依据

### 1. OpenClaw Session Tools

来源：<https://docs.openclaw.ai/concepts/session-tool>

关键点：
- group session 必须使用完整键 `agent:<agentId>:<channel>:group:<id>`
- `sessions_send` 用于跨会话派发
- `sessions_history` 用于后续追收结果
- announce 是 `best-effort`

工程含义：
- supervisor 必须用完整 `sessionKey` 精确派单
- 群里“看见机器人说话”不能依赖 announce，worker 必须显式 `message`

### 2. OpenClaw Groups / Configuration Reference

来源：
- <https://docs.openclaw.ai/groups>
- <https://docs.openclaw.ai/gateway/configuration-reference>

关键点：
- group allowlist 与 mention gating 是两层控制
- `mentionPatterns` 是跨客户端稳定触发的兜底方式
- 多 bot / 多群配置仍建议保持单入口和精确路由

工程含义：
- 用户入口应只保留主管机器人
- worker 不应作为普通用户默认入口

### 3. OpenClaw Multiple Gateways

来源：<https://docs.openclaw.ai/gateway/multiple-gateways>

关键点：
- 官方明确：多数场景一个 Gateway 就够了
- 多 Gateway 主要用于隔离或冗余

工程含义：
- 单群生产版不需要为了“多机器人”强行拆多个 Gateway
- 优先把稳定性做在状态层和编排层，而不是基础设施层

### 4. OpenClaw FAQ / 实践提示

来源：<https://docs.openclaw.ai/start/faq>

关键点：
- 代理之间互相调用时必须加 guardrail，避免 loop
- CLI bridge / 多 bot 协作应通过清晰边界控制

工程含义：
- 单群中公开 `@其他机器人` 只能做展示层，不能作为控制面正确性的唯一依据

### 5. Anthropic / OpenAI orchestrator-worker 实践

来源：
- <https://www.anthropic.com/engineering/multi-agent-research-system>
- <https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf>

关键点：
- orchestrator 负责拆分、协调、取舍与收口
- workers 负责结构化子任务输出
- 复杂系统需要显式状态、工件和失败恢复

工程含义：
- `V4.3.1` 采用 supervisor + worker 的集中编排，比“群聊里自由平权聊天”更稳
- watchdog、队列和状态层是生产稳定件，不是可选装饰

## 未找到的官方成品答案

截至 2026-03-07，没有找到 OpenClaw 官方给出的“Feishu 单群 3 个可见机器人长期生产版” turnkey 配方。

因此 `V4.3.1` 不是照抄某一条 issue，而是基于：
- OpenClaw 官方能力边界
- 远端 VMware 实测故障链
- 行业 orchestrator-worker 生产实践

交叉收敛出来的稳定方案。

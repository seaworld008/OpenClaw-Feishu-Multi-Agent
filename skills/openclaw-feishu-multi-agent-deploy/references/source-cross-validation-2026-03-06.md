# 交叉验证记录（2026-03-06）

## 范围

本轮交叉验证聚焦 `V4.2` 单群团队模式，关注 3 个现场问题：
- `sessions_send timeout` 但 worker 实际已执行
- 被 `@` 后仍进入 `NO_REPLY`
- `PLAIN_TEXT` / 代码块包裹文本导致主管未进入工具链

## 官方与公开资料结论

1. OpenClaw Session Tool 的核心是会话级派发能力：`sessions_list`、`sessions_history`、`sessions_send`、`sessions_spawn`。
- 这支持 manager-worker 架构，但不保证“所有派发都同步完成”。
- 公开文档对 `sessions_send` 的语义偏向 best-effort。
- 来源：<https://docs.openclaw.ai/session-tool>
- 来源：<https://docs.openclaw.ai/tools>

2. 单群 Feishu 团队模式中，`sessions_list` 适合作为观察信号，不应作为唯一存在性判断。
- 你们现场已出现“固定 sessionKey 可 send，但 list 未稳定列出”的情况。
- 因此 `send-first probe` 比 `list-first gating` 更稳。
- 来源：OpenClaw 官方会话工具文档 + 本地运行日志交叉判断。

3. `sessions_spawn` 在当前 Feishu 场景下可能受 thread / hook 能力限制。
- 文档没有承诺所有 channel 都等价支持 thread-bound subagent spawning。
- 你们现场日志已出现 `thread=true` / `subagent_spawning hooks` 相关限制。
- 结论：Feishu 下应把 `sessions_spawn` 当兜底，而不是主路径。
- 来源：<https://docs.openclaw.ai/session-tool>
- 来源：本地运行日志（2026-03-06 ~ 2026-03-07）

4. OpenClaw Groups / GroupChat 配置支持 `mentionPatterns`。
- 这可作为 native mention 之外的兜底触发方式。
- 对 `PLAIN_TEXT` / 代码块包裹文本尤其有价值。
- 来源：<https://docs.openclaw.ai/configuration/groups>
- 来源：<https://docs.openclaw.ai/zh-CN/configuration/groups>

5. OpenAI 与 Anthropic 的公开多 Agent 最佳实践都更接近 manager-worker / orchestrator-workers，而不是让所有 agent 在公开群里自由乱聊。
- 这支持当前 `V4.2` 里的“控制面与展示层分离”设计。
- 来源：<https://openai.com/index/building-effective-agents/>
- 来源：<https://www.anthropic.com/engineering/built-multi-agent-research-system>

6. 两阶段交互（先 ACK，再发正文）是降低超时假阴性的常见工程化手段。
- 公开资料没有针对 OpenClaw Feishu 的专门教程，但在 agent / workflow 编排实践里，这是合理的保守策略。
- 本仓库将其纳入 `V4.2` 推荐，而不是强制默认。
- 来源：OpenAI / Anthropic 的 agent 编排方法论 + 本地运行时序分析。

## 本轮沉淀到 skill 的结论

1. `V4.2` 默认采用 `send-first probe`。
2. `sessions_list` 只做观察，不再作为唯一 gating。
3. `sessions_spawn` 只做兜底。
4. 若 `sessions_send timeout` 但 worker 已出现同 `taskId` 回包，应进入 `timeout_observed_worker_delivered` 分支，而不是继续误报纯失败。
5. 对被 `@` 的主管任务，若正文命中任务关键词，不应再落入 `NO_REPLY`；需要通过 `mentionPatterns` 与包裹文本兼容来增强鲁棒性。
6. 公开群里的 `@其他机器人` 只作为展示层，不作为控制面正确性的唯一依据。

## 仍然保留的现实边界

1. 目前没有找到公开的、与 OpenClaw Feishu `timeout but delivered` 完全一一对应的官方 issue 结论。
- 这部分优化主要基于官方语义边界 + 你们本地实测日志。

2. `V3 / V3.1` 跨群模式尚未全面迁移到与 `V4.2` 相同的 timeout / mentionPatterns 策略。
- 这是有意保守，避免在缺少跨群实测证据时过度改动生产推荐路径。

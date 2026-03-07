# 单群生产版 V4.3 交叉验证（2026-03-07）

## 结论摘要

`V4.3` 的关键判断是：

1. 生产环境不应要求最终用户手工输入 `taskId`
2. supervisor 应自动生成内部 `jobRef`
3. 单群场景必须限制为“一个活跃任务 + 队列”，否则 transcript 长期复用后会串任务
4. 最终收口应基于外部状态层，不应只依赖 transcript

## 官方与行业依据

### 1. OpenClaw Session Tools

来源：<https://docs.openclaw.ai/concepts/session-tool>

关键点：

- `sessions_send` 支持 `timeoutSeconds=0` 并返回 `accepted`
- `sessions_history` 用于后续追收结果
- announce 是 `best-effort`
- `status: "ok"` 不等于公开群一定收到展示消息

工程含义：

- 单群生产版必须把“控制面派单成功”和“公开群消息可见”分开建模
- worker 群发应显式调用 `message`，而不是继续把 announce 当可靠主路径

### 2. OpenClaw Session Management

来源：<https://docs.openclaw.ai/concepts/session>

关键点：

- group session 会复用
- `resetByType.group.idleMinutes` 可控制群会话空闲重置
- `/new` 与 `/reset` 会创建 fresh session
- 删除 store key 或 transcript 后，下次消息会重建会话

工程含义：

- 单群生产版不能无限制复用同一个群 transcript
- 应显式配置群会话 reset 策略
- 同时仍需外部状态层来避免任务串线

### 3. OpenClaw Feishu Channel

来源：<https://docs.openclaw.ai/channels/feishu>

关键点：

- 飞书群路由可精确到群
- 多账号 account 路由可精确控制出站 bot

工程含义：

- 单群多 bot 团队模式是成立的
- 但生产上的正确性仍需 supervisor 编排与外部状态层来兜底

### 4. Anthropic 多 agent 系统实践

来源：<https://www.anthropic.com/engineering/multi-agent-research-system>

关键点：

- 采用 orchestrator-worker 模式
- lead agent 负责拆任务、边界和资源分配
- subagent 应拿到清晰的目标、输出格式和边界
- 对复杂度做 effort budget 控制
- 更推荐通过外部工件系统减少“传话游戏”

工程含义：

- 单群生产版应坚持 supervisor 统筹、worker 专职执行
- 状态层或工件层优于只靠自然语言上下文传递

### 5. Akka 多 agent 编排实践

来源：<https://doc.akka.io/sdk/agents/orchestrating.html>

关键点：

- orchestration 适合需要持久流程状态和明确任务流转的场景
- 工作流编排应显式管理状态与任务阶段

工程含义：

- `V4.3` 采用“活跃任务 + 队列 + 外部状态层”比继续堆 prompt 更稳

## 未找到的官方结论

截至 2026-03-07，我没有找到一条 OpenClaw 官方 issue 明确给出：

- “飞书单群多 agent 生产版应要求用户手输 taskId”
- “仅靠 transcript 就足以处理单群多人多任务长期运行”

所以这里的 `V4.3` 不是照抄某一条 issue，而是基于：

- OpenClaw 官方能力边界
- 已有远端实测问题
- 行业主流 orchestrator-worker 实践

交叉收敛得到的更稳方案。

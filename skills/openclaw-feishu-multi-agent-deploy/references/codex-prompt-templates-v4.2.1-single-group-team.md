# 飞书单群高级 Agent 团队交付蓝图（V4.2.1）

## 这份 V4.2.1 要解决什么

`V4.2` 已经把单群团队模式的控制面跑通：

- 主管真实派单
- worker 真实执行
- 主管最终收口

`V4.2.1` 进一步解决的是：

- 其他机器人不再只在内部 session 执行，而是要在群里真实发出可见消息
- 展示层不再依赖隐式 announce，而是由 worker 显式调用 `message` 工具发群消息
- 演示时用户能看到“主管拆任务 -> 运营/财务机器人回群里报进度 -> 主管最终收口”的完整团队观感
- 控制面仍保持稳定，不把群消息观感误当成唯一正确性依据

一句话说，`V4.2.1` 是：

**单群团队模式 + 稳定控制面 + worker 显式群发进度 + 主管最终收口。**

## 与 V4.2 的区别

- `V4.2`：重点是控制面跑通，展示层允许增强，但不保证 worker 一定显式发群消息。
- `V4.2.1`：把“worker 显式群发短摘要”正式纳入主流程和验收标准。

## 真实跑通结论（2026-03-07，VMware + Feishu 实测）

以下结论已经在远端真实环境中跑通：

- OpenClaw 部署环境：VMware 虚拟机
- OpenClaw 版本：`2026.3.2`
- 团队群：`oc_f785e73d3c00954d4ccd5d49b63ef919`
- 主管机器人：`aoteman`
- 运营机器人：`xiaolongxia`
- 财务机器人：`yiran_yibao`
- 成功任务：`team-v4-2-015`

本轮真实证据：

1. 运营机器人真实群发成功  
- `messageId`: `om_x100b558f16d170e0c4ac92409ae2e2c`

2. 财务机器人真实群发成功  
- `messageId`: `om_x100b558f147928a0b214ccb83766041`

3. 主管最终完成收口  
- gateway 日志出现：`feishu[aoteman]: dispatch complete (queuedFinal=true, replies=1)`

这说明 `V4.2.1` 已经是：

- 可复现
- 可验证
- 可交付
- 可演示

## V4.2.1 架构（推荐）

```mermaid
flowchart LR
  user["用户任务入口"]

  subgraph team["飞书单群团队（Team Group）"]
    supervisor["supervisor_agent\n主管总控"]
    ack["ACK_ONLY 派单"]
    detail["详细任务派单"]
    visible["worker 显式群发短摘要"]
    rollup["主管统一收口"]

    subgraph workers["执行层"]
      ops["ops_agent\n运营执行"]
      finance["finance_agent\n财务执行"]
    end
  end

  user -->|@主管机器人| supervisor
  supervisor --> ack
  ack --> ops
  ack --> finance
  supervisor --> detail
  detail --> ops
  detail --> finance
  ops -->|message 工具群发摘要| visible
  finance -->|message 工具群发摘要| visible
  ops -->|详细结果回主管| rollup
  finance -->|详细结果回主管| rollup
  supervisor -->|最终方案| rollup
```

## 当前 3 机器人真实配置目标

```yaml
singleTeamGroup:
  peerKind: "group"
  peerId: "oc_f785e73d3c00954d4ccd5d49b63ef919"

routes:
  - { peerKind: "group", peerId: "oc_f785e73d3c00954d4ccd5d49b63ef919", accountId: "aoteman",     agentId: "supervisor_agent" }
  - { peerKind: "group", peerId: "oc_f785e73d3c00954d4ccd5d49b63ef919", accountId: "xiaolongxia", agentId: "ops_agent" }
  - { peerKind: "group", peerId: "oc_f785e73d3c00954d4ccd5d49b63ef919", accountId: "yiran_yibao", agentId: "finance_agent" }
```

## V4.2.1 核心配置要求

```yaml
tools:
  allow:
    - "group:fs"
    - "group:runtime"
    - "group:web"
    - "group:messaging"
    - "group:sessions"
  agentToAgent:
    enabled: true
    allow:
      - "supervisor_agent"
      - "ops_agent"
      - "finance_agent"
  sessions:
    visibility: "all"

session:
  sendPolicy:
    default: "allow"
```

## 主管规则

```text
你是主管 Agent，是本群唯一总控入口。

固定流程：
1) 识别任务并做 sessions_list 观察
2) 对 ops_agent / finance_agent 发送 ACK_ONLY，建议 timeoutSeconds=15
3) ACK 成功后发送详细执行任务，建议 timeoutSeconds=0
4) 详细任务正文中必须明确要求 worker：
   - 先显式调用 message 工具往团队群发 1 条短摘要
   - 再把详细结果与 toSupervisorSummary 回传给你
5) 通过 sessions_history 或 worker session jsonl 完成二次收口
6) 最终统一对用户输出

硬约束：
- 不得文本模拟派单
- 不得在无证据时声称“已安排 / 已派单 / 已分配”
- 固定 sessionKey 只能使用 `agent:<agentId>:feishu:group:<peerId>`
- 若 worker 已回包但 sendStatus=timeout，记为 `timeout_observed_worker_delivered`
- worker 的群发摘要不是可选项；若详细任务已进入 worker，但缺少真实 messageId，不得判定为“展示层成功”
```

## 执行角色规则

### ops_agent / finance_agent

```text
你是执行角色 Agent。

收到 ACK_ONLY 时：
1) 只允许返回两行：
   ACK
   toSupervisorSummary: ...
2) 禁止 NO_REPLY

收到详细任务时：
1) 必须先显式调用 `message` 工具往团队群发 1 条短摘要
2) 必须使用你自己的 accountId 和团队群 chat target
3) message 成功后，首行返回：
   简短进度已群发（messageId=<真实 messageId>）
4) 随后再输出 toSupervisorSummary 与详细执行结果
5) 禁止 ANNOUNCE_SKIP
6) 禁止把完整长文直接刷到群里
```

## worker 显式群发规则

不要再依赖隐式 announce。  
在 `V4.2.1` 里，worker 的展示层必须显式调用 `message` 工具。

### 运营机器人

```text
channel=feishu
account=xiaolongxia
target=chat:oc_f785e73d3c00954d4ccd5d49b63ef919
```

示例摘要：

```text
【运营进度｜<taskId>】已接单，正在输出活动节奏、渠道策略、执行清单与风险预案。
```

### 财务机器人

```text
channel=feishu
account=yiran_yibao
target=chat:oc_f785e73d3c00954d4ccd5d49b63ef919
```

示例摘要：

```text
【财务进度｜<taskId>】已接单，正在输出预算上限、ROI 三线、现金流与止损规则。
```

## 一次性交付主提示词（V4.2.1，可直接发 Codex）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，按官方最新规范完成 V4.2.1 交付：
实现“飞书单群高级 Agent 团队模式 + 主管真实派单 + worker 显式群发短摘要 + 最终统一收口”。

目标：
- 在同一个飞书群里放 3 个机器人。
- 用户默认只 @主管机器人。
- supervisor_agent 负责拆任务、派单、必要时组织互审、最终收口。
- ops_agent / finance_agent 在执行详细任务时，必须先显式调用 `message` 工具往团队群发一条短摘要，再把详细结果回主管。
- 群里必须真的看到其他机器人发消息，不能只在 session 内部执行。

固定输入：
- teamGroup:
  - { peerKind: "group", peerId: "oc_f785e73d3c00954d4ccd5d49b63ef919" }
- accountMappings:
  - { accountId: "aoteman", appId: "cli_a923c749bab6dcba", appSecret: "TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX", encryptKey: "", verificationToken: "" }
  - { accountId: "xiaolongxia", appId: "cli_a9f1849b67f9dcc2", appSecret: "g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr", encryptKey: "", verificationToken: "" }
  - { accountId: "yiran_yibao", appId: "cli_a923c71498b8dcc9", appSecret: "swscrlPKYCwAehOyyoLrlesLTsuYY6nl", encryptKey: "", verificationToken: "" }
- agents:
  - { id: "supervisor_agent", role: "主管总控" }
  - { id: "ops_agent", role: "运营执行" }
  - { id: "finance_agent", role: "财务执行" }
- routes:
  - { peerKind: "group", peerId: "oc_f785e73d3c00954d4ccd5d49b63ef919", accountId: "aoteman",     agentId: "supervisor_agent" }
  - { peerKind: "group", peerId: "oc_f785e73d3c00954d4ccd5d49b63ef919", accountId: "xiaolongxia", agentId: "ops_agent" }
  - { peerKind: "group", peerId: "oc_f785e73d3c00954d4ccd5d49b63ef919", accountId: "yiran_yibao", agentId: "finance_agent" }

强约束：
1) 先审计 ~/.openclaw/openclaw.json。
2) 只做最小 patch。
3) 主管必须采用 ACK_ONLY -> 详细任务 -> sessions_history 的双阶段派单。
4) 固定 sessionKey 只能使用 `agent:<agentId>:feishu:group:<peerId>`。
5) worker 详细任务中必须显式调用 `message` 工具发群摘要：
   - ops_agent 使用 `accountId=xiaolongxia`
   - finance_agent 使用 `accountId=yiran_yibao`
   - target 必须是 `chat:oc_f785e73d3c00954d4ccd5d49b63ef919`
6) worker 返回时必须带 `messageId` 与 `toSupervisorSummary`。
7) 验收必须证明：
   - supervisor 真实派单
   - ops_agent 有真实群发 messageId
   - finance_agent 有真实群发 messageId
   - supervisor 最终收口
8) 公开群消息只能发摘要，不得把完整执行稿刷到群里。
9) 若详细任务 sendStatus=timeout，但 worker session 已出现相同 taskId 且带 messageId / toSupervisorSummary，按 `timeout_observed_worker_delivered` 继续收口。
10) 输出完整命令：
   - 备份
   - openclaw config validate
   - openclaw gateway restart
   - openclaw agents list --bindings
   - canary 验证
   - 回滚
```

## 推荐测试任务

```text
@奥特曼 请启动本群高级团队模式：
任务ID：team-v4-2-015
主题：为 4 月促销活动做一份可执行方案
要求：
1) 你先拆分任务
2) 让运营与财务分别执行
3) 如果两方结论冲突，请组织 1 轮互审
4) 最终由你统一收口
5) 运营和财务在执行时，各自必须先在群里公开回复一条简短进度摘要，再把详细结果回传给你
```

## 验收标准

以下 4 条缺一不可：

1. `supervisor_agent` 真实派单
- 有 `dispatchEvidence`

2. `ops_agent` 真实群发
- worker session 中出现 `messageId`
- 群里可见 `【运营进度｜<taskId>】...`

3. `finance_agent` 真实群发
- worker session 中出现 `messageId`
- 群里可见 `【财务进度｜<taskId>】...`

4. 主管最终收口
- supervisor 最终回复已发出

## 门禁命令

```bash
LOG="/tmp/openclaw/openclaw-$(date +%F).log"
START_LINE=$(wc -l < "$LOG")
sleep 120
bash skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_2_team_canary.sh \
  --task-id "team-v4-2-015" \
  --session-root "${HOME}/.openclaw/agents" \
  --log "$LOG" \
  --start-line "$START_LINE" \
  --required-agents "ops_agent,finance_agent" \
  --require-visible-messages
```

## 真实交付建议

1. 如果客户只关心“能跑”，`V4.2` 已经足够。
2. 如果客户要现场看见多个机器人真的在群里协作，直接交付 `V4.2.1`。
3. 单群模式里，`V4.2.1` 现在是当前最推荐版本。
